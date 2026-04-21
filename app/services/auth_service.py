from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> User | None:
    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await get_user_by_firebase_uid(db, data.firebase_uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already registered",
        )
    user = User(
        firebase_uid=data.firebase_uid,
        email=data.email,
        name=data.name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    if data.name is not None:
        user.name = data.name
    if data.salary is not None:
        user.salary = data.salary
    await db.flush()
    await db.refresh(user)
    return user
