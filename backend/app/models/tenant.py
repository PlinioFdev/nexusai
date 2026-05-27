from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        back_populates="tenant", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]
        back_populates="tenant", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(  # type: ignore[name-defined]
        back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant slug={self.slug}>"
