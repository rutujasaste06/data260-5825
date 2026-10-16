#Pydantic validation

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Status(str, Enum):
    recruiting = "recruiting"
    active = "active"
    completed = "completed"
    withdrawn = "withdrawn"

class Phase(str, Enum):
    phase1 = "phase1"
    phase2 = "phase2"
    phase3 = "phase3"
    phase4 = "phase4"

class TrialIn(BaseModel):
    trial_title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    status: Status = Status.recruiting
    phase: Phase
    start_date: datetime

class TrialOut(TrialIn):
    id: str
    created_at: datetime
    updated_at: datetime

class TrialUpdate(BaseModel):
    trial_title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[Status] = None
    phase: Optional[Phase] = None
    start_date: Optional[datetime] = None