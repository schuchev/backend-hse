from typing import Optional
from pydantic import BaseModel, Field


class ModerationResultResponse(BaseModel):
    task_id: int = Field(description="ID записи moderation_results")
    status: str = Field(description="pending/completed/failed")
    is_violation: Optional[bool] = Field(default=None, description="NULL пока pending")
    probability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="NULL пока pending")
