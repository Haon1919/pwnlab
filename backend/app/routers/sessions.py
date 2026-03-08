from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_session
from app.models.user import User
from app.models.session import LabSession
from app.models.wargame import WargameState
from app.dependencies import get_current_user, check_session_limit
from app.services.session_manager import create_session, stop_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    scenario_id: str
    wargame: bool = False
    blackbox: bool = False


class SessionResponse(BaseModel):
    id: str
    scenario_id: Optional[str]
    status: str
    mode: str
    blackbox: bool
    docker_network_name: Optional[str]
    container_count: int
    session_offset: Optional[int]
    flags_captured: List[str]
    created_at: datetime
    updated_at: datetime
    stopped_at: Optional[datetime]
    error_message: Optional[str]


class FlagSubmitRequest(BaseModel):
    flag: str
    objective_id: str


def session_to_response(session: LabSession, blackbox_hide: bool = False) -> dict:
    data = {
        "id": session.id,
        "scenario_id": None if blackbox_hide else session.scenario_id,
        "status": session.status,
        "mode": session.mode,
        "blackbox": session.blackbox,
        "docker_network_name": session.docker_network_name,
        "container_count": len(session.container_ids),
        "session_offset": session.session_offset,
        "flags_captured": session.flags_captured,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "stopped_at": session.stopped_at,
        "error_message": session.error_message,
    }
    return data


@router.post("", status_code=201)
async def start_session(
    req: StartSessionRequest,
    current_user: User = Depends(check_session_limit),
    db: Session = Depends(get_session),
):
    try:
        session = await create_session(
            scenario_id=req.scenario_id,
            user=current_user,
            db=db,
            wargame=req.wargame,
            blackbox=req.blackbox,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {e}")

    return session_to_response(session, blackbox_hide=session.blackbox)


@router.get("/{session_id}")
def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    return session_to_response(session, blackbox_hide=session.blackbox and session.status != "stopped")


@router.get("")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    sessions = db.exec(select(LabSession).where(LabSession.user_id == current_user.id)).all()
    return [session_to_response(s, blackbox_hide=s.blackbox and s.status != "stopped") for s in sessions]


@router.delete("/{session_id}")
async def stop_session_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in ["starting", "running"]:
        raise HTTPException(status_code=400, detail=f"Session is {session.status}, cannot stop")

    await stop_session(session, db)
    return {"status": "stopped", "session_id": session_id}


@router.post("/{session_id}/flag")
def submit_flag(
    session_id: str,
    req: FlagSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")

    # Load scenario to validate flag
    from app.services.scenario_loader import load_scenario_from_db_or_disk
    try:
        scenario_data = load_scenario_from_db_or_disk(session.scenario_id, db)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not load scenario for validation")

    # Find matching objective
    for obj in scenario_data.get("objectives", []):
        if obj["id"] == req.objective_id:
            validation = obj.get("validation", {})
            if validation.get("method") == "flag_string":
                if req.flag == validation.get("value"):
                    flags = session.flags_captured
                    if req.objective_id not in flags:
                        flags.append(req.objective_id)
                        session.flags_captured = flags
                        session.updated_at = datetime.utcnow()
                        db.add(session)
                        db.commit()
                    return {"correct": True, "message": "Flag captured!"}
                else:
                    return {"correct": False, "message": "Incorrect flag"}

    raise HTTPException(status_code=404, detail="Objective not found")
