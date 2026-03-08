import logging
import json
from typing import Optional
from cryptography.fernet import Fernet

from app.config import settings
from app.services.scenario_loader import load_yaml, validate_scenario, ScenarioValidationError

logger = logging.getLogger(__name__)

SCENARIO_PROMPT = """You are a pentest lab designer. Generate a valid PwnLab scenario YAML.

Rules:
- Allowed images ONLY: {allowed_images}
- Use subnet template "{base_subnet}.{{session_offset}}.0/24" literally (with curly braces)
- Target IPs must be "{base_subnet}.{{session_offset}}.X" format
- All flags must use PWNLAB{{}} format
- schema_version must be "1.0"
- difficulty must be one of: beginner, intermediate, advanced, expert
- attacker.tool_profile must be one of: web, network, crypto, full

User request: {prompt}
Difficulty: {difficulty}
Tags: {tags}
Include wargame detection: {wargame}

Output ONLY raw YAML. No markdown fences. No explanation. No comments.
"""


def decrypt_gemini_key(encrypted_key: str) -> str:
    """Decrypt a Fernet-encrypted Gemini API key."""
    f = Fernet(settings.FERNET_KEY.encode())
    return f.decrypt(encrypted_key.encode()).decode()


def encrypt_gemini_key(raw_key: str) -> str:
    """Encrypt a Gemini API key for storage."""
    f = Fernet(settings.FERNET_KEY.encode())
    return f.encrypt(raw_key.encode()).decode()


async def generate_scenario(
    prompt: str,
    difficulty: str = "beginner",
    tags: list = None,
    wargame: bool = False,
    gemini_api_key: Optional[str] = None,
    encrypted_key: Optional[str] = None,
) -> dict:
    """Generate a scenario using Gemini API. Returns validated scenario dict."""
    import google.generativeai as genai

    # Resolve API key
    api_key = gemini_api_key
    if not api_key and encrypted_key:
        api_key = decrypt_gemini_key(encrypted_key)
    if not api_key:
        raise ValueError("No Gemini API key available")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    prompt_text = SCENARIO_PROMPT.format(
        allowed_images=", ".join(settings.allowed_images_list),
        base_subnet=settings.PWNLAB_BASE_SUBNET,
        prompt=prompt,
        difficulty=difficulty,
        tags=", ".join(tags or []),
        wargame="yes" if wargame else "no",
    )

    response = model.generate_content(prompt_text)
    yaml_content = response.text.strip()

    # Remove any markdown fences if present
    if yaml_content.startswith("```"):
        lines = yaml_content.split("\n")
        yaml_content = "\n".join(lines[1:-1])

    # Validate the generated YAML
    data = load_yaml(yaml_content)
    validated = validate_scenario(data, settings.allowed_images_list)
    validated["_raw_yaml"] = yaml_content
    validated["metadata"]["ai_generated"] = True

    return validated


async def pick_blackbox_scenario(wargame_only: bool = True, db=None) -> str:
    """Pick a random scenario ID for blackbox mode."""
    import random
    from pathlib import Path
    from app.services.scenario_loader import list_scenarios_from_disk

    scenarios_path = Path(settings.SCENARIOS_PATH)
    all_scenarios = list_scenarios_from_disk(scenarios_path)

    if wargame_only:
        candidates = [
            s["metadata"]["id"]
            for s in all_scenarios
            if s.get("wargame", {}) and s["wargame"].get("enabled", False)
        ]
    else:
        candidates = [s["metadata"]["id"] for s in all_scenarios]

    if not candidates:
        # Fall back to any scenario
        candidates = [s["metadata"]["id"] for s in all_scenarios]

    if not candidates:
        raise ValueError("No scenarios available for blackbox mode")

    return random.choice(candidates)
