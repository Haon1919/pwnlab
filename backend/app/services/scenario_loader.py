import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError
from app.config import settings

logger = logging.getLogger(__name__)

SCENARIO_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "metadata", "network", "targets", "attacker", "objectives"],
    "properties": {
        "schema_version": {"type": "string"},
        "metadata": {
            "type": "object",
            "required": ["id", "name", "difficulty", "tags"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced", "expert"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "ai_generated": {"type": "boolean"},
            }
        },
        "network": {
            "type": "object",
            "required": ["subnet"],
            "properties": {
                "subnet": {"type": "string"},
                "internal": {"type": "boolean"},
            }
        },
        "targets": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "image", "ip"],
                "properties": {
                    "id": {"type": "string"},
                    "image": {"type": "string"},
                    "ip": {"type": "string"},
                    "mem_limit": {"type": "string"},
                    "cpu_quota": {"type": "integer"},
                }
            }
        },
        "attacker": {
            "type": "object",
            "required": ["tool_profile"],
            "properties": {
                "tool_profile": {"type": "string", "enum": ["web", "network", "crypto", "full"]},
                "kali": {"type": "boolean"},
            }
        },
        "objectives": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "validation"],
                "properties": {
                    "id": {"type": "string"},
                    "validation": {
                        "type": "object",
                        "required": ["method", "value"],
                        "properties": {
                            "method": {"type": "string"},
                            "value": {"type": "string"},
                        }
                    }
                }
            }
        },
        "wargame": {
            "type": ["object", "null"],
        }
    }
}


class ScenarioValidationError(Exception):
    pass


def load_yaml(content: str) -> Dict[str, Any]:
    """Parse YAML content."""
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ScenarioValidationError(f"YAML parse error: {e}")


def validate_scenario(data: Dict[str, Any], allowed_images: Optional[list] = None) -> Dict[str, Any]:
    """Validate scenario dict against schema and image whitelist."""
    try:
        validate(instance=data, schema=SCENARIO_SCHEMA)
    except ValidationError as e:
        raise ScenarioValidationError(f"Schema validation failed: {e.message}")

    # Validate images against whitelist
    if allowed_images:
        for target in data.get("targets", []):
            image = target.get("image", "")
            if image not in allowed_images:
                raise ScenarioValidationError(
                    f"Image '{image}' not in allowed images whitelist. "
                    f"Allowed: {allowed_images}"
                )

    return data


def load_scenario_file(path: Path) -> Dict[str, Any]:
    """Load and validate a scenario from a YAML file."""
    if not path.exists():
        raise ScenarioValidationError(f"Scenario file not found: {path}")
    content = path.read_text()
    data = load_yaml(content)
    return validate_scenario(data, settings.allowed_images_list)


def load_scenario_from_db_or_disk(scenario_id: str, db=None) -> Dict[str, Any]:
    """Load scenario by ID, checking DB first then disk."""
    if db:
        from sqlmodel import select
        from app.models.scenario import Scenario
        scenario = db.exec(select(Scenario).where(Scenario.id == scenario_id)).first()
        if scenario:
            data = load_yaml(scenario.yaml_content)
            return validate_scenario(data, settings.allowed_images_list)

    # Fall back to disk
    scenarios_path = Path(settings.SCENARIOS_PATH)
    for yaml_file in scenarios_path.rglob("*.yaml"):
        if yaml_file.name == "_schema.yaml":
            continue
        try:
            data = load_scenario_file(yaml_file)
            if data.get("metadata", {}).get("id") == scenario_id:
                return data
        except ScenarioValidationError:
            continue

    raise ScenarioValidationError(f"Scenario '{scenario_id}' not found")


def resolve_template(template: str, session_offset: int) -> str:
    """Replace {session_offset} template variables."""
    template = template.replace("10.100", settings.BLAQLIQ_BASE_SUBNET)
    return template.replace("{session_offset}", str(session_offset))


def apply_session_offset(data: Dict[str, Any], session_offset: int) -> Dict[str, Any]:
    """Apply session offset to all template strings in scenario."""
    import copy
    data = copy.deepcopy(data)

    # Network subnet
    if "network" in data:
        data["network"]["subnet"] = resolve_template(
            data["network"].get("subnet", ""), session_offset
        )

    # Target IPs
    for target in data.get("targets", []):
        target["ip"] = resolve_template(target.get("ip", ""), session_offset)

    return data


def list_scenarios_from_disk(scenarios_path: Path) -> list:
    """List all valid scenarios from the scenarios directory."""
    results = []
    for yaml_file in scenarios_path.rglob("*.yaml"):
        if yaml_file.name == "_schema.yaml":
            continue
        try:
            data = load_scenario_file(yaml_file)
            results.append(data)
        except ScenarioValidationError as e:
            logger.warning(f"Skipping invalid scenario {yaml_file}: {e}")
    return results
