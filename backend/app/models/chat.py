from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, Index

from app.db.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="Nova conversa",
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="chat_sessions")  # type: ignore[name-defined]
    user: Mapped["User"] = relationship(back_populates="chat_sessions")  # type: ignore[name-defined]
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_tenant_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user={self.user_id}>"


class Message(Base):
    __tablename__ = "messages"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_chunks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array de chunk IDs usados no contexto RAG",
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message role={self.role} session={self.session_id}>"
