"""
Endpoints do widget embeddable.

Rotas:
  GET  /widget/api-key  → retorna api_key atual do tenant (requer JWT OWNER/ADMIN)
  POST /widget/api-key  → gera/rotaciona api_key do tenant (requer JWT OWNER/ADMIN)
  POST /widget/chat     → endpoint público autenticado por api_key (sem JWT)
"""

import json
import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import require_roles
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.models.chat import ChatSession, Message
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.embedding import embed_query
from app.services.retrieval import retrieve_chunks
from app.services.rag import generate_answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["widget"])

# Email do user de sistema criado por tenant para isolar sessões do widget
_WIDGET_BOT_EMAIL_SUFFIX = "widget-bot@nexusai.internal"


# ── Schemas ───────────────────────────────────────────────────────────────────

class ApiKeyResponse(BaseModel):
    api_key: str


class WidgetChatRequest(BaseModel):
    api_key: str
    session_id: str | None = None
    message: str


class WidgetChatResponse(BaseModel):
    session_id: str
    answer: str
    source_chunks: list[str] | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _widget_bot_email(slug: str) -> str:
    """Email único do user de sistema por tenant."""
    return f"{slug}.{_WIDGET_BOT_EMAIL_SUFFIX}"


def _get_or_create_widget_bot(tenant: Tenant, db: Session) -> User:
    """
    Retorna o user de sistema do widget para este tenant.
    Cria na primeira vez — reutiliza nas seguintes.
    Isolado do OWNER: sessões do widget não aparecem no dashboard.
    """
    email = _widget_bot_email(str(tenant.slug))
    bot = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email == email)
        .first()
    )
    if bot:
        return bot

    bot = User(
        tenant_id=tenant.id,
        email=email,
        # Senha aleatória — nunca usada para login
        hashed_password=hash_password(str(uuid.uuid4())),
        full_name="Widget Bot",
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    logger.info("Widget bot criado para tenant=%s", tenant.slug)
    return bot


def _get_tenant_by_api_key(api_key: str, db: Session) -> Tenant:
    """Resolve tenant pelo api_key — 401 genérico para não vazar existência."""
    tenant = db.query(Tenant).filter(Tenant.api_key == api_key).first()
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida",
        )
    return tenant


def _get_or_create_session(
    session_id: str | None,
    tenant: Tenant,
    bot: User,
    db: Session,
) -> ChatSession:
    """Retorna sessão existente (do tenant) ou cria uma nova para o widget."""
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.tenant_id == tenant.id,
                ChatSession.user_id == str(bot.id),
            )
            .first()
        )
        if session:
            return session
        # session_id fornecido mas não encontrado — cria nova silenciosamente
    session = ChatSession(
        tenant_id=tenant.id,
        user_id=str(bot.id),
        title="Widget",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_recent_history(session: ChatSession, limit: int) -> list[dict[str, str]]:
    """Retorna as últimas `limit` mensagens — mesmo padrão de chat.py."""
    messages = (
        sorted(session.messages, key=lambda m: m.created_at)[-limit:]
        if session.messages
        else []
    )
    return [{"role": m.role, "content": m.content} for m in messages]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/api-key", response_model=ApiKeyResponse)
def get_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> dict:
    """Retorna a api_key atual do tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    if tenant.api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key ainda não gerada. Use POST /widget/api-key para criar.",
        )
    return {"api_key": tenant.api_key}


@router.post("/api-key", response_model=ApiKeyResponse)
def generate_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> dict:
    """
    Gera ou rotaciona a api_key do tenant. Invalida a chave anterior.
    Também cria o widget bot user se ainda não existir.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    # Garante que o widget bot existe antes de ativar o widget
    _get_or_create_widget_bot(tenant, db)

    tenant.api_key = secrets.token_hex(32)  # 64 chars hex
    db.commit()
    db.refresh(tenant)
    return {"api_key": tenant.api_key}


@router.post("/chat", response_model=WidgetChatResponse)
def widget_chat(
    body: WidgetChatRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Endpoint público consumido pelo widget embeddable.
    Não requer JWT — autentica pelo api_key do tenant.
    Pipeline idêntico ao chat.py: embed → retrieval → RAG → persist.
    Sessões criadas pelo widget são atribuídas ao widget bot — isoladas do OWNER.
    """
    if not body.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mensagem não pode ser vazia",
        )

    tenant = _get_tenant_by_api_key(body.api_key, db)
    bot = _get_or_create_widget_bot(tenant, db)
    session = _get_or_create_session(body.session_id, tenant, bot, db)

    history = _get_recent_history(session, limit=settings.RAG_HISTORY_MESSAGES)
    query_vector = embed_query(body.message)
    chunks = retrieve_chunks(query_vector, tenant_id=str(tenant.id))
    rag_result = generate_answer(
        question=body.message,
        chunks=chunks,
        history=history,
    )

    user_msg = Message(
        session_id=str(session.id),
        role="user",
        content=body.message,
    )
    assistant_msg = Message(
        session_id=str(session.id),
        role="assistant",
        content=rag_result.answer,
        source_chunks=(
            json.dumps(rag_result.source_chunk_ids) if rag_result.source_chunk_ids else None
        ),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    logger.info(
        "Widget chat: session=%s tenant=%s chunks=%d",
        session.id, tenant.id, len(chunks),
    )

    return {
        "session_id": str(session.id),
        "answer": rag_result.answer,
        "source_chunks": rag_result.source_chunk_ids or None,
    }
