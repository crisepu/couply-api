import uuid
from calendar import monthrange
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.expense import Expense, ExpenseType
from app.models.couple import Couple
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


async def _get_couple(db: AsyncSession, user: User) -> Couple:
    if user.couple_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not in a couple")
    result = await db.execute(select(Couple).where(Couple.id == user.couple_id))
    couple = result.scalar_one_or_none()
    if not couple:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couple not found")
    if couple.user2_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Couple is not complete yet")
    return couple


def _resolve_visible_to(expense_type: ExpenseType, couple: Couple, created_by: uuid.UUID) -> list[str]:
    if expense_type == ExpenseType.shared:
        return [str(couple.user1_id), str(couple.user2_id)]
    return [str(created_by)]


async def create_expense(db: AsyncSession, current_user: User, data: ExpenseCreate) -> Expense:
    couple = await _get_couple(db, current_user)

    valid_payers = {couple.user1_id, couple.user2_id}
    if data.paid_by not in valid_payers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="paid_by must be one of the couple's users")

    visible_to = _resolve_visible_to(data.type, couple, current_user.id)

    expense = Expense(
        couple_id=couple.id,
        created_by=current_user.id,
        type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description,
        expense_date=data.expense_date,
        paid_by=data.paid_by,
        split_override_user1=data.split_override_user1,
        split_override_user2=data.split_override_user2,
        visible_to=visible_to,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return expense


async def list_expenses(
    db: AsyncSession,
    current_user: User,
    type_filter: ExpenseType | None = None,
    month: str | None = None,
) -> list[Expense]:
    if current_user.couple_id is None:
        return []

    stmt = select(Expense).where(Expense.couple_id == current_user.couple_id)

    if type_filter is not None:
        stmt = stmt.where(Expense.type == type_filter)

    if month is not None:
        try:
            year, mon = int(month[:4]), int(month[5:7])
            start = date(year, mon, 1)
            last_day = monthrange(year, mon)[1]
            end = date(year, mon, last_day)
            stmt = stmt.where(Expense.expense_date >= start, Expense.expense_date <= end)
        except (ValueError, IndexError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be in YYYY-MM format")

    result = await db.execute(stmt)
    expenses = result.scalars().all()
    return [e for e in expenses if str(current_user.id) in e.visible_to]


async def _get_visible_expense(db: AsyncSession, expense_id: uuid.UUID, current_user: User) -> Expense:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense or str(current_user.id) not in expense.visible_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


async def update_expense(db: AsyncSession, expense_id: uuid.UUID, current_user: User, data: ExpenseUpdate) -> Expense:
    expense = await _get_visible_expense(db, expense_id, current_user)
    if expense.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can edit this expense")

    couple = await _get_couple(db, current_user)

    if data.paid_by is not None:
        valid_payers = {couple.user1_id, couple.user2_id}
        if data.paid_by not in valid_payers:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="paid_by must be one of the couple's users")
        expense.paid_by = data.paid_by

    if data.amount is not None:
        expense.amount = data.amount
    if data.category is not None:
        expense.category = data.category
    if data.description is not None:
        expense.description = data.description
    if data.expense_date is not None:
        expense.expense_date = data.expense_date

    # Handle split_override together (validator ensures both or neither)
    if data.split_override_user1 is not None:
        expense.split_override_user1 = data.split_override_user1
        expense.split_override_user2 = data.split_override_user2
    elif data.split_override_user1 is None and data.split_override_user2 is None:
        # Explicit clear only if both are explicitly None in the payload — keep existing if not sent
        pass

    await db.flush()
    await db.refresh(expense)
    return expense


async def delete_expense(db: AsyncSession, expense_id: uuid.UUID, current_user: User) -> None:
    expense = await _get_visible_expense(db, expense_id, current_user)
    if expense.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can delete this expense")
    await db.delete(expense)
    await db.flush()
