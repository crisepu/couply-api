import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, model_validator
from app.models.expense import ExpenseType


class ExpenseCreate(BaseModel):
    type: ExpenseType
    amount: Decimal
    category: str
    description: str | None = None
    expense_date: date
    paid_by: uuid.UUID
    split_override_user1: Decimal | None = None
    split_override_user2: Decimal | None = None

    @model_validator(mode="after")
    def validate_overrides(self):
        one_set = (self.split_override_user1 is None) != (self.split_override_user2 is None)
        if one_set:
            raise ValueError("Ambos split_override deben estar presentes o ninguno")
        if self.split_override_user1 is not None:
            total = self.split_override_user1 + self.split_override_user2
            if abs(total - Decimal("100")) > Decimal("0.01"):
                raise ValueError("split_override_user1 + split_override_user2 debe sumar 100")
        return self


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = None
    category: str | None = None
    description: str | None = None
    expense_date: date | None = None
    paid_by: uuid.UUID | None = None
    split_override_user1: Decimal | None = None
    split_override_user2: Decimal | None = None

    @model_validator(mode="after")
    def validate_overrides(self):
        one_set = (self.split_override_user1 is None) != (self.split_override_user2 is None)
        if one_set:
            raise ValueError("Ambos split_override deben estar presentes o ninguno")
        if self.split_override_user1 is not None:
            total = self.split_override_user1 + self.split_override_user2
            if abs(total - Decimal("100")) > Decimal("0.01"):
                raise ValueError("split_override_user1 + split_override_user2 debe sumar 100")
        return self


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    couple_id: uuid.UUID
    created_by: uuid.UUID
    type: ExpenseType
    amount: Decimal
    category: str
    description: str | None
    expense_date: date
    paid_by: uuid.UUID
    split_override_user1: Decimal | None
    split_override_user2: Decimal | None

    model_config = {"from_attributes": True}
