# MongoDB Pydantic v2 Models
from datetime import datetime
from typing import Optional, List, Annotated
from bson import ObjectId
from pydantic import BaseModel, Field, BeforeValidator

# PyObjectId for MongoDB _id fields
def validate_object_id(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")

PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: str
    hashed_password: str
    role: str  # 'Admin' | 'Supervisor' | 'Other'
    org_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class Organisation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class Project(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    org_id: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class DPR(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    created_by: str
    date: datetime
    notes: str
    photos: List[str] = Field(default_factory=list)
    status: str = "draft"  # 'draft' | 'submitted' | 'approved' | 'rejected'
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class PettyCash(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    created_by: str
    amount: float
    purpose: str
    receipt_photo: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class Attendance(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    selfie_url: str
    gps_lat: float
    gps_lng: float
    check_in_time: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
