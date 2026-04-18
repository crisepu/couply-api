import uuid
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, model_validator
from app.models.couple import SplitMode


class JoinCoupleRequest(BaseModel):
    invite_code: str


class UpdateSplitRequest(BaseModel):
    split_mode: SplitMode
    percentage_user1: Decimal | None = None
    percentage_user2: Decimal | None = None

    @model_validator(mode="after")
    def validate_custom_percentages(self):
        if self.split_mode == SplitMode.custom:
            if self.percentage_user1 is None or self.percentage_user2 is None:
                raise ValueError("Both percentages are required for custom split mode")
            total = self.percentage_user1 + self.percentage_user2
            if abs(total - 100) > Decimal("0.01"):
                raise ValueError("Percentages must sum to 100")
        return self


class CoupleResponse(BaseModel):
    id: uuid.UUID
    user1_id: uuid.UUID
    user2_id: uuid.UUID | None
    split_mode: SplitMode
    percentage_user1: Decimal | None
    percentage_user2: Decimal | None
    invite_code: str

    model_config = {"from_attributes": True}
