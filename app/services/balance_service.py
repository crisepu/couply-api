import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.expense import Expense, ExpenseType
from app.models.couple import Couple, SplitMode
from app.models.user import User


async def _resolve_split_percentages(
    db: AsyncSession, couple: Couple
) -> tuple[Decimal, Decimal]:
    if couple.split_mode == SplitMode.equal:
        return Decimal("50"), Decimal("50")

    if couple.split_mode == SplitMode.custom:
        if couple.percentage_user1 is None or couple.percentage_user2 is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Custom split mode requires percentages to be set via PUT /couple/split",
            )
        return Decimal(str(couple.percentage_user1)), Decimal(str(couple.percentage_user2))

    # auto: calculate from salaries in real time
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
    pct_u1 = (Decimal(str(u1.salary)) / total * 100).quantize(Decimal("0.01"))
    pct_u2 = (Decimal("100") - pct_u1).quantize(Decimal("0.01"))
    return pct_u1, pct_u2


async def calculate_balance(db: AsyncSession, current_user: User) -> dict:
    if current_user.couple_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not in a couple")

    result = await db.execute(select(Couple).where(Couple.id == current_user.couple_id))
    couple = result.scalar_one_or_none()
    if not couple:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couple not found")
    if couple.user2_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Couple is not complete yet")

    # Global percentages (used when no split_override on expense)
    global_pct_u1, global_pct_u2 = await _resolve_split_percentages(db, couple)

    # Get all shared expenses
    result = await db.execute(
        select(Expense).where(
            Expense.couple_id == couple.id,
            Expense.type == ExpenseType.shared,
        )
    )
    expenses = result.scalars().all()

    # net_u1: positive = u1 is owed money, negative = u1 owes money
    net_u1 = Decimal("0")

    for expense in expenses:
        amount = Decimal(str(expense.amount))

        if expense.split_override_user1 is not None:
            pct_u1 = Decimal(str(expense.split_override_user1))
            pct_u2 = Decimal(str(expense.split_override_user2))
        else:
            pct_u1 = global_pct_u1
            pct_u2 = global_pct_u2

        debt_u1 = (amount * pct_u1 / 100).quantize(Decimal("0.01"))
        debt_u2 = (amount * pct_u2 / 100).quantize(Decimal("0.01"))

        if expense.paid_by == couple.user1_id:
            # u1 paid the full amount → u2 owes u1 their share
            net_u1 += debt_u2
        else:
            # u2 paid the full amount → u1 owes u2 their share
            net_u1 -= debt_u1

    balance = abs(net_u1).quantize(Decimal("0.01"))

    if net_u1 > Decimal("0.01"):
        debtor, creditor = couple.user2_id, couple.user1_id
    elif net_u1 < Decimal("-0.01"):
        debtor, creditor = couple.user1_id, couple.user2_id
    else:
        debtor, creditor = None, None

    return {
        "user1_id": couple.user1_id,
        "user2_id": couple.user2_id,
        "balance": balance,
        "debtor": debtor,
        "creditor": creditor,
    }
