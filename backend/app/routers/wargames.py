from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_session
from app.models.user import User
from app.models.session import LabSession
from app.models.wargame import WargameState, DetectionEvent
from app.dependencies import get_current_user

router = APIRouter(prefix="/wargames", tags=["wargames"])


class WargameStateResponse(BaseModel):
    id: int
    session_id: str
    detection_score: int
    detection_level: str
    is_active: bool
    busted_at: Optional[datetime]
    won_at: Optional[datetime]
    last_poll_at: Optional[datetime]
    created_at: datetime


class DetectionEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    raw_log_line: str
    source_ip: Optional[str]
    score_delta: int
    timestamp: datetime


class StartWargameRequest(BaseModel):
    session_id: str


@router.post("", response_model=WargameStateResponse, status_code=201)
def start_wargame(
    req: StartWargameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, req.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session must be running to start wargame")

    # Check if wargame already exists
    existing = db.exec(select(WargameState).where(WargameState.session_id == req.session_id)).first()
    if existing:
        return existing

    state = WargameState(session_id=req.session_id)
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


@router.get("/{session_id}", response_model=WargameStateResponse)
def get_wargame(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    state = db.exec(select(WargameState).where(WargameState.session_id == session_id)).first()
    if not state:
        raise HTTPException(status_code=404, detail="Wargame not found for this session")
    return state


@router.get("/{session_id}/events", response_model=List[DetectionEventResponse])
def get_wargame_events(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    state = db.exec(select(WargameState).where(WargameState.session_id == session_id)).first()
    if not state:
        raise HTTPException(status_code=404, detail="Wargame not found")

    events = db.exec(
        select(DetectionEvent)
        .where(DetectionEvent.wargame_state_id == state.id)
        .order_by(DetectionEvent.timestamp.desc())
        .limit(limit)
    ).all()
    return events
