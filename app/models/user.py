import uuid
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    couple_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("couples.id"), nullable=True)
    salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    couple: Mapped["Couple | None"] = relationship("Couple", foreign_keys=[couple_id], back_populates="members")
