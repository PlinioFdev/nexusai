"""
Embedding service — Voyage AI voyage-3 (1024 dimensões).

Documentação: https://docs.voyageai.com/docs/embeddings
Batching: lotes de 96 (margem abaixo do limite de 128 da API).
"""

import voyageai

from app.core.config import settings

_MODEL = "voyage-3"
_BATCH_SIZE = 96

# Lazy: instanciado na primeira chamada, não na importação
# Evita AuthenticationError em testes sem VOYAGE_API_KEY no .env
_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings para uma lista de textos (input_type="document").
    Retorna vetores na mesma ordem de entrada.
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        result = _get_client().embed(batch, model=_MODEL, input_type="document")
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """
    Gera embedding para query de busca (input_type="query").
    Voyage aplica prompt interno otimizado para retrieval.
    """
    result = _get_client().embed([text], model=_MODEL, input_type="query")
    return result.embeddings[0]
