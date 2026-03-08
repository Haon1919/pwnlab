from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "PwnLab"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production-use-32-char-min"

    # Database
    DATABASE_URL: str = "sqlite:///./pwnlab.db"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Docker
    DOCKER_SOCKET: str = "unix:///var/run/docker.sock"
    PWNLAB_ALLOWED_TARGET_IMAGES: str = "pwnlab/target-dvwa:latest,pwnlab/target-webgoat:latest,pwnlab/target-metasploitable-lite:latest,vulnerables/web-dvwa:latest,webgoat/goat-and-wolf:latest"
    PWNLAB_ATTACKER_BASE_IMAGE: str = "pwnlab/attacker-base:latest"
    PWNLAB_ATTACKER_KALI_IMAGE: str = "pwnlab/attacker-kali:latest"
    PWNLAB_WARGAME_SIDECAR_IMAGE: str = "pwnlab/wargame-sidecar:latest"

    # Session
    SESSION_TIMEOUT_HOURS: int = 4
    MAX_SUBNET_OFFSET: int = 254
    PWNLAB_BASE_SUBNET: str = "10.100"

    # Encryption key for Gemini API keys at rest
    FERNET_KEY: str = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="

    # Scenarios path
    SCENARIOS_PATH: str = "/app/scenarios"

    # Gemini
    GEMINI_MODEL: str = "gemini-1.5-flash"

    @property
    def allowed_images_list(self) -> List[str]:
        return [img.strip() for img in self.PWNLAB_ALLOWED_TARGET_IMAGES.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()
