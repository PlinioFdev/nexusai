from datetime import datetime
from pydantic import BaseModel, field_validator


# ── ChatSession ──────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: str = "Nova conversa"

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title não pode ser vazio")
        return v.strip()


class ChatSessionResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int


# ── Message ──────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content não pode ser vazio")
        return v.strip()


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    source_chunks: str | None = None  # JSON array de chunk IDs
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Retorno do endpoint de chat: mensagem do usuário + resposta do assistant."""
    user_message: MessageResponse
    assistant_message: MessageResponse
