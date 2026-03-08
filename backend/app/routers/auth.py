from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_session
from app.models.user import User, APIKey
from app.config import settings
from app.dependencies import get_current_user
from app.services.ai_service import encrypt_gemini_key

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    gemini_api_key: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    plan: str
    created_at: datetime


class APIKeyResponse(BaseModel):
    id: int
    label: str
    created_at: datetime
    last_used_at: Optional[datetime]


class APIKeyCreateRequest(BaseModel):
    label: str = "default"


class APIKeyCreatedResponse(BaseModel):
    raw_key: str  # Only shown once
    label: str
    id: int


@router.post("/register", response_model=UserResponse)
def register(req: RegisterRequest, db: Session = Depends(get_session)):
    # Check duplicates
    if db.exec(select(User).where(User.username == req.username)).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.exec(select(User).where(User.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    encrypted_key = None
    if req.gemini_api_key:
        encrypted_key = encrypt_gemini_key(req.gemini_api_key)

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        gemini_api_key_encrypted=encrypted_key,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.username == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return {"access_token": create_access_token(user.id)}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/api-keys", response_model=APIKeyCreatedResponse)
def create_api_key(
    req: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    raw_key = APIKey.generate_raw_key()
    api_key = APIKey(
        key_hash=APIKey.hash_key(raw_key),
        user_id=current_user.id,
        label=req.label,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {"raw_key": raw_key, "label": api_key.label, "id": api_key.id}


@router.get("/api-keys", response_model=List[APIKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    keys = db.exec(select(APIKey).where(APIKey.user_id == current_user.id, APIKey.is_active == True)).all()
    return keys


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    key = db.get(APIKey, key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    db.add(key)
    db.commit()
    return {"status": "deleted"}
