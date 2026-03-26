from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class User(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str
    email: str
    hashed_password: str
    role: str  # 'Admin' | 'Supervisor' | 'Other'
    active_status: bool = True
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Supervisor"
    dpr_generation_permission: bool = False

class UserCreateAdmin(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Supervisor"
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)

class UserResponse(BaseModel):
    user_id: str
    organisation_id: str
    name: str
    email: str
    role: str
    active_status: bool
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active_status: Optional[bool] = None
    dpr_generation_permission: Optional[bool] = None
    assigned_projects: Optional[List[str]] = None
    screen_permissions: Optional[List[str]] = None

class UserProjectMap(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    organisation_id: str
    write_access: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
