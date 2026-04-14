from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ActionExecutionCreate(BaseModel):
    corrective_action_id: int
    comment: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None


class ActionExecutionResponse(BaseModel):
    id: int
    corrective_action_id: int
    comment: Optional[str] = None
    is_completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
