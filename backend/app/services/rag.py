"""
RAG service — monta prompt com contexto e chama Claude API.

Responsabilidade: dado uma pergunta, histórico e chunks recuperados,
retorna a resposta do assistant e os IDs dos chunks usados.
"""

import logging
from dataclasses import dataclass

import anthropic

from app.core.config import settings
from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

# Lazy init — mesmo padrão dos outros clients externos
_anthropic_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


@dataclass
class RAGResult:
    answer: str
    source_chunk_ids: list[str]  # pinecone_ids dos chunks usados


_SYSTEM_PROMPT = """\
Você é um assistente especializado que responde perguntas com base \
nos documentos fornecidos pelo usuário.

Regras:
- Responda apenas com base no CONTEXTO fornecido.
- Se o contexto não contiver informação suficiente, diga claramente \
que não encontrou a resposta nos documentos.
- Seja conciso e preciso.
- Não invente informações.
- Responda no mesmo idioma da pergunta do usuário.\
"""


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    """Formata chunks recuperados como bloco de contexto para o prompt."""
    if not chunks:
        return "Nenhum documento relevante encontrado."

    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Trecho {i} — {chunk.filename} | score={chunk.score:.2f}]\n"
            f"{chunk.content_preview}"
        )
    return "\n\n---\n\n".join(parts)


def _build_messages(
    question: str,
    history: list[dict[str, str]],
    context_block: str,
) -> list[dict[str, str]]:
    """
    Monta o array de messages para a Claude API.

    Formato:
      [histórico recente] + [user: contexto + pergunta]

    O contexto é injetado na última mensagem do usuário para não
    vazar entre turns do histórico.
    """
    messages: list[dict[str, str]] = list(history)  # cópia — não mutar o original
    user_content = (
        f"CONTEXTO DOS DOCUMENTOS:\n{context_block}\n\n"
        f"PERGUNTA:\n{question}"
    )
    messages.append({"role": "user", "content": user_content})
    return messages


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
) -> RAGResult:
    """
    Gera resposta via Claude usando os chunks como contexto.

    Args:
        question: pergunta do usuário (já validada)
        chunks: chunks recuperados do Pinecone
        history: últimas N mensagens da sessão como [{role, content}]

    Returns:
        RAGResult com answer e lista de pinecone_ids usados.

    Raises:
        ValueError: se a API retornar resposta sem conteúdo de texto.
    """
    context_block = _build_context_block(chunks)
    messages = _build_messages(question, history, context_block)

    response = _get_client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=settings.RAG_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=messages,  # type: ignore[arg-type]
    )

    # Extrai texto da resposta — guard contra content filtering ou resposta vazia
    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        raise ValueError("Claude API retornou resposta sem bloco de texto.")
    answer = text_blocks[0].text

    source_ids = [c.pinecone_id for c in chunks]

    logger.debug(
        "RAG: chunks_used=%d tokens_in=%d tokens_out=%d",
        len(chunks),
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    return RAGResult(answer=answer, source_chunk_ids=source_ids)
