from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_session
from app.models.user import User
from app.models.session import LabSession
from app.models.scenario import Scenario
from app.dependencies import get_current_user, PLAN_LIMITS
from app.services.ai_service import generate_scenario, pick_blackbox_scenario
from app.services.session_manager import create_session

router = APIRouter(prefix="/ai", tags=["ai"])


class GenerateScenarioRequest(BaseModel):
    prompt: str
    difficulty: str = "beginner"
    tags: List[str] = []
    wargame: bool = False
    gemini_api_key: Optional[str] = None  # If not using stored key


class BlackboxRequest(BaseModel):
    novel: bool = False  # Use Gemini to generate a new scenario vs picking existing


class BlackboxResponse(BaseModel):
    session_id: str
    status: str
    message: str


@router.post("/generate-scenario")
async def generate_scenario_endpoint(
    req: GenerateScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    limits = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])

    # Use provided key or user's stored key
    api_key = req.gemini_api_key
    encrypted_key = current_user.gemini_api_key_encrypted if not api_key else None

    if not api_key and not encrypted_key:
        raise HTTPException(
            status_code=400,
            detail="No Gemini API key. Provide one in request or store it in your account."
        )

    try:
        scenario_data = await generate_scenario(
            prompt=req.prompt,
            difficulty=req.difficulty,
            tags=req.tags,
            wargame=req.wargame,
            gemini_api_key=api_key,
            encrypted_key=encrypted_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e}")

    # Save to DB
    meta = scenario_data["metadata"]
    raw_yaml = scenario_data.pop("_raw_yaml", "")

    import yaml
    if not raw_yaml:
        raw_yaml = yaml.dump(scenario_data, default_flow_style=False)

    scenario = Scenario(
        id=meta["id"],
        name=meta["name"],
        difficulty=meta["difficulty"],
        tags_json=json.dumps(meta.get("tags", [])),
        ai_generated=True,
        yaml_content=raw_yaml,
        is_public=False,
        owner_user_id=current_user.id,
        wargame_enabled=bool(scenario_data.get("wargame")),
    )

    # Handle ID conflicts
    existing = db.get(Scenario, meta["id"])
    if existing:
        import uuid
        scenario.id = f"{meta['id']}-{str(uuid.uuid4())[:8]}"

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "scenario_id": scenario.id,
        "name": scenario.name,
        "difficulty": scenario.difficulty,
        "tags": json.loads(scenario.tags_json),
        "wargame_enabled": scenario.wargame_enabled,
        "yaml_preview": raw_yaml[:500] + ("..." if len(raw_yaml) > 500 else ""),
    }


@router.post("/blackbox", response_model=BlackboxResponse)
async def start_blackbox(
    req: BlackboxRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    try:
        scenario_id = await pick_blackbox_scenario(db=db)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        session = await create_session(
            scenario_id=scenario_id,
            user=current_user,
            db=db,
            wargame=True,
            blackbox=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start blackbox session: {e}")

    return BlackboxResponse(
        session_id=session.id,
        status=session.status,
        message="Blackbox session started. Target is hidden. Use nmap to discover it.",
    )


@router.get("/blackbox/{session_id}/reveal")
def reveal_blackbox(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session = db.get(LabSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.blackbox:
        raise HTTPException(status_code=400, detail="Session is not a blackbox session")
    if session.status != "stopped":
        raise HTTPException(status_code=403, detail="Session must be stopped before reveal")

    from app.services.scenario_loader import load_scenario_from_db_or_disk, ScenarioValidationError
    try:
        scenario_data = load_scenario_from_db_or_disk(session.scenario_id, db)
    except ScenarioValidationError:
        raise HTTPException(status_code=404, detail="Scenario data not found")

    return {
        "session_id": session_id,
        "scenario_id": session.scenario_id,
        "scenario_name": scenario_data["metadata"]["name"],
        "difficulty": scenario_data["metadata"]["difficulty"],
        "targets": [
            {"id": t["id"], "image": t["image"]}
            for t in scenario_data.get("targets", [])
        ],
        "objectives": scenario_data.get("objectives", []),
        "flags_captured": session.flags_captured,
    }
