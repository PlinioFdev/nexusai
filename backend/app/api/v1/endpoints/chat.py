"""
Endpoints de chat RAG.

Rotas:
  POST   /chat/sessions                              → cria sessão
  GET    /chat/sessions                              → lista sessões do usuário
  GET    /chat/sessions/{session_id}                 → detalhe da sessão
  DELETE /chat/sessions/{session_id}                 → deleta sessão
  GET    /chat/sessions/{session_id}/messages        → lista mensagens da sessão
  POST   /chat/sessions/{session_id}/messages        → envia mensagem, recebe resposta RAG
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.chat import ChatSession, Message
from app.models.user import User
from app.schemas.chat import (
    ChatResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)
from app.services.embedding import embed_query
from app.services.retrieval import retrieve_chunks
from app.services.rag import generate_answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_or_404(
    session_id: str,
    tenant_id: str,
    user_id: str,
    db: Session,
) -> ChatSession:
    """Busca sessão filtrando por tenant + user — 404 em vez de 403 para não vazar IDs."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.tenant_id == tenant_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada")
    return session


def _get_recent_history(session: ChatSession, limit: int) -> list[dict[str, str]]:
    """Retorna as últimas `limit` mensagens como lista de dicts para a Claude API."""
    messages = (
        sorted(session.messages, key=lambda m: m.created_at)[-limit:]
        if session.messages
        else []
    )
    return [{"role": m.role, "content": m.content} for m in messages]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    session = ChatSession(
        tenant_id=current_user.tenant_id,
        user_id=str(current_user.id),
        title=payload.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionListResponse:
    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == str(current_user.id),
        )
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return ChatSessionListResponse(items=sessions, total=len(sessions))


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    return _get_session_or_404(session_id, current_user.tenant_id, str(current_user.id), db)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    session = _get_session_or_404(session_id, current_user.tenant_id, str(current_user.id), db)
    db.delete(session)
    db.commit()


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
def list_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """Lista todas as mensagens de uma sessão ordenadas por created_at."""
    # Valida que a sessão pertence ao tenant + user
    session = _get_session_or_404(session_id, current_user.tenant_id, str(current_user.id), db)
    messages = sorted(session.messages, key=lambda m: m.created_at)
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=len(messages),
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
def send_message(
    session_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Pipeline RAG completo:
      1. Valida sessão
      2. Embed da pergunta
      3. Retrieval no Pinecone
      4. Gera resposta via Claude
      5. Persiste user + assistant Message
    """
    session = _get_session_or_404(session_id, current_user.tenant_id, str(current_user.id), db)

    # 1. Histórico recente para contexto (sem a pergunta atual)
    history = _get_recent_history(session, limit=settings.RAG_HISTORY_MESSAGES)

    # 2. Embed da pergunta
    query_vector = embed_query(payload.content)

    # 3. Retrieval
    chunks = retrieve_chunks(query_vector, tenant_id=current_user.tenant_id)

    # 4. Gera resposta
    rag_result = generate_answer(
        question=payload.content,
        chunks=chunks,
        history=history,
    )

    # 5. Persiste — user primeiro, depois assistant (só após resposta bem-sucedida)
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=payload.content,
    )
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=rag_result.answer,
        source_chunks=json.dumps(rag_result.source_chunk_ids) if rag_result.source_chunk_ids else None,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    logger.info(
        "Chat: session=%s tenant=%s chunks=%d",
        session_id, current_user.tenant_id, len(chunks),
    )

    return ChatResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )
