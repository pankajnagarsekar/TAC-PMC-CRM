from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class Organisation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class OrganisationCreate(BaseModel):
    name: str
