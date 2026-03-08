from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime

class Scenario(SQLModel, table=True):
    id: str = Field(primary_key=True)  # matches metadata.id in YAML
    name: str
    difficulty: str
    tags_json: str = Field(default="[]")  # JSON list
    ai_generated: bool = Field(default=False)
    yaml_content: str  # full YAML text
    is_public: bool = Field(default=True)
    download_count: int = Field(default=0)
    owner_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    rating: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    wargame_enabled: bool = Field(default=False)
