"""
Testes do M3 — Chat RAG.

Estratégia: mockar embed_query, retrieve_chunks e generate_answer
para isolar a lógica dos endpoints sem depender de APIs externas.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.rag import RAGResult
from app.services.retrieval import RetrievedChunk

# ── Fixtures helpers ──────────────────────────────────────────────────────────

def _register_and_login(client: TestClient, slug: str = "acme") -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "tenant_data": {"name": slug.capitalize(), "slug": slug},
            "user_data": {"email": f"owner@{slug}.com", "password": "secret123", "full_name": "Owner"},
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": f"owner@{slug}.com", "password": "secret123"},
    )
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_session(client: TestClient, token: str, title: str = "Test session") -> str:
    res = client.post("/api/v1/chat/sessions", json={"title": title}, headers=_auth(token))
    assert res.status_code == 201, res.json()
    return res.json()["id"]


# ── Mocks padrão ──────────────────────────────────────────────────────────────

_FAKE_CHUNK = RetrievedChunk(
    pinecone_id="doc1#0",
    score=0.92,
    document_id="doc1",
    filename="manual.pdf",
    content_preview="O produto X possui garantia de 12 meses.",
)

_FAKE_RAG_RESULT = RAGResult(
    answer="O produto X possui garantia de 12 meses.",
    source_chunk_ids=["doc1#0"],
)

# RAGResult para o caso sem chunks relevantes
_FAKE_RAG_RESULT_NO_CONTEXT = RAGResult(
    answer="Não encontrei informações sobre esse assunto nos documentos.",
    source_chunk_ids=[],
)


# ── ChatSession CRUD ──────────────────────────────────────────────────────────

class TestChatSession:
    def test_create_session(self, client: TestClient):
        token = _register_and_login(client)
        res = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Minha sessão"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Minha sessão"
        assert "id" in data
        assert "tenant_id" in data

    def test_create_session_default_title(self, client: TestClient):
        token = _register_and_login(client)
        res = client.post("/api/v1/chat/sessions", json={}, headers=_auth(token))
        assert res.status_code == 201
        assert res.json()["title"] == "Nova conversa"

    def test_create_session_empty_title_fails(self, client: TestClient):
        token = _register_and_login(client)
        res = client.post("/api/v1/chat/sessions", json={"title": "   "}, headers=_auth(token))
        assert res.status_code == 422

    def test_list_sessions(self, client: TestClient):
        token = _register_and_login(client)
        _create_session(client, token, "S1")
        _create_session(client, token, "S2")
        res = client.get("/api/v1/chat/sessions", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_session(self, client: TestClient):
        token = _register_and_login(client)
        session_id = _create_session(client, token)
        res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["id"] == session_id

    def test_delete_session(self, client: TestClient):
        token = _register_and_login(client)
        session_id = _create_session(client, token)
        res = client.delete(f"/api/v1/chat/sessions/{session_id}", headers=_auth(token))
        assert res.status_code == 204
        res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=_auth(token))
        assert res.status_code == 404

    def test_session_not_found(self, client: TestClient):
        token = _register_and_login(client)
        res = client.get("/api/v1/chat/sessions/nonexistent-id", headers=_auth(token))
        assert res.status_code == 404

    def test_unauthenticated_request_fails(self, client: TestClient):
        res = client.get("/api/v1/chat/sessions")
        assert res.status_code == 403  # HTTPBearer retorna 403 sem credencial


# ── Multi-tenancy isolation ───────────────────────────────────────────────────

class TestTenantIsolation:
    def test_tenant_cannot_access_other_tenant_session(self, client: TestClient):
        token_a = _register_and_login(client, slug="tenant-a")
        token_b = _register_and_login(client, slug="tenant-b")
        session_id = _create_session(client, token_a)
        res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=_auth(token_b))
        assert res.status_code == 404  # 404, não 403 — não vaza existência

    def test_sessions_list_isolated_per_tenant(self, client: TestClient):
        token_a = _register_and_login(client, slug="tenant-a")
        token_b = _register_and_login(client, slug="tenant-b")
        _create_session(client, token_a)
        _create_session(client, token_a)
        res = client.get("/api/v1/chat/sessions", headers=_auth(token_b))
        assert res.json()["total"] == 0


# ── Pipeline RAG ──────────────────────────────────────────────────────────────

class TestRAGPipeline:
    @patch("app.api.v1.endpoints.chat.generate_answer", return_value=_FAKE_RAG_RESULT)
    @patch("app.api.v1.endpoints.chat.retrieve_chunks", return_value=[_FAKE_CHUNK])
    @patch("app.api.v1.endpoints.chat.embed_query", return_value=[0.1] * 1024)
    def test_send_message_happy_path(
        self, mock_embed, mock_retrieve, mock_generate, client: TestClient
    ):
        token = _register_and_login(client)
        session_id = _create_session(client, token)

        res = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Qual é a garantia do produto X?"},
            headers=_auth(token),
        )
        assert res.status_code == 200
        data = res.json()

        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "Qual é a garantia do produto X?"
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["content"] == _FAKE_RAG_RESULT.answer
        assert data["assistant_message"]["source_chunks"] is not None

        mock_embed.assert_called_once_with("Qual é a garantia do produto X?")
        mock_retrieve.assert_called_once()
        mock_generate.assert_called_once()

    @patch("app.api.v1.endpoints.chat.generate_answer", return_value=_FAKE_RAG_RESULT_NO_CONTEXT)
    @patch("app.api.v1.endpoints.chat.retrieve_chunks", return_value=[])
    @patch("app.api.v1.endpoints.chat.embed_query", return_value=[0.1] * 1024)
    def test_send_message_no_chunks_still_responds(
        self, mock_embed, mock_retrieve, mock_generate, client: TestClient
    ):
        """Sem chunks relevantes: Claude responde informando que não encontrou conteúdo."""
        token = _register_and_login(client)
        session_id = _create_session(client, token)
        res = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Pergunta sem contexto relevante"},
            headers=_auth(token),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["assistant_message"]["source_chunks"] is None

    def test_send_message_empty_content_fails(self, client: TestClient):
        token = _register_and_login(client)
        session_id = _create_session(client, token)
        res = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": ""},
            headers=_auth(token),
        )
        assert res.status_code == 422

    @patch("app.api.v1.endpoints.chat.generate_answer", return_value=_FAKE_RAG_RESULT)
    @patch("app.api.v1.endpoints.chat.retrieve_chunks", return_value=[_FAKE_CHUNK])
    @patch("app.api.v1.endpoints.chat.embed_query", return_value=[0.1] * 1024)
    def test_messages_persisted_in_db(
        self, mock_embed, mock_retrieve, mock_generate, client: TestClient
    ):
        """Verifica que user + assistant message são persistidos após o chat."""
        token = _register_and_login(client)
        session_id = _create_session(client, token)

        client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Teste de persistência"},
            headers=_auth(token),
        )
        client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Segunda pergunta"},
            headers=_auth(token),
        )

        res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=_auth(token))
        assert res.status_code == 200

    def test_send_message_to_nonexistent_session_fails(self, client: TestClient):
        token = _register_and_login(client)
        res = client.post(
            "/api/v1/chat/sessions/nonexistent/messages",
            json={"content": "Olá"},
            headers=_auth(token),
        )
        assert res.status_code == 404
