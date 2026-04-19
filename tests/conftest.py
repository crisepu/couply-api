import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import date

from app.models.user import User
from app.models.couple import Couple, SplitMode
from app.models.expense import Expense, ExpenseType


# ── DB session mock ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


# ── Reusable IDs ─────────────────────────────────────────────────────────────

@pytest.fixture
def user1_id():
    return uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")

@pytest.fixture
def user2_id():
    return uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")

@pytest.fixture
def couple_id():
    return uuid.UUID("cccccccc-0000-0000-0000-000000000003")


# ── Model factories ───────────────────────────────────────────────────────────

@pytest.fixture
def user1(user1_id, couple_id):
    u = User()
    u.id = user1_id
    u.firebase_uid = "firebase-uid-1"
    u.email = "user1@couply.dev"
    u.name = "User One"
    u.couple_id = couple_id
    u.salary = None
    return u

@pytest.fixture
def user2(user2_id, couple_id):
    u = User()
    u.id = user2_id
    u.firebase_uid = "firebase-uid-2"
    u.email = "user2@couply.dev"
    u.name = "User Two"
    u.couple_id = couple_id
    u.salary = None
    return u

@pytest.fixture
def user1_no_couple(user1_id):
    u = User()
    u.id = user1_id
    u.firebase_uid = "firebase-uid-1"
    u.email = "user1@couply.dev"
    u.couple_id = None
    u.salary = None
    return u

@pytest.fixture
def complete_couple(couple_id, user1_id, user2_id):
    c = Couple()
    c.id = couple_id
    c.user1_id = user1_id
    c.user2_id = user2_id
    c.split_mode = SplitMode.equal
    c.percentage_user1 = Decimal("50.00")
    c.percentage_user2 = Decimal("50.00")
    c.invite_code = "abc12345"
    return c

@pytest.fixture
def incomplete_couple(couple_id, user1_id):
    c = Couple()
    c.id = couple_id
    c.user1_id = user1_id
    c.user2_id = None
    c.split_mode = SplitMode.equal
    c.percentage_user1 = None
    c.percentage_user2 = None
    c.invite_code = "xyz99999"
    return c

@pytest.fixture
def shared_expense(couple_id, user1_id, user2_id):
    e = Expense()
    e.id = uuid.uuid4()
    e.couple_id = couple_id
    e.created_by = user1_id
    e.type = ExpenseType.shared
    e.amount = Decimal("10000")
    e.category = "food"
    e.description = None
    e.expense_date = date(2026, 4, 18)
    e.paid_by = user2_id
    e.split_override_user1 = None
    e.split_override_user2 = None
    e.visible_to = [str(user1_id), str(user2_id)]
    return e

@pytest.fixture
def personal_expense(couple_id, user1_id):
    e = Expense()
    e.id = uuid.uuid4()
    e.couple_id = couple_id
    e.created_by = user1_id
    e.type = ExpenseType.personal
    e.amount = Decimal("3000")
    e.category = "gym"
    e.description = None
    e.expense_date = date(2026, 4, 18)
    e.paid_by = user1_id
    e.split_override_user1 = None
    e.split_override_user2 = None
    e.visible_to = [str(user1_id)]
    return e
