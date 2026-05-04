import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.services import auth_service
from app.schemas.user import PublicUserResponse
from app.models.user import User


class TestGetUserById:
    async def test_returns_user_when_found(self, mock_db, user1, user1_id):
        mock_db.execute = AsyncMock(
            return_value=AsyncMock(scalar_one_or_none=lambda: user1)
        )
        result = await auth_service.get_user_by_id(mock_db, user1_id)
        assert result is user1

    async def test_returns_none_when_not_found(self, mock_db):
        mock_db.execute = AsyncMock(
            return_value=AsyncMock(scalar_one_or_none=lambda: None)
        )
        result = await auth_service.get_user_by_id(mock_db, uuid.uuid4())
        assert result is None

    async def test_public_response_exposes_id_name_email(self, user1):
        response = PublicUserResponse.model_validate(user1)
        assert response.id == user1.id
        assert response.name == user1.name
        assert response.email == user1.email

    async def test_public_response_does_not_expose_salary(self, user1):
        user1.salary = 9_999_999
        response = PublicUserResponse.model_validate(user1)
        assert not hasattr(response, "salary")

    async def test_public_response_does_not_expose_couple_id(self, user1):
        response = PublicUserResponse.model_validate(user1)
        assert not hasattr(response, "couple_id")

    async def test_name_can_be_null(self, user1):
        user1.name = None
        response = PublicUserResponse.model_validate(user1)
        assert response.name is None
