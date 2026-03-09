from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import hashlib
import secrets

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    gemini_api_key_encrypted: Optional[str] = None  # Fernet-encrypted
    plan: str = Field(default="free")  # free | pro | enterprise
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    sessions: List["LabSession"] = Relationship(back_populates="user")
    api_keys: List["APIKey"] = Relationship(back_populates="user")


class APIKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str = Field(unique=True, index=True)  # sha256 of raw key
    user_id: int = Field(foreign_key="user.id")
    label: str = Field(default="default")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

    user: Optional[User] = Relationship(back_populates="api_keys")

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @staticmethod
    def generate_raw_key() -> str:
        return f"blaqliq_{secrets.token_urlsafe(32)}"
