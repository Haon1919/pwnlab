from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
import json

class LabSession(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    scenario_id: str
    status: str = Field(default="starting")  # starting | running | stopping | stopped | error
    mode: str = Field(default="standard")  # standard | wargame
    blackbox: bool = Field(default=False)
    docker_network_name: Optional[str] = None
    container_ids_json: str = Field(default="[]")  # JSON list of container IDs
    session_offset: Optional[int] = None  # 1-254 for subnet allocation
    flags_captured_json: str = Field(default="[]")  # JSON list of captured flag IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    stopped_at: Optional[datetime] = None
    error_message: Optional[str] = None

    user: Optional["User"] = Relationship(back_populates="sessions")
    wargame_state: Optional["WargameState"] = Relationship(back_populates="session")

    @property
    def container_ids(self) -> List[str]:
        return json.loads(self.container_ids_json)

    @container_ids.setter
    def container_ids(self, value: List[str]):
        self.container_ids_json = json.dumps(value)

    @property
    def flags_captured(self) -> List[str]:
        return json.loads(self.flags_captured_json)

    @flags_captured.setter
    def flags_captured(self, value: List[str]):
        self.flags_captured_json = json.dumps(value)
