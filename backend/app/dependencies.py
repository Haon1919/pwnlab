from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime
import hashlib

from app.database import get_session
from app.config import settings
from app.models.user import User, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

PLAN_LIMITS = {
    "free":       {"max_concurrent_sessions": 1, "ai_generations_per_month": 5,  "kali_access": False},
    "pro":        {"max_concurrent_sessions": 3, "ai_generations_per_month": 50, "kali_access": True},
    "enterprise": {"max_concurrent_sessions": 20,"ai_generations_per_month": -1, "kali_access": True},
}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try API key first
    if x_api_key:
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        api_key = db.exec(select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)).first()
        if api_key:
            api_key.last_used_at = datetime.utcnow()
            db.add(api_key)
            db.commit()
            user = db.get(User, api_key.user_id)
            if user and user.is_active:
                return user
        raise credentials_exception

    # Try JWT Bearer
    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_plan_limits(user: User = Depends(get_current_user)) -> dict:
    return PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])


def check_session_limit(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    from app.models.session import LabSession
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    active_sessions = db.exec(
        select(LabSession).where(
            LabSession.user_id == user.id,
            LabSession.status.in_(["starting", "running"])
        )
    ).all()
    if len(active_sessions) >= limits["max_concurrent_sessions"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Plan limit reached: max {limits['max_concurrent_sessions']} concurrent sessions"
        )
