from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class SponsorCreate(BaseModel):
    sponsor_name: str = Field(min_length=1)
    contact_person: str = Field(min_length=1)
    email: EmailStr


class SponsorUpdate(BaseModel):
    sponsor_name: str = Field(min_length=1)
    contact_person: str = Field(min_length=1)
    email: EmailStr


class SponsorOut(BaseModel):
    id: int
    sponsor_name: str
    contact_person: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TrialCreate(BaseModel):
    trial_title: str = Field(min_length=1)
    nct_number: str = Field(min_length=1)
    available_slots: int = Field(default=10, ge=0)
    sponsor_id: Optional[int] = None


class TrialUpdate(BaseModel):
    trial_title: str = Field(min_length=1)
    nct_number: str = Field(min_length=1)
    available_slots: int = Field(ge=0)
    sponsor_id: Optional[int] = None


class TrialOut(BaseModel):
    id: int
    trial_title: str
    nct_number: str
    available_slots: int
    sponsor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

#get all trials for a specific sponsor
class SponsorWithTrialsOut(BaseModel):
    id: int
    sponsor_name: str
    contact_person: str
    email: EmailStr
    trials: list[TrialOut] = []

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SiteOut(BaseModel):
    id: int
    site_name: str
    city: str

    class Config:
        from_attributes = True


class TrialWithSitesOut(BaseModel):
    id: int
    trial_title: str
    nct_number: str
    sites: list[SiteOut] = []

    class Config:
        from_attributes = True