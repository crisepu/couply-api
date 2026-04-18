from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.schemas.couple import CoupleResponse, JoinCoupleRequest, UpdateSplitRequest
from app.services import couple_service
from app.models.user import User

router = APIRouter(prefix="/couple", tags=["couple"])


@router.post("", response_model=CoupleResponse, status_code=status.HTTP_201_CREATED)
async def create_couple(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await couple_service.create_couple(db, current_user)


@router.post("/join", response_model=CoupleResponse)
async def join_couple(
    body: JoinCoupleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await couple_service.join_couple(db, current_user, body.invite_code)


@router.get("", response_model=CoupleResponse)
async def get_couple(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await couple_service.get_couple_for_user(db, current_user)


@router.put("/split", response_model=CoupleResponse)
async def update_split(
    body: UpdateSplitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await couple_service.update_split(db, current_user, body)
