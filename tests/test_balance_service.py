import uuid
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.services import balance_service
from app.services.balance_service import _resolve_split_percentages
from app.models.couple import SplitMode
from app.models.expense import Expense, ExpenseType


def _make_expense(couple_id, paid_by, amount, user1_id, user2_id,
                  split_override_user1=None, split_override_user2=None):
    e = Expense()
    e.id = uuid.uuid4()
    e.couple_id = couple_id
    e.created_by = user1_id
    e.type = ExpenseType.shared
    e.amount = Decimal(str(amount))
    e.category = "test"
    e.expense_date = date(2026, 4, 18)
    e.paid_by = paid_by
    e.split_override_user1 = split_override_user1
    e.split_override_user2 = split_override_user2
    e.visible_to = [str(user1_id), str(user2_id)]
    return e


class TestResolveSplitPercentages:
    async def test_equal_returns_50_50(self, complete_couple):
        db = AsyncMock()
        pct_u1, pct_u2 = await _resolve_split_percentages(db, complete_couple)
        assert pct_u1 == Decimal("50")
        assert pct_u2 == Decimal("50")

    async def test_custom_returns_stored_percentages(self, complete_couple):
        complete_couple.split_mode = SplitMode.custom
        complete_couple.percentage_user1 = Decimal("70")
        complete_couple.percentage_user2 = Decimal("30")
        db = AsyncMock()
        pct_u1, pct_u2 = await _resolve_split_percentages(db, complete_couple)
        assert pct_u1 == Decimal("70")
        assert pct_u2 == Decimal("30")

    async def test_custom_raises_422_if_percentages_not_set(self, complete_couple):
        complete_couple.split_mode = SplitMode.custom
        complete_couple.percentage_user1 = None
        complete_couple.percentage_user2 = None
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await _resolve_split_percentages(db, complete_couple)
        assert exc.value.status_code == 422

    async def test_auto_calculates_from_salaries(self, complete_couple, user1, user2):
        complete_couple.split_mode = SplitMode.auto
        user1.salary = 1000000
        user2.salary = 500000

        mock_scalars = AsyncMock()
        mock_scalars.all = lambda: [user1, user2]
        mock_result = AsyncMock()
        mock_result.scalars = lambda: mock_scalars
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        pct_u1, pct_u2 = await _resolve_split_percentages(db, complete_couple)
        assert pct_u1 == Decimal("66.67")
        assert pct_u2 == Decimal("33.33")

    async def test_auto_raises_422_if_salary_missing(self, complete_couple, user1, user2):
        complete_couple.split_mode = SplitMode.auto
        user1.salary = None
        user2.salary = 500000

        mock_scalars = AsyncMock()
        mock_scalars.all = lambda: [user1, user2]
        mock_result = AsyncMock()
        mock_result.scalars = lambda: mock_scalars
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await _resolve_split_percentages(db, complete_couple)
        assert exc.value.status_code == 422


class TestCalculateBalance:
    async def test_raises_400_if_no_couple(self, user1_no_couple):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await balance_service.calculate_balance(db, user1_no_couple)
        assert exc.value.status_code == 400

    def _setup_db(self, couple, expenses):
        mock_couple_result = AsyncMock()
        mock_couple_result.scalar_one_or_none = lambda: couple

        mock_scalars = AsyncMock()
        mock_scalars.all = lambda: expenses
        mock_expenses_result = AsyncMock()
        mock_expenses_result.scalars = lambda: mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[mock_couple_result, mock_expenses_result])
        return db

    async def test_zero_balance_when_no_expenses(self, user1, complete_couple):
        db = self._setup_db(complete_couple, [])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("0.00")
        assert result["debtor"] is None
        assert result["creditor"] is None
        assert "settled" in result["summary"]

    async def test_u2_owes_u1_when_u1_paid(self, user1, user1_id, user2_id, complete_couple, couple_id):
        # u1 paid 10000, split equal → u2 owes 5000
        expense = _make_expense(couple_id, user1_id, 10000, user1_id, user2_id)
        db = self._setup_db(complete_couple, [expense])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("5000.00")
        assert result["debtor"] == user2_id
        assert result["creditor"] == user1_id

    async def test_u1_owes_u2_when_u2_paid(self, user1, user1_id, user2_id, complete_couple, couple_id):
        # u2 paid 10000, split equal → u1 owes 5000
        expense = _make_expense(couple_id, user2_id, 10000, user1_id, user2_id)
        db = self._setup_db(complete_couple, [expense])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("5000.00")
        assert result["debtor"] == user1_id
        assert result["creditor"] == user2_id

    async def test_balance_with_split_override(self, user1, user1_id, user2_id, complete_couple, couple_id):
        # u2 paid 10000, override 70/30 → u1 owes 7000
        expense = _make_expense(
            couple_id, user2_id, 10000, user1_id, user2_id,
            split_override_user1=Decimal("70"),
            split_override_user2=Decimal("30"),
        )
        db = self._setup_db(complete_couple, [expense])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("7000.00")
        assert result["debtor"] == user1_id

    async def test_net_balance_multiple_expenses(self, user1, user1_id, user2_id, complete_couple, couple_id):
        # u1 paid 10000 (u2 owes 5000)
        # u2 paid 4000  (u1 owes 2000)
        # net: u2 still owes 3000
        e1 = _make_expense(couple_id, user1_id, 10000, user1_id, user2_id)
        e2 = _make_expense(couple_id, user2_id, 4000, user1_id, user2_id)
        db = self._setup_db(complete_couple, [e1, e2])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("3000.00")
        assert result["debtor"] == user2_id

    async def test_balanced_expenses_returns_settled(self, user1, user1_id, user2_id, complete_couple, couple_id):
        # Both paid 10000 equal → net 0
        e1 = _make_expense(couple_id, user1_id, 10000, user1_id, user2_id)
        e2 = _make_expense(couple_id, user2_id, 10000, user1_id, user2_id)
        db = self._setup_db(complete_couple, [e1, e2])
        result = await balance_service.calculate_balance(db, user1)
        assert result["balance"] == Decimal("0.00")
        assert result["debtor"] is None
        assert "settled" in result["summary"]
