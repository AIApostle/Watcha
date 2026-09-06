"""Agent schemas — models for agent status, runs, and control."""

from pydantic import BaseModel
from datetime import datetime


class AgentStatus(BaseModel):
    is_running: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    total_runs: int = 0
    active_users: int = 0


class AgentRunResponse(BaseModel):
    id: str
    user_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str  # running | completed | failed
    sources_checked: int = 0
    items_found: int = 0
    alerts_generated: int = 0
    error_log: str | None = None


class AgentControlResponse(BaseModel):
    success: bool
    message: str
    status: AgentStatus
