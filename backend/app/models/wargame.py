from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class WargameState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="labsession.id", unique=True)
    detection_score: int = Field(default=0)
    detection_level: str = Field(default="clean")  # clean | warning | detected | busted
    is_active: bool = Field(default=True)
    busted_at: Optional[datetime] = None
    won_at: Optional[datetime] = None
    last_poll_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    session: Optional["LabSession"] = Relationship(back_populates="wargame_state")
    events: List["DetectionEvent"] = Relationship(back_populates="wargame_state")


class DetectionEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    wargame_state_id: int = Field(foreign_key="wargamestate.id")
    event_type: str  # iptables_log | fail2ban_ban | auditd
    severity: str   # warning | detected | busted
    raw_log_line: str
    source_ip: Optional[str] = None
    score_delta: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    wargame_state: Optional[WargameState] = Relationship(back_populates="events")
