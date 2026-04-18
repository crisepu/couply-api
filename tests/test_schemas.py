import pytest
from decimal import Decimal
from datetime import date
import uuid
from pydantic import ValidationError

from app.schemas.couple import UpdateSplitRequest
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.models.couple import SplitMode
from app.models.expense import ExpenseType


# ── UpdateSplitRequest ────────────────────────────────────────────────────────

class TestUpdateSplitRequest:
    def test_equal_mode_no_percentages_required(self):
        req = UpdateSplitRequest(split_mode=SplitMode.equal)
        assert req.split_mode == SplitMode.equal

    def test_auto_mode_no_percentages_required(self):
        req = UpdateSplitRequest(split_mode=SplitMode.auto)
        assert req.split_mode == SplitMode.auto

    def test_custom_mode_requires_both_percentages(self):
        with pytest.raises(ValidationError, match="Both percentages are required"):
            UpdateSplitRequest(split_mode=SplitMode.custom)

    def test_custom_mode_requires_both_not_just_one(self):
        with pytest.raises(ValidationError):
            UpdateSplitRequest(split_mode=SplitMode.custom, percentage_user1=Decimal("60"))

    def test_custom_mode_percentages_must_sum_100(self):
        with pytest.raises(ValidationError, match="sum to 100"):
            UpdateSplitRequest(
                split_mode=SplitMode.custom,
                percentage_user1=Decimal("60"),
                percentage_user2=Decimal("60"),
            )

    def test_custom_mode_valid(self):
        req = UpdateSplitRequest(
            split_mode=SplitMode.custom,
            percentage_user1=Decimal("70"),
            percentage_user2=Decimal("30"),
        )
        assert req.percentage_user1 == Decimal("70")
        assert req.percentage_user2 == Decimal("30")

    def test_custom_mode_allows_tolerance(self):
        # 100.005 rounds within tolerance
        req = UpdateSplitRequest(
            split_mode=SplitMode.custom,
            percentage_user1=Decimal("50.005"),
            percentage_user2=Decimal("50"),
        )
        assert req.percentage_user1 is not None


# ── ExpenseCreate ─────────────────────────────────────────────────────────────

class TestExpenseCreate:
    def _base(self, **kwargs):
        defaults = dict(
            type=ExpenseType.shared,
            amount=Decimal("10000"),
            category="comida",
            expense_date=date(2026, 4, 18),
            paid_by=uuid.uuid4(),
        )
        defaults.update(kwargs)
        return defaults

    def test_valid_no_override(self):
        e = ExpenseCreate(**self._base())
        assert e.split_override_user1 is None
        assert e.split_override_user2 is None

    def test_valid_with_override(self):
        e = ExpenseCreate(**self._base(
            split_override_user1=Decimal("70"),
            split_override_user2=Decimal("30"),
        ))
        assert e.split_override_user1 == Decimal("70")

    def test_override_only_one_fails(self):
        with pytest.raises(ValidationError, match="presentes o ninguno"):
            ExpenseCreate(**self._base(split_override_user1=Decimal("70")))

    def test_override_not_summing_100_fails(self):
        with pytest.raises(ValidationError, match="sumar 100"):
            ExpenseCreate(**self._base(
                split_override_user1=Decimal("60"),
                split_override_user2=Decimal("60"),
            ))

    def test_personal_type_valid(self):
        paid_by = uuid.uuid4()
        e = ExpenseCreate(**self._base(type=ExpenseType.personal, paid_by=paid_by))
        assert e.type == ExpenseType.personal


# ── ExpenseUpdate ─────────────────────────────────────────────────────────────

class TestExpenseUpdate:
    def test_empty_update_valid(self):
        u = ExpenseUpdate()
        assert u.amount is None
        assert u.category is None

    def test_partial_update_valid(self):
        u = ExpenseUpdate(amount=Decimal("5000"), category="transporte")
        assert u.amount == Decimal("5000")

    def test_override_only_one_fails(self):
        with pytest.raises(ValidationError, match="presentes o ninguno"):
            ExpenseUpdate(split_override_user1=Decimal("80"))

    def test_override_not_summing_100_fails(self):
        with pytest.raises(ValidationError, match="sumar 100"):
            ExpenseUpdate(
                split_override_user1=Decimal("80"),
                split_override_user2=Decimal("80"),
            )

    def test_valid_override_update(self):
        u = ExpenseUpdate(
            split_override_user1=Decimal("40"),
            split_override_user2=Decimal("60"),
        )
        assert u.split_override_user1 == Decimal("40")
