from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, ForeignKey, Index

from app.db.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    # tenant_id direto — filtro sem JOIN (regra multi-tenancy)
    tenant_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pinecone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_chunks_tenant_document", "tenant_id", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<Chunk document_id={self.document_id} index={self.chunk_index}>"
