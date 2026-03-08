import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import Session, select

from app.models.session import LabSession
from app.models.user import User
from app.services.docker_manager import docker_manager
from app.services.scenario_loader import (
    load_scenario_from_db_or_disk,
    apply_session_offset,
    ScenarioValidationError,
)
from app.config import settings

logger = logging.getLogger(__name__)


def allocate_session_offset(db: Session) -> int:
    """Find an unused subnet offset (1-254)."""
    used = set(
        row.session_offset
        for row in db.exec(
            select(LabSession).where(LabSession.status.in_(["starting", "running"]))
        ).all()
        if row.session_offset is not None
    )
    available = [i for i in range(1, settings.MAX_SUBNET_OFFSET + 1) if i not in used]
    if not available:
        raise RuntimeError("No available subnet offsets")
    return random.choice(available)


def get_attacker_image(tool_profile: str, kali: bool, user: User) -> str:
    from app.dependencies import PLAN_LIMITS
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    if kali:
        if not limits["kali_access"]:
            raise PermissionError("Kali attacker requires pro or enterprise plan")
        return settings.PWNLAB_ATTACKER_KALI_IMAGE
    return settings.PWNLAB_ATTACKER_BASE_IMAGE


async def create_session(
    scenario_id: str,
    user: User,
    db: Session,
    wargame: bool = False,
    blackbox: bool = False,
) -> LabSession:
    """Orchestrate: load scenario -> allocate resources -> spin up Docker -> persist."""
    # Load scenario
    scenario_data = load_scenario_from_db_or_disk(scenario_id, db)

    # Allocate session offset
    offset = allocate_session_offset(db)

    # Apply offset to scenario
    resolved = apply_session_offset(scenario_data, offset)

    # Create session record
    session = LabSession(
        user_id=user.id,
        scenario_id=scenario_id,
        status="starting",
        mode="wargame" if wargame else "standard",
        blackbox=blackbox,
        session_offset=offset,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        # Create Docker network
        network_name = f"pwnlab-{session.id[:8]}"
        subnet = resolved["network"]["subnet"]
        internal = resolved["network"].get("internal", True)
        docker_manager.create_network(network_name, subnet, internal=internal)
        session.docker_network_name = network_name

        container_ids = []

        # Start target containers
        for target in resolved["targets"]:
            cname = f"pwnlab-target-{target['id']}-{session.id[:8]}"
            cid = docker_manager.run_target(
                image=target["image"],
                container_name=cname,
                network_name=network_name,
                ip_address=target["ip"],
                mem_limit=target.get("mem_limit", "512m"),
                cpu_quota=target.get("cpu_quota", 50000),
            )
            container_ids.append(cid)

        # Start attacker container
        attacker_cfg = resolved.get("attacker", {})
        kali = attacker_cfg.get("kali", False)
        attacker_image = get_attacker_image(attacker_cfg.get("tool_profile", "web"), kali, user)

        # Build attacker IP (one above the subnet base)
        subnet_base = subnet.rsplit(".", 1)[0]
        attacker_ip = f"{subnet_base}.100"

        env_vars = {}
        if not blackbox:
            for target in resolved["targets"]:
                env_key = f"TARGET_{target['id'].upper()}_IP"
                env_vars[env_key] = target["ip"]

        attacker_cname = f"pwnlab-attacker-{session.id[:8]}"
        attacker_cid = docker_manager.run_attacker(
            image=attacker_image,
            container_name=attacker_cname,
            network_name=network_name,
            ip_address=attacker_ip,
            environment=env_vars,
            kali=kali,
            net_admin=True,
        )
        container_ids.append(attacker_cid)

        # Start wargame sidecar if needed
        if wargame and resolved.get("wargame", {}) and resolved["wargame"].get("enabled", False):
            volume_name = f"pwnlab-events-{session.id[:8]}"
            docker_manager.create_volume(volume_name)
            sidecar_cname = f"pwnlab-sidecar-{session.id[:8]}"
            sidecar_cid = docker_manager.run_wargame_sidecar(
                container_name=sidecar_cname,
                network_name=network_name,
                events_volume=volume_name,
                session_id=session.id,
                target_container_id=container_ids[0],
            )
            container_ids.append(sidecar_cid)

        session.container_ids = container_ids
        session.status = "running"
        session.updated_at = datetime.utcnow()
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(f"Session {session.id} started with {len(container_ids)} containers")
        return session

    except Exception as e:
        logger.error(f"Failed to create session {session.id}: {e}")
        # Cleanup
        try:
            docker_manager.teardown_session(
                container_ids=session.container_ids,
                network_name=session.docker_network_name or f"pwnlab-{session.id[:8]}",
            )
        except Exception as cleanup_err:
            logger.error(f"Cleanup error for session {session.id}: {cleanup_err}")

        session.status = "error"
        session.error_message = str(e)
        session.updated_at = datetime.utcnow()
        db.add(session)
        db.commit()
        raise


async def stop_session(session: LabSession, db: Session):
    """Stop a running session and clean up Docker resources."""
    session.status = "stopping"
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    try:
        volume_name = f"pwnlab-events-{session.id[:8]}" if session.mode == "wargame" else None
        docker_manager.teardown_session(
            container_ids=session.container_ids,
            network_name=session.docker_network_name or f"pwnlab-{session.id[:8]}",
            volume_name=volume_name,
        )

        session.status = "stopped"
        session.stopped_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        db.add(session)
        db.commit()
        logger.info(f"Session {session.id} stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping session {session.id}: {e}")
        session.status = "error"
        session.error_message = str(e)
        db.add(session)
        db.commit()
        raise
