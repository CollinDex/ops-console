"""Staff list models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    created_at: datetime
