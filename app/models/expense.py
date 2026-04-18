import uuid
import enum
from datetime import date
from sqlalchemy import String, Numeric, ForeignKey, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class ExpenseType(str, enum.Enum):
    shared = "shared"
    personal = "personal"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    couple_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("couples.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[ExpenseType] = mapped_column(SAEnum(ExpenseType, native_enum=False), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    split_override_user1: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    split_override_user2: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    couple: Mapped["Couple"] = relationship("Couple", foreign_keys=[couple_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    payer: Mapped["User"] = relationship("User", foreign_keys=[paid_by])
