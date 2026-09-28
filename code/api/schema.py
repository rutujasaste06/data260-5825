from pydantic import BaseModel, Field, EmailStr


class TrialCreate(BaseModel):
    trial_title: str = Field(min_length=1)
    nct_number: str = Field(min_length=1)


class TrialUpdate(BaseModel):
    trial_title: str = Field(min_length=1)
    nct_number: str = Field(min_length=1)


class TrialOut(BaseModel):
    id: int
    trial_title: str
    nct_number: str

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