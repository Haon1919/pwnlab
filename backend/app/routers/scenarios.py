from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path

from app.database import get_session
from app.models.user import User
from app.models.scenario import Scenario
from app.dependencies import get_current_user
from app.services.scenario_loader import (
    load_yaml, validate_scenario, ScenarioValidationError, list_scenarios_from_disk
)
from app.config import settings

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class ScenarioSummary(BaseModel):
    id: str
    name: str
    difficulty: str
    tags: List[str]
    ai_generated: bool
    is_public: bool
    download_count: int
    wargame_enabled: bool
    rating: Optional[float]
    created_at: datetime


@router.get("", response_model=List[ScenarioSummary])
def list_scenarios(
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    # Load from DB
    query = select(Scenario).where(Scenario.is_public == True)
    db_scenarios = db.exec(query).all()

    # Also load from disk
    disk_scenarios = list_scenarios_from_disk(Path(settings.SCENARIOS_PATH))
    disk_ids = {s["metadata"]["id"] for s in disk_scenarios}

    # Merge: disk scenarios not in DB
    all_scenarios = list(db_scenarios)
    for ds in disk_scenarios:
        meta = ds["metadata"]
        if meta["id"] not in {s.id for s in db_scenarios}:
            scenario = Scenario(
                id=meta["id"],
                name=meta["name"],
                difficulty=meta["difficulty"],
                tags_json=json.dumps(meta.get("tags", [])),
                ai_generated=meta.get("ai_generated", False),
                yaml_content="",  # lazy
                wargame_enabled=bool(ds.get("wargame")),
            )
            all_scenarios.append(scenario)

    results = []
    for s in all_scenarios:
        tags = json.loads(s.tags_json) if s.tags_json else []
        if difficulty and s.difficulty != difficulty:
            continue
        if tag and tag not in tags:
            continue
        results.append(ScenarioSummary(
            id=s.id,
            name=s.name,
            difficulty=s.difficulty,
            tags=tags,
            ai_generated=s.ai_generated,
            is_public=s.is_public,
            download_count=s.download_count,
            wargame_enabled=s.wargame_enabled,
            rating=s.rating,
            created_at=s.created_at,
        ))

    return results


@router.get("/{scenario_id}", response_model=ScenarioSummary)
def get_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    scenario = db.exec(select(Scenario).where(Scenario.id == scenario_id)).first()
    if not scenario:
        # Try disk
        from app.services.scenario_loader import load_scenario_from_db_or_disk
        try:
            data = load_scenario_from_db_or_disk(scenario_id)
            meta = data["metadata"]
            return ScenarioSummary(
                id=meta["id"],
                name=meta["name"],
                difficulty=meta["difficulty"],
                tags=meta.get("tags", []),
                ai_generated=meta.get("ai_generated", False),
                is_public=True,
                download_count=0,
                wargame_enabled=bool(data.get("wargame")),
                rating=None,
                created_at=datetime.utcnow(),
            )
        except ScenarioValidationError:
            raise HTTPException(status_code=404, detail="Scenario not found")

    return ScenarioSummary(
        id=scenario.id,
        name=scenario.name,
        difficulty=scenario.difficulty,
        tags=json.loads(scenario.tags_json),
        ai_generated=scenario.ai_generated,
        is_public=scenario.is_public,
        download_count=scenario.download_count,
        wargame_enabled=scenario.wargame_enabled,
        rating=scenario.rating,
        created_at=scenario.created_at,
    )


@router.get("/{scenario_id}/yaml")
def get_scenario_yaml(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    from app.services.scenario_loader import load_scenario_from_db_or_disk
    try:
        data = load_scenario_from_db_or_disk(scenario_id, db)
        import yaml
        return {"yaml": yaml.dump(data, default_flow_style=False)}
    except ScenarioValidationError:
        raise HTTPException(status_code=404, detail="Scenario not found")


@router.post("", response_model=ScenarioSummary, status_code=201)
async def upload_scenario(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    content = await file.read()
    try:
        data = load_yaml(content.decode())
        validate_scenario(data, settings.allowed_images_list)
    except ScenarioValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    meta = data["metadata"]
    existing = db.get(Scenario, meta["id"])
    if existing and existing.owner_user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Scenario ID already exists")

    import yaml
    scenario = Scenario(
        id=meta["id"],
        name=meta["name"],
        difficulty=meta["difficulty"],
        tags_json=json.dumps(meta.get("tags", [])),
        ai_generated=meta.get("ai_generated", False),
        yaml_content=content.decode(),
        is_public=True,
        owner_user_id=current_user.id,
        wargame_enabled=bool(data.get("wargame")),
        updated_at=datetime.utcnow(),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return ScenarioSummary(
        id=scenario.id,
        name=scenario.name,
        difficulty=scenario.difficulty,
        tags=json.loads(scenario.tags_json),
        ai_generated=scenario.ai_generated,
        is_public=scenario.is_public,
        download_count=scenario.download_count,
        wargame_enabled=scenario.wargame_enabled,
        rating=scenario.rating,
        created_at=scenario.created_at,
    )
