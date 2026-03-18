from pydantic import BaseModel , EmailStr
from datetime import datetime
from typing import List , Optional

# --- Organization Schemas ---
class OrganisationBase(BaseModel):
    name : str

class OrganisationCreate(OrganisationBase):
    pass 

class OrganisationResponse(OrganisationBase):
    id : int
    created_at : datetime

    class Config:
        from_attributes = True # Tells Pydantic to read data from a SQLAlchemy model

class OrganisationUpdate(BaseModel):
    name : Optional[str] = None


# --- User Schemas ---
class UserBase(BaseModel):
    email : EmailStr
    role : str

class UserCreate(UserBase):
    password : str
    organisation_id : int

class UserResponse(UserBase):
    id : int
    organisation_id : int
    is_admin : bool = False

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email : Optional[EmailStr] = None
    role : Optional[str] = None
    password : Optional[str] = None

# --- Training Job Schemas ---
class TrainingJobBase(BaseModel):
    name : str
    model_template : str
    total_rounds : int = 5
    aggregation_algorithm : str = "FedAvg"

class TrainingJobCreate(TrainingJobBase):
    organisation_id : int

class TrainingJobResponse(TrainingJobBase):
    id : int
    organisation_id : int

    class Config:
        from_attributes = True

class TrainingJobUpdate(BaseModel):
    name : Optional[str] = None
    total_rounds : Optional[int] = None
    aggregation_algorithm : Optional[str] = None

class Token(BaseModel):
    access_token : str
    token_type : str