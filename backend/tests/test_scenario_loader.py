import pytest
from app.services.scenario_loader import (
    validate_scenario,
    ScenarioValidationError,
    resolve_template,
    apply_session_offset,
)
from app.config import settings

def test_resolve_template():
    # Test basic replacement
    assert resolve_template("10.100.{session_offset}.10", 5) == f"{settings.PWNLAB_BASE_SUBNET}.5.10"
    
    # Test with different base subnet
    original_subnet = settings.PWNLAB_BASE_SUBNET
    settings.PWNLAB_BASE_SUBNET = "192.168"
    assert resolve_template("10.100.{session_offset}.10", 5) == "192.168.5.10"
    settings.PWNLAB_BASE_SUBNET = original_subnet

def test_apply_session_offset():
    data = {
        "network": {"subnet": "10.100.{session_offset}.0/24"},
        "targets": [
            {"id": "target1", "ip": "10.100.{session_offset}.10"},
            {"id": "target2", "ip": "10.100.{session_offset}.20"}
        ]
    }
    
    resolved = apply_session_offset(data, 42)
    
    assert resolved["network"]["subnet"] == f"{settings.PWNLAB_BASE_SUBNET}.42.0/24"
    assert resolved["targets"][0]["ip"] == f"{settings.PWNLAB_BASE_SUBNET}.42.10"
    assert resolved["targets"][1]["ip"] == f"{settings.PWNLAB_BASE_SUBNET}.42.20"
    
    # Ensure original data is not mutated
    assert data["network"]["subnet"] == "10.100.{session_offset}.0/24"

def test_validate_scenario_valid():
    valid_data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "test-lab",
            "name": "Test Lab",
            "difficulty": "beginner",
            "tags": ["test"]
        },
        "network": {
            "subnet": "10.100.{session_offset}.0/24"
        },
        "targets": [
            {
                "id": "target1",
                "image": "allowed-image:latest",
                "ip": "10.100.{session_offset}.10"
            }
        ],
        "attacker": {
            "tool_profile": "web"
        },
        "objectives": [
            {
                "id": "flag1",
                "validation": {
                    "method": "flag_string",
                    "value": "PWNLAB{test}"
                }
            }
        ]
    }
    
    # Should not raise an exception
    validated = validate_scenario(valid_data, allowed_images=["allowed-image:latest"])
    assert validated == valid_data

def test_validate_scenario_invalid_image():
    invalid_data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "test-lab",
            "name": "Test Lab",
            "difficulty": "beginner",
            "tags": ["test"]
        },
        "network": {
            "subnet": "10.100.{session_offset}.0/24"
        },
        "targets": [
            {
                "id": "target1",
                "image": "malicious-image:latest",
                "ip": "10.100.{session_offset}.10"
            }
        ],
        "attacker": {
            "tool_profile": "web"
        },
        "objectives": [
            {
                "id": "flag1",
                "validation": {
                    "method": "flag_string",
                    "value": "PWNLAB{test}"
                }
            }
        ]
    }
    
    with pytest.raises(ScenarioValidationError, match="not in allowed images whitelist"):
        validate_scenario(invalid_data, allowed_images=["allowed-image:latest"])

def test_validate_scenario_missing_required_field():
    invalid_data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "test-lab",
            "name": "Test Lab",
            "difficulty": "beginner",
            "tags": ["test"]
        },
        # Missing network
        "targets": [
            {
                "id": "target1",
                "image": "allowed-image:latest",
                "ip": "10.100.{session_offset}.10"
            }
        ],
        "attacker": {
            "tool_profile": "web"
        },
        "objectives": []
    }
    
    with pytest.raises(ScenarioValidationError, match="Schema validation failed"):
        validate_scenario(invalid_data, allowed_images=["allowed-image:latest"])
