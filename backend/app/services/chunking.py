"""
Chunking service — fixed-size com overlap.

Divide o texto em janelas de CHUNK_SIZE_TOKENS tokens com sobreposição
de CHUNK_OVERLAP_TOKENS entre chunks adjacentes para preservar contexto
nas bordas.

Usa tiktoken (cl100k_base) — encoding compatível com Claude e Voyage AI.
"""

from dataclasses import dataclass

import tiktoken

from app.core.config import settings

_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    token_count: int


def split_text(text: str) -> list[TextChunk]:
    """
    Divide `text` em chunks de até CHUNK_SIZE_TOKENS tokens com overlap.

    Retorna lista vazia para texto vazio ou só whitespace.
    """
    text = text.strip()
    if not text:
        return []

    chunk_size = settings.CHUNK_SIZE_TOKENS
    overlap = settings.CHUNK_OVERLAP_TOKENS
    step = chunk_size - overlap

    tokens = _ENCODING.encode(text)
    if not tokens:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        window = tokens[start:end]

        chunks.append(TextChunk(
            content=_ENCODING.decode(window),
            chunk_index=index,
            token_count=len(window),
        ))

        if end == len(tokens):
            break

        start += step
        index += 1

    return chunks
