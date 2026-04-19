import secrets
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.couple import Couple, SplitMode
from app.schemas.couple import UpdateSplitRequest


async def create_couple(db: AsyncSession, current_user: User) -> Couple:
    if current_user.couple_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in a couple",
        )
    invite_code = secrets.token_urlsafe(8)
    couple = Couple(
        user1_id=current_user.id,
        invite_code=invite_code,
    )
    db.add(couple)
    await db.flush()
    current_user.couple_id = couple.id
    await db.flush()
    await db.refresh(couple)
    return couple


async def join_couple(db: AsyncSession, current_user: User, invite_code: str) -> Couple:
    if current_user.couple_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in a couple",
        )
    result = await db.execute(select(Couple).where(Couple.invite_code == invite_code))
    couple = result.scalar_one_or_none()
    if not couple:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code",
        )
    if couple.user2_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This couple is already complete",
        )
    if couple.user1_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join your own couple",
        )
    couple.user2_id = current_user.id
    current_user.couple_id = couple.id
    await db.flush()
    await db.refresh(couple)
    return couple


async def get_couple_for_user(db: AsyncSession, current_user: User) -> Couple:
    if current_user.couple_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not in a couple",
        )
    result = await db.execute(select(Couple).where(Couple.id == current_user.couple_id))
    couple = result.scalar_one_or_none()
    if not couple:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couple not found")
    return couple


async def update_split(db: AsyncSession, current_user: User, data: UpdateSplitRequest) -> Couple:
    couple = await get_couple_for_user(db, current_user)

    if data.split_mode == SplitMode.auto:
        result = await db.execute(
            select(User).where(User.id.in_([couple.user1_id, couple.user2_id]))
        )
        users = {u.id: u for u in result.scalars().all()}
        u1 = users.get(couple.user1_id)
        u2 = users.get(couple.user2_id)
        if not u1 or not u2 or u1.salary is None or u2.salary is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both users must have their salary set to use auto split mode",
            )
        total = Decimal(str(u1.salary)) + Decimal(str(u2.salary))
        couple.percentage_user1 = (Decimal(str(u1.salary)) / total * 100).quantize(Decimal("0.01"))
        couple.percentage_user2 = (Decimal("100") - couple.percentage_user1).quantize(Decimal("0.01"))
    elif data.split_mode == SplitMode.equal:
        couple.percentage_user1 = Decimal("50.00")
        couple.percentage_user2 = Decimal("50.00")
    else:
        couple.percentage_user1 = data.percentage_user1
        couple.percentage_user2 = data.percentage_user2

    couple.split_mode = data.split_mode
    await db.flush()
    await db.refresh(couple)
    return couple
