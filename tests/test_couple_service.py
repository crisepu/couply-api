import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services import couple_service
from app.models.couple import SplitMode
from app.schemas.couple import UpdateSplitRequest


def _make_execute(return_value):
    """Helper: mock db.execute to return scalar_one_or_none."""
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = lambda: return_value
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


class TestCreateCouple:
    async def test_creates_couple_for_user_without_couple(self, user1_no_couple):
        db = _make_execute(None)
        await couple_service.create_couple(db, user1_no_couple)
        db.add.assert_called_once()
        db.flush.assert_called()

    async def test_raises_400_if_user_already_in_couple(self, user1):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await couple_service.create_couple(db, user1)
        assert exc.value.status_code == 400
        assert "already in a couple" in exc.value.detail


class TestJoinCouple:
    async def test_raises_400_if_user_already_in_couple(self, user1):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await couple_service.join_couple(db, user1, "somecode")
        assert exc.value.status_code == 400

    async def test_raises_404_if_invalid_invite_code(self, user1_no_couple):
        db = _make_execute(None)
        with pytest.raises(HTTPException) as exc:
            await couple_service.join_couple(db, user1_no_couple, "badcode")
        assert exc.value.status_code == 404
        assert "Invalid invite code" in exc.value.detail

    async def test_raises_400_if_couple_already_complete(self, user1_no_couple, complete_couple):
        db = _make_execute(complete_couple)
        with pytest.raises(HTTPException) as exc:
            await couple_service.join_couple(db, user1_no_couple, complete_couple.invite_code)
        assert exc.value.status_code == 400
        assert "already complete" in exc.value.detail

    async def test_raises_400_if_joining_own_couple(self, user1_no_couple, incomplete_couple):
        # user1 tries to join their own couple
        incomplete_couple.user1_id = user1_no_couple.id
        db = _make_execute(incomplete_couple)
        with pytest.raises(HTTPException) as exc:
            await couple_service.join_couple(db, user1_no_couple, incomplete_couple.invite_code)
        assert exc.value.status_code == 400
        assert "own couple" in exc.value.detail

    async def test_joins_couple_successfully(self, user2, incomplete_couple):
        user2.couple_id = None
        db = _make_execute(incomplete_couple)
        await couple_service.join_couple(db, user2, incomplete_couple.invite_code)
        assert incomplete_couple.user2_id == user2.id
        assert user2.couple_id == incomplete_couple.id


class TestGetCoupleForUser:
    async def test_raises_404_if_no_couple(self, user1_no_couple):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await couple_service.get_couple_for_user(db, user1_no_couple)
        assert exc.value.status_code == 404

    async def test_returns_couple(self, user1, complete_couple):
        db = _make_execute(complete_couple)
        result = await couple_service.get_couple_for_user(db, user1)
        assert result.id == complete_couple.id


class TestUpdateSplit:
    async def test_equal_mode_sets_50_50(self, user1, complete_couple):
        db = _make_execute(complete_couple)
        data = UpdateSplitRequest(split_mode=SplitMode.equal)
        await couple_service.update_split(db, user1, data)
        assert complete_couple.percentage_user1 == Decimal("50.00")
        assert complete_couple.percentage_user2 == Decimal("50.00")

    async def test_custom_mode_sets_percentages(self, user1, complete_couple):
        db = _make_execute(complete_couple)
        data = UpdateSplitRequest(
            split_mode=SplitMode.custom,
            percentage_user1=Decimal("70"),
            percentage_user2=Decimal("30"),
        )
        await couple_service.update_split(db, user1, data)
        assert complete_couple.percentage_user1 == Decimal("70")
        assert complete_couple.percentage_user2 == Decimal("30")
        assert complete_couple.split_mode == SplitMode.custom

    async def test_auto_mode_raises_422_if_salary_missing(self, user1, complete_couple, user2):
        # Both users have no sueldo
        mock_result_couple = AsyncMock()
        mock_result_couple.scalar_one_or_none = lambda: complete_couple

        mock_result_users = AsyncMock()
        mock_result_users.scalars = lambda: AsyncMock(all=lambda: [user1, user2])

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[mock_result_couple, mock_result_users])
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        data = UpdateSplitRequest(split_mode=SplitMode.auto)
        with pytest.raises(HTTPException) as exc:
            await couple_service.update_split(db, user1, data)
        assert exc.value.status_code == 422

    async def test_auto_mode_calculates_from_salary(self, user1, user2, complete_couple):
        user1.salary = 1000000
        user2.salary = 500000

        mock_result_couple = AsyncMock()
        mock_result_couple.scalar_one_or_none = lambda: complete_couple

        mock_scalars = AsyncMock()
        mock_scalars.all = lambda: [user1, user2]
        mock_result_users = AsyncMock()
        mock_result_users.scalars = lambda: mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[mock_result_couple, mock_result_users])
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        data = UpdateSplitRequest(split_mode=SplitMode.auto)
        await couple_service.update_split(db, user1, data)

        # 1000000 / 1500000 * 100 = 66.67
        assert complete_couple.percentage_user1 == Decimal("66.67")
        assert complete_couple.percentage_user2 == Decimal("33.33")
