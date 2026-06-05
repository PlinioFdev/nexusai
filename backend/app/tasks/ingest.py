"""
Task Celery: pipeline de ingestão de documentos.

Fluxo:
  1. Extrai texto (PDF ou TXT)
  2. Divide em chunks (512 tokens / overlap 50)
  3. Gera embeddings via Voyage AI
  4. Persiste Chunks no PostgreSQL
  5. Indexa vetores no Pinecone (namespace=tenant_id)
  6. Atualiza Document.status → READY ou FAILED
"""

import logging
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.services.chunking import split_text
from app.services.embedding import embed_texts
from app.services.storage import download_to_tmp
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_PINECONE_UPSERT_BATCH = 100


def _get_pinecone_index():
    """Lazy: instancia Pinecone só quando a task executa, não na importação."""
    from pinecone import Pinecone
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc.Index(settings.PINECONE_INDEX_NAME)


def _read_local(path: Path, file_type: str) -> str:
    """Lê arquivo local por tipo. Usado tanto em dev (caminho direto) quanto em prod (após download)."""
    if file_type == "txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if file_type == "pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"file_type não suportado: {file_type}")


def _extract_text(storage_path: str, file_type: str) -> str:
    """
    Extrai texto do arquivo.
    Dev:  lê direto do caminho local.
    Prod: baixa do R2 para /tmp, processa e remove ao final.
    """
    if settings.is_development:
        return _read_local(Path(storage_path), file_type)

    tmp_path = download_to_tmp(storage_path, file_type)
    try:
        return _read_local(tmp_path, file_type)
    finally:
        tmp_path.unlink(missing_ok=True)


def _set_status(
    db: Session,
    document_id: str,
    status: DocumentStatus,
    error: str | None = None,
    chunk_count: int | None = None,
) -> None:
    """Atualiza status do Document e commita atomicamente."""
    update: dict = {"status": status, "error_message": error}
    if chunk_count is not None:
        update["chunk_count"] = chunk_count
    db.query(Document).filter(Document.id == document_id).update(
        update, synchronize_session=False
    )
    db.commit()


@celery_app.task(
    bind=True,
    name="tasks.ingest_document",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def ingest_document(self, document_id: str) -> dict:
    db = SessionLocal()
    try:
        # 1. Carrega documento
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error("ingest_document: document %s não encontrado", document_id)
            return {"document_id": document_id, "status": "not_found"}

        _set_status(db, document_id, DocumentStatus.PROCESSING)
        logger.info("Ingestão iniciada: doc=%s tenant=%s", document_id, doc.tenant_id)

        # 2. Extração de texto
        raw_text = _extract_text(doc.storage_path, doc.file_type)
        if not raw_text.strip():
            raise ValueError("Arquivo não contém texto extraível.")

        # 3. Chunking
        text_chunks = split_text(raw_text)
        if not text_chunks:
            raise ValueError("Chunking não gerou nenhum chunk.")

        # 4. Embeddings
        embeddings = embed_texts([c.content for c in text_chunks])

        # 5. Persiste no PostgreSQL (remove chunks anteriores em caso de reprocessamento)
        db.query(Chunk).filter(Chunk.document_id == document_id).delete(
            synchronize_session=False
        )

        db_chunks: list[Chunk] = []
        for tc in text_chunks:
            pinecone_id = f"{document_id}#{tc.chunk_index}"
            db_chunks.append(Chunk(
                tenant_id=doc.tenant_id,
                document_id=document_id,
                chunk_index=tc.chunk_index,
                content=tc.content,
                token_count=tc.token_count,
                pinecone_id=pinecone_id,
            ))

        db.add_all(db_chunks)
        db.flush()  # flush antes do Pinecone — se Pinecone falhar, rollback total

        # 6. Indexa no Pinecone (namespace=tenant_id)
        index = _get_pinecone_index()
        vectors = [
            {
                "id": f"{document_id}#{tc.chunk_index}",
                "values": embeddings[i],
                "metadata": {
                    "document_id": document_id,
                    "tenant_id": doc.tenant_id,
                    "chunk_index": tc.chunk_index,
                    "filename": doc.name,
                    "content_preview": tc.content[:500],
                },
            }
            for i, tc in enumerate(text_chunks)
        ]

        for i in range(0, len(vectors), _PINECONE_UPSERT_BATCH):
            index.upsert(vectors=vectors[i : i + _PINECONE_UPSERT_BATCH], namespace=doc.tenant_id)

        # 7. Finaliza — _set_status já commita, não precisa de commit adicional
        _set_status(db, document_id, DocumentStatus.READY, chunk_count=len(db_chunks))

        logger.info(
            "Ingestão concluída: doc=%s chunks=%d tenant=%s",
            document_id, len(db_chunks), doc.tenant_id,
        )
        return {"document_id": document_id, "chunks_created": len(db_chunks), "status": "ready"}

    except Exception as exc:
        db.rollback()
        logger.exception("Erro na ingestão %s: %s", document_id, exc)
        try:
            _set_status(db, document_id, DocumentStatus.FAILED, error=str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        db.close()
