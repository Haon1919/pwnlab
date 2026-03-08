import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.models.wargame import WargameState, DetectionEvent
from app.models.session import LabSession

logger = logging.getLogger(__name__)

SCORE_MAP = {
    "warning": 10,
    "detected": 30,
    "busted": 100,
}

LEVEL_THRESHOLDS = {
    "warning": 10,
    "detected": 40,
    "busted": 100,
}


def score_to_level(score: int) -> str:
    if score >= LEVEL_THRESHOLDS["busted"]:
        return "busted"
    if score >= LEVEL_THRESHOLDS["detected"]:
        return "detected"
    if score >= LEVEL_THRESHOLDS["warning"]:
        return "warning"
    return "clean"


def parse_iptables_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse an iptables PWNLAB-DETECT log line."""
    if "PWNLAB-DETECT" not in line:
        return None

    event = {"type": "iptables_log", "raw": line}

    # Extract SRC IP
    src_match = re.search(r"SRC=(\S+)", line)
    if src_match:
        event["src_ip"] = src_match.group(1)

    # Extract DST port
    dpt_match = re.search(r"DPT=(\d+)", line)
    if dpt_match:
        event["dst_port"] = int(dpt_match.group(1))

    return event


def parse_fail2ban_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a fail2ban ban event."""
    if "Ban " not in line:
        return None

    ip_match = re.search(r"Ban (\S+)", line)
    jail_match = re.search(r"\[(\w+)\]", line)

    return {
        "type": "fail2ban_ban",
        "src_ip": ip_match.group(1) if ip_match else None,
        "jail": jail_match.group(1) if jail_match else "unknown",
        "raw": line,
    }


def parse_auditd_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse an auditd event line."""
    if "type=EXECVE" not in line and "type=SYSCALL" not in line:
        return None

    event = {"type": "auditd", "raw": line}

    key_match = re.search(r'key="([^"]+)"', line)
    if key_match:
        event["key"] = key_match.group(1)

    exe_match = re.search(r'exe="([^"]+)"', line)
    if exe_match:
        event["exe"] = exe_match.group(1)

    return event


def parse_jsonl_event(line: str) -> Optional[Dict[str, Any]]:
    """Parse a JSONL event from sidecar."""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def match_detection_rules(event: Dict[str, Any], detection_rules: Dict[str, Any]) -> Optional[str]:
    """Match an event against detection rules. Returns severity if matched, else None."""
    event_type = event.get("type", "")

    for rule_name, rule_config in detection_rules.items():
        backend = rule_config.get("backend", "")
        severity = rule_config.get("severity", "warning")

        if backend == "iptables" and event_type == "iptables_log":
            threshold = rule_config.get("threshold", {})
            # Simple match: any iptables log triggers warning
            return severity

        if backend == "fail2ban" and event_type == "fail2ban_ban":
            return severity

        if backend == "auditd" and event_type == "auditd":
            trigger = rule_config.get("trigger", "")
            # Check if event matches the auditd trigger pattern
            event_key = event.get("key", "")
            if rule_name in event_key or trigger.split(" ")[0] in event.get("exe", ""):
                return severity

    return None


def read_new_events(volume_path: str, last_offset: int) -> tuple[List[str], int]:
    """Read new JSONL lines from the sidecar events volume."""
    events_file = Path(volume_path) / "events.jsonl"
    if not events_file.exists():
        return [], last_offset

    lines = events_file.read_text().split("\n")
    new_lines = [l for l in lines[last_offset:] if l.strip()]
    return new_lines, last_offset + len(new_lines)


async def poll_wargame(session_id: str, db: Session):
    """Poll detection events for a wargame session. Called by APScheduler."""
    try:
        # Get session and wargame state
        session = db.get(LabSession, session_id)
        if not session or session.status != "running":
            return

        wargame_state = db.exec(
            select(WargameState).where(WargameState.session_id == session_id)
        ).first()

        if not wargame_state or not wargame_state.is_active:
            return

        # Load scenario for detection rules
        from app.services.scenario_loader import load_scenario_from_db_or_disk
        try:
            scenario_data = load_scenario_from_db_or_disk(session.scenario_id, db)
        except Exception as e:
            logger.error(f"Could not load scenario for wargame polling: {e}")
            return

        detection_rules = {}
        wargame_cfg = scenario_data.get("wargame", {})
        if wargame_cfg:
            detection_rules = wargame_cfg.get("detection_rules", {})

        # Read new events from sidecar volume
        volume_path = f"/var/lib/docker/volumes/pwnlab-events-{session_id[:8]}/_data"
        last_offset = getattr(wargame_state, '_event_offset', 0)

        new_lines, new_offset = read_new_events(volume_path, last_offset)
        wargame_state._event_offset = new_offset

        score_delta = 0

        for line in new_lines:
            event = parse_jsonl_event(line)
            if not event:
                continue

            severity = match_detection_rules(event, detection_rules)
            if not severity:
                continue

            delta = SCORE_MAP.get(severity, 10)
            score_delta += delta

            det_event = DetectionEvent(
                wargame_state_id=wargame_state.id,
                event_type=event.get("type", "unknown"),
                severity=severity,
                raw_log_line=line,
                source_ip=event.get("src_ip"),
                score_delta=delta,
            )
            db.add(det_event)

            # Busted = instant game over
            if severity == "busted":
                wargame_state.detection_score = max(wargame_state.detection_score + delta, LEVEL_THRESHOLDS["busted"])
                wargame_state.detection_level = "busted"
                wargame_state.is_active = False
                wargame_state.busted_at = datetime.utcnow()
                db.add(wargame_state)
                db.commit()
                logger.info(f"Session {session_id} BUSTED")
                return

        if score_delta > 0:
            wargame_state.detection_score += score_delta
            wargame_state.detection_level = score_to_level(wargame_state.detection_score)

            if wargame_state.detection_score >= LEVEL_THRESHOLDS["busted"]:
                wargame_state.is_active = False
                wargame_state.busted_at = datetime.utcnow()

        wargame_state.last_poll_at = datetime.utcnow()
        db.add(wargame_state)
        db.commit()

    except Exception as e:
        logger.error(f"Error polling wargame {session_id}: {e}")
