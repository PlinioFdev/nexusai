"""
Endpoints de documentos.

POST   /documents/upload     — upload + ingestão assíncrona (202)
GET    /documents/           — lista com paginação
GET    /documents/{id}       — status e detalhes
DELETE /documents/{id}       — remove documento, chunks e vetores
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services import storage
from app.services.storage import StorageError
from app.tasks.ingest import ingest_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_pinecone_index():
    """Lazy: instancia Pinecone só quando necessário (não na importação)."""
    from pinecone import Pinecone
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc.Index(settings.PINECONE_INDEX_NAME)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Faz upload de PDF ou TXT e inicia ingestão assíncrona",
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    try:
        storage_path, file_type, file_size_bytes = await storage.save(
            file, tenant_id=current_user.tenant_id
        )
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    doc = Document(
        tenant_id=current_user.tenant_id,
        name=file.filename or "unknown",
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ingest_document.delay(doc.id)

    logger.info("Documento enfileirado: id=%s name=%s tenant=%s", doc.id, doc.name, current_user.tenant_id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="Lista documentos do tenant",
)
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    base = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
    total = base.count()
    items = (
        base.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Retorna status e detalhes de um documento",
)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = _get_or_404(db, document_id, current_user.tenant_id)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove documento, chunks e vetores do Pinecone",
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    doc = _get_or_404(db, document_id, current_user.tenant_id)

    pinecone_ids = [
        row.pinecone_id
        for row in db.query(Chunk.pinecone_id)
            .filter(Chunk.document_id == document_id)
            .all()
        if row.pinecone_id
    ]

    if pinecone_ids:
        _get_pinecone_index().delete(ids=pinecone_ids, namespace=current_user.tenant_id)

    storage.delete(doc.storage_path)
    db.delete(doc)
    db.commit()

    logger.info(
        "Documento removido: id=%s tenant=%s vetores=%d",
        document_id, current_user.tenant_id, len(pinecone_ids),
    )


def _get_or_404(db: Session, document_id: str, tenant_id: str) -> Document:
    """404 em vez de 403 para não vazar IDs de outros tenants."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.tenant_id == tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return doc
