import uuid
import enum
from sqlalchemy import String, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class SplitMode(str, enum.Enum):
    auto = "auto"
    equal = "equal"
    custom = "custom"


class Couple(Base):
    __tablename__ = "couples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user1_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user2_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    split_mode: Mapped[SplitMode] = mapped_column(SAEnum(SplitMode, native_enum=False), nullable=False, default=SplitMode.equal)
    percentage_user1: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    percentage_user2: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    invite_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id])
    user2: Mapped["User | None"] = relationship("User", foreign_keys=[user2_id])
    members: Mapped[list["User"]] = relationship("User", foreign_keys="User.couple_id", back_populates="couple")
