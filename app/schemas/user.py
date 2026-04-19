import uuid
from decimal import Decimal
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    firebase_uid: str
    email: EmailStr
    name: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    salary: Decimal | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    couple_id: uuid.UUID | None

    model_config = {"from_attributes": True}
