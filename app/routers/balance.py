import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import balance_service

router = APIRouter(prefix="/balance", tags=["balance"])


class BalanceResponse(BaseModel):
    user1_id: uuid.UUID
    user2_id: uuid.UUID
    balance: Decimal
    debtor: uuid.UUID | None
    creditor: uuid.UUID | None
    summary: str


@router.get("", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await balance_service.calculate_balance(db, current_user)
