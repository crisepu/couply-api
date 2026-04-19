import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services import auth_service
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User


class TestCreateUser:
    async def test_creates_user_successfully(self, mock_db):
        mock_db.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: None))

        data = UserCreate(firebase_uid="uid-123", email="test@example.com", name="Test")
        created = User()
        created.firebase_uid = "uid-123"
        created.email = "test@example.com"

        mock_db.refresh = AsyncMock(side_effect=lambda u: None)

        with patch.object(auth_service, "get_user_by_firebase_uid", return_value=None):
            result = await auth_service.create_user(mock_db, data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called()

    async def test_raises_409_if_user_exists(self, mock_db, user1):
        with patch.object(auth_service, "get_user_by_firebase_uid", return_value=user1):
            with pytest.raises(HTTPException) as exc:
                await auth_service.create_user(
                    mock_db,
                    UserCreate(firebase_uid="firebase-uid-1", email="x@x.com"),
                )
        assert exc.value.status_code == 409
        assert "already registered" in exc.value.detail

    async def test_get_user_by_firebase_uid_returns_none_when_not_found(self, mock_db):
        mock_db.execute = AsyncMock(
            return_value=AsyncMock(scalar_one_or_none=lambda: None)
        )
        result = await auth_service.get_user_by_firebase_uid(mock_db, "nonexistent")
        assert result is None


class TestUpdateUser:
    async def test_updates_name(self, mock_db, user1):
        data = UserUpdate(name="New Name")
        await auth_service.update_user(mock_db, user1, data)
        assert user1.name == "New Name"
        mock_db.flush.assert_called()

    async def test_updates_salary(self, mock_db, user1):
        data = UserUpdate(salary=Decimal("2500000"))
        await auth_service.update_user(mock_db, user1, data)
        assert user1.salary == Decimal("2500000")

    async def test_updates_name_and_salary_together(self, mock_db, user1):
        data = UserUpdate(name="Jane", salary=Decimal("1800000"))
        await auth_service.update_user(mock_db, user1, data)
        assert user1.name == "Jane"
        assert user1.salary == Decimal("1800000")

    async def test_empty_payload_changes_nothing(self, mock_db, user1):
        original_name = user1.name
        original_salary = user1.salary
        data = UserUpdate()
        await auth_service.update_user(mock_db, user1, data)
        assert user1.name == original_name
        assert user1.salary == original_salary

    async def test_salary_not_exposed_in_response_schema(self, mock_db, user1):
        data = UserUpdate(salary=Decimal("9999999"))
        result = await auth_service.update_user(mock_db, user1, data)
        from app.schemas.user import UserResponse
        response = UserResponse.model_validate(result)
        assert not hasattr(response, "salary")
