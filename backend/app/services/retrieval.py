"""
Retrieval service — busca semântica no Pinecone.

Responsabilidade única: dado um embedding de query e um tenant_id,
retorna os chunks mais relevantes com score >= threshold.
"""

import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy init — mesmo padrão de embedding.py e ingest.py
_pinecone_index = None


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


@dataclass
class RetrievedChunk:
    pinecone_id: str
    score: float
    document_id: str
    filename: str
    content_preview: str  # 500 chars — suficiente para o prompt


def retrieve_chunks(
    query_embedding: list[float],
    tenant_id: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> list[RetrievedChunk]:
    """
    Consulta Pinecone e retorna chunks relevantes para o tenant.

    Args:
        query_embedding: vetor da pergunta (1024 dims, Voyage AI)
        tenant_id: namespace isolado por tenant
        top_k: número máximo de resultados (padrão: settings.RAG_TOP_K)
        score_threshold: score mínimo de relevância (padrão: settings.RAG_SCORE_THRESHOLD)

    Returns:
        Lista de RetrievedChunk ordenada por score descendente.
    """
    k = top_k if top_k is not None else settings.RAG_TOP_K
    threshold = score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD

    result = _get_index().query(
        vector=query_embedding,
        top_k=k,
        namespace=tenant_id,
        include_metadata=True,
    )

    chunks: list[RetrievedChunk] = []
    for match in result.matches:
        if match.score < threshold:
            continue
        meta = match.metadata or {}
        chunks.append(RetrievedChunk(
            pinecone_id=match.id,
            score=match.score,
            document_id=meta.get("document_id", ""),
            filename=meta.get("filename", ""),
            content_preview=meta.get("content_preview", ""),
        ))

    logger.debug(
        "Retrieval: tenant=%s top_k=%d threshold=%.2f returned=%d",
        tenant_id, k, threshold, len(chunks),
    )
    return chunks
