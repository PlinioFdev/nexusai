"""
Testes M2 — Ingestão.

Segue o padrão do conftest.py do M1:
- fixture `db` com SQLite in-memory
- fixture `client` com TestClient
- mocks para serviços externos (Voyage AI, Pinecone, Celery)
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.chunking import split_text
from app.services.storage import StorageError, _validate


# =========================================================================== #
# Helpers de fixture                                                            #
# =========================================================================== #

def _create_tenant(db: Session, slug: str = "test-tenant") -> Tenant:
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant", slug=slug)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _create_user(db: Session, tenant: Tenant, email: str = "user@test.com") -> User:
    from app.core.security import hash_password
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password("password123"),
        full_name="Test User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(client: TestClient, email: str = "user@test.com") -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# =========================================================================== #
# Chunking                                                                      #
# =========================================================================== #

class TestSplitText:
    def test_empty_returns_empty(self):
        assert split_text("") == []

    def test_whitespace_returns_empty(self):
        assert split_text("   \n\t  ") == []

    def test_short_text_single_chunk(self):
        chunks = split_text("Hello world.")
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test_long_text_multiple_chunks_ordered(self):
        text = " ".join(["word"] * 2000)
        chunks = split_text(text)
        assert len(chunks) > 1
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_chunk_respects_max_tokens(self):
        text = " ".join(["word"] * 2000)
        for chunk in split_text(text):
            assert chunk.token_count <= 512

    def test_adjacent_chunks_have_overlap(self):
        """
        Verifica que chunks adjacentes se sobrepõem em conteúdo.
        Prova: chunk[N+1] começa antes do fim de chunk[N].
        Estratégia: decodifica os tokens de volta e verifica que o
        início do chunk[1] aparece dentro do chunk[0].
        """
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = split_text(text)
        assert len(chunks) >= 2

        # O início do chunk[1] deve estar contido no final do chunk[0]
        # Pegamos as primeiras 5 palavras do chunk[1] e verificamos
        # que pelo menos uma aparece no chunk[0]
        start_of_second = chunks[1].content.split()[:5]
        assert any(w in chunks[0].content for w in start_of_second), (
            "chunk[1] deve compartilhar conteúdo com o final de chunk[0]"
        )


# =========================================================================== #
# Storage                                                                       #
# =========================================================================== #

class TestValidateFile:
    def test_pdf_accepted(self):
        assert _validate("report.pdf", 1024) == "pdf"

    def test_txt_accepted(self):
        assert _validate("notes.TXT", 1024) == "txt"

    def test_invalid_extension_raises(self):
        with pytest.raises(StorageError, match="não suportado"):
            _validate("file.exe", 1024)

    def test_too_large_raises(self):
        with pytest.raises(StorageError, match="muito grande"):
            _validate("file.pdf", 20 * 1024 * 1024 + 1)

    def test_exactly_at_limit_accepted(self):
        assert _validate("file.pdf", 20 * 1024 * 1024) == "pdf"


# =========================================================================== #
# Embedding — batching                                                          #
# =========================================================================== #

class TestEmbedTexts:
    def test_empty_list_returns_empty_without_api_call(self):
        from app.services.embedding import embed_texts
        with patch("app.services.embedding._get_client") as mock_get:
            result = embed_texts([])
        assert result == []
        mock_get.assert_not_called()

    def test_single_text_returns_single_vector(self):
        from app.services.embedding import embed_texts
        fake = [0.1] * 1024
        mock_result = MagicMock()
        mock_result.embeddings = [fake]
        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result
        with patch("app.services.embedding._get_client", return_value=mock_client):
            result = embed_texts(["hello"])
        assert result == [fake]

    def test_large_batch_splits_correctly(self):
        from app.services.embedding import embed_texts, _BATCH_SIZE
        n = _BATCH_SIZE + 5
        fake = [0.0] * 1024

        r1 = MagicMock()
        r1.embeddings = [fake] * _BATCH_SIZE
        r2 = MagicMock()
        r2.embeddings = [fake] * 5

        mock_client = MagicMock()
        mock_client.embed.side_effect = [r1, r2]

        with patch("app.services.embedding._get_client", return_value=mock_client):
            result = embed_texts([f"t{i}" for i in range(n)])

        assert len(result) == n
        assert mock_client.embed.call_count == 2


# =========================================================================== #
# Endpoint /api/v1/documents                                                    #
# =========================================================================== #

class TestUploadEndpoint:
    def test_unauthenticated_returns_403(self, client: TestClient):
        # HTTPBearer retorna 403 quando não há token (comportamento padrão FastAPI)
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")},
        )
        assert resp.status_code == 403

    def test_invalid_extension_returns_422(self, client: TestClient, db: Session):
        tenant = _create_tenant(db)
        _create_user(db, tenant)
        headers = _auth_headers(client)

        with patch("app.api.v1.endpoints.documents.ingest_document") as mock_task:
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("malware.exe", io.BytesIO(b"evil"), "application/octet-stream")},
                headers=headers,
            )

        assert resp.status_code == 422
        mock_task.delay.assert_not_called()

    def test_valid_pdf_returns_202_and_enqueues(self, client: TestClient, db: Session):
        tenant = _create_tenant(db)
        _create_user(db, tenant)
        headers = _auth_headers(client)

        with (
            patch("app.services.storage.save") as mock_save,
            patch("app.api.v1.endpoints.documents.ingest_document") as mock_task,
        ):
            mock_save.return_value = ("/app/uploads/t1/abc.pdf", "pdf", 1024)

            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("doc.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
                headers=headers,
            )

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == DocumentStatus.PENDING.value
        assert body["file_type"] == "pdf"
        mock_task.delay.assert_called_once()

    def test_get_document_wrong_tenant_returns_404(self, client: TestClient, db: Session):
        """Tenant B não pode ver documentos do Tenant A — 404, não 403."""
        tenant_a = _create_tenant(db, slug="tenant-a")
        doc = Document(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            name="secret.pdf",
            file_type="pdf",
            file_size_bytes=100,
            storage_path="/tmp/secret.pdf",
            status=DocumentStatus.READY,
        )
        db.add(doc)
        db.commit()

        tenant_b = _create_tenant(db, slug="tenant-b")
        _create_user(db, tenant_b, email="b@test.com")
        headers_b = _auth_headers(client, email="b@test.com")

        resp = client.get(f"/api/v1/documents/{doc.id}", headers=headers_b)
        assert resp.status_code == 404
