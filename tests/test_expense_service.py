import uuid
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.services import expense_service
from app.models.expense import ExpenseType
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


def _db_returning(value):
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = lambda: value
    mock_result.scalars = lambda: AsyncMock(all=lambda: [value] if value else [])
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


def _expense_data(**kwargs):
    defaults = dict(
        type=ExpenseType.shared,
        amount=Decimal("10000"),
        category="comida",
        expense_date=date(2026, 4, 18),
        paid_by=None,  # set per test
    )
    defaults.update(kwargs)
    return ExpenseCreate(**defaults)


class TestResolveVisibleTo:
    def test_shared_includes_both_users(self, complete_couple, user1_id, user2_id):
        result = expense_service._resolve_visible_to(
            ExpenseType.shared, complete_couple, user1_id
        )
        assert str(user1_id) in result
        assert str(user2_id) in result
        assert len(result) == 2

    def test_personal_includes_only_creator(self, complete_couple, user1_id, user2_id):
        result = expense_service._resolve_visible_to(
            ExpenseType.personal, complete_couple, user1_id
        )
        assert str(user1_id) in result
        assert str(user2_id) not in result
        assert len(result) == 1


class TestCreateExpense:
    async def test_raises_400_if_user_not_in_couple(self, user1_no_couple):
        db = AsyncMock()
        data = _expense_data(paid_by=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            await expense_service.create_expense(db, user1_no_couple, data)
        assert exc.value.status_code == 400

    async def test_raises_400_if_couple_incomplete(self, user1, incomplete_couple):
        db = _db_returning(incomplete_couple)
        data = _expense_data(paid_by=user1.id)
        with pytest.raises(HTTPException) as exc:
            await expense_service.create_expense(db, user1, data)
        assert exc.value.status_code == 400
        assert "not complete" in exc.value.detail

    async def test_raises_400_if_paid_by_not_in_couple(self, user1, complete_couple):
        db = _db_returning(complete_couple)
        outsider_id = uuid.uuid4()
        data = _expense_data(paid_by=outsider_id)
        with pytest.raises(HTTPException) as exc:
            await expense_service.create_expense(db, user1, data)
        assert exc.value.status_code == 400
        assert "paid_by" in exc.value.detail

    async def test_creates_shared_expense_visible_to_both(self, user1, user2_id, complete_couple):
        db = _db_returning(complete_couple)
        data = _expense_data(paid_by=user1.id, type=ExpenseType.shared)
        await expense_service.create_expense(db, user1, data)
        added_expense = db.add.call_args[0][0]
        assert str(user1.id) in added_expense.visible_to
        assert str(user2_id) in added_expense.visible_to

    async def test_creates_personal_expense_visible_to_creator_only(self, user1, user2_id, complete_couple):
        db = _db_returning(complete_couple)
        data = _expense_data(paid_by=user1.id, type=ExpenseType.personal)
        await expense_service.create_expense(db, user1, data)
        added_expense = db.add.call_args[0][0]
        assert str(user1.id) in added_expense.visible_to
        assert str(user2_id) not in added_expense.visible_to


class TestListExpenses:
    async def test_returns_empty_if_no_couple(self, user1_no_couple):
        db = AsyncMock()
        result = await expense_service.list_expenses(db, user1_no_couple)
        assert result == []

    async def test_filters_by_visibility(self, user1, user2_id, shared_expense, personal_expense):
        # user1 should see shared but user2 should NOT see personal_expense
        user2_mock = AsyncMock()
        user2_mock.id = user2_id
        user2_mock.couple_id = user1.couple_id

        mock_result = AsyncMock()
        mock_result.scalars = lambda: AsyncMock(
            all=lambda: [shared_expense, personal_expense]
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await expense_service.list_expenses(db, user2_mock)
        assert shared_expense in result
        assert personal_expense not in result

    async def test_invalid_month_format_raises_400(self, user1):
        db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars = lambda: AsyncMock(all=lambda: [])
        db.execute = AsyncMock(return_value=mock_result)
        with pytest.raises(HTTPException) as exc:
            await expense_service.list_expenses(db, user1, month="abril-2026")
        assert exc.value.status_code == 400


class TestUpdateExpense:
    async def test_raises_403_if_not_creator(self, user2, shared_expense):
        # shared_expense.created_by == user1_id, user2 tries to edit
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = lambda: shared_expense
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await expense_service.update_expense(
                db, shared_expense.id, user2, ExpenseUpdate(amount=Decimal("999"))
            )
        assert exc.value.status_code == 403

    async def test_raises_404_if_not_visible(self, user2, personal_expense):
        # personal_expense only visible to user1, user2 tries to edit
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = lambda: personal_expense
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await expense_service.update_expense(
                db, personal_expense.id, user2, ExpenseUpdate(amount=Decimal("999"))
            )
        assert exc.value.status_code == 404


class TestDeleteExpense:
    async def test_raises_403_if_not_creator(self, user2, shared_expense):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = lambda: shared_expense
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await expense_service.delete_expense(db, shared_expense.id, user2)
        assert exc.value.status_code == 403

    async def test_deletes_if_creator(self, user1, shared_expense, complete_couple):
        # shared_expense.created_by == user1_id
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = lambda: shared_expense
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.delete = AsyncMock()
        db.flush = AsyncMock()

        await expense_service.delete_expense(db, shared_expense.id, user1)
        db.delete.assert_called_once_with(shared_expense)
