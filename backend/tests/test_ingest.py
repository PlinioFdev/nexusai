"""
Testes M2 — Ingestão.

Segue o padrão do conftest.py do M1:
- fixture `db` com SQLite in-memory
- fixture `client` com TestClient
- mocks para serviços externos (Voyage AI, Pinecone, Celery)
"""

import asyncio
import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.chunking import split_text
from app.services.storage import StorageError, _validate, delete, download_to_tmp, save


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


def _auth_headers(client: TestClient, slug: str = "test-tenant", email: str = "user@test.com") -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123", "slug": slug},
    )
    assert resp.status_code == 200, resp.json()
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
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = split_text(text)
        assert len(chunks) >= 2
        start_of_second = chunks[1].content.split()[:5]
        assert any(w in chunks[0].content for w in start_of_second)


# =========================================================================== #
# Storage — validação                                                           #
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
# Storage — R2 (prod)                                                           #
# =========================================================================== #

class TestStorageR2:
    """Testa o comportamento de storage em modo produção (Cloudflare R2)."""

    def test_save_prod_uploads_to_r2(self):
        """save() em prod chama put_object e retorna chave S3 correta."""
        mock_s3 = MagicMock()
        file_content = b"fake pdf content"

        mock_file = MagicMock()
        mock_file.filename = "doc.pdf"
        mock_file.read = AsyncMock(return_value=file_content)

        async def _run():
            with (
                patch("app.services.storage._get_s3_client", return_value=mock_s3),
                patch("app.services.storage.settings") as ms,
            ):
                ms.is_development = False
                ms.AWS_BUCKET_NAME = "test-bucket"
                return await save(mock_file, "tenant-xyz")

        storage_path, file_type, size = asyncio.run(_run())

        assert file_type == "pdf"
        assert size == len(file_content)
        assert storage_path.startswith("tenants/tenant-xyz/")
        assert storage_path.endswith(".pdf")
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == storage_path
        assert call_kwargs["Body"] == file_content

    def test_delete_prod_calls_delete_object(self):
        """delete() em prod chama delete_object no R2."""
        mock_s3 = MagicMock()

        with (
            patch("app.services.storage._get_s3_client", return_value=mock_s3),
            patch("app.services.storage.settings") as ms,
        ):
            ms.is_development = False
            ms.AWS_BUCKET_NAME = "test-bucket"
            delete("tenants/abc/file.pdf")

        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="tenants/abc/file.pdf",
        )

    def test_delete_prod_is_silent_on_error(self):
        """delete() em prod não propaga exceção (idempotente)."""
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = Exception("R2 unavailable")

        with (
            patch("app.services.storage._get_s3_client", return_value=mock_s3),
            patch("app.services.storage.settings") as ms,
        ):
            ms.is_development = False
            ms.AWS_BUCKET_NAME = "test-bucket"
            delete("tenants/abc/file.pdf")  # não deve lançar

    def test_download_to_tmp_calls_download_file_and_returns_path(self):
        """download_to_tmp() chama download_file e retorna Path do arquivo temporário."""
        mock_s3 = MagicMock()

        def fake_download(bucket, key, dest):
            Path(dest).write_bytes(b"r2 content")

        mock_s3.download_file.side_effect = fake_download

        with (
            patch("app.services.storage._get_s3_client", return_value=mock_s3),
            patch("app.services.storage.settings") as ms,
        ):
            ms.AWS_BUCKET_NAME = "test-bucket"
            result = download_to_tmp("tenants/abc/file.txt", "txt")

        assert result.exists()
        assert result.suffix == ".txt"
        assert result.read_bytes() == b"r2 content"
        mock_s3.download_file.assert_called_once()
        args = mock_s3.download_file.call_args[0]
        assert args[0] == "test-bucket"
        assert args[1] == "tenants/abc/file.txt"
        result.unlink(missing_ok=True)

    def test_download_to_tmp_cleans_up_on_download_error(self):
        """download_to_tmp() remove o arquivo temporário se download_file falhar."""
        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = Exception("Network error")

        with (
            patch("app.services.storage._get_s3_client", return_value=mock_s3),
            patch("app.services.storage.settings") as ms,
        ):
            ms.AWS_BUCKET_NAME = "test-bucket"
            with pytest.raises(Exception, match="Network error"):
                download_to_tmp("tenants/abc/file.txt", "txt")


# =========================================================================== #
# Ingest — extração de texto em prod                                            #
# =========================================================================== #

class TestExtractTextProd:
    def test_extract_txt_prod_downloads_reads_and_cleans_up(self, tmp_path):
        """Em prod, _extract_text baixa do R2, lê o conteúdo e deleta o arquivo temporário."""
        tmp_file = tmp_path / "test.txt"
        tmp_file.write_text("hello from r2", encoding="utf-8")

        with (
            patch("app.tasks.ingest.settings") as ms,
            patch("app.tasks.ingest.download_to_tmp", return_value=tmp_file) as mock_dl,
        ):
            ms.is_development = False
            from app.tasks.ingest import _extract_text
            result = _extract_text("tenants/abc/file.txt", "txt")

        assert result == "hello from r2"
        mock_dl.assert_called_once_with("tenants/abc/file.txt", "txt")
        assert not tmp_file.exists()  # finally deletou o arquivo temporário


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
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")},
        )
        assert resp.status_code == 403

    def test_invalid_extension_returns_422(self, client: TestClient, db: Session):
        tenant = _create_tenant(db)
        _create_user(db, tenant)
        headers = _auth_headers(client, slug=tenant.slug)

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
        headers = _auth_headers(client, slug=tenant.slug)

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
        headers_b = _auth_headers(client, slug="tenant-b", email="b@test.com")

        resp = client.get(f"/api/v1/documents/{doc.id}", headers=headers_b)
        assert resp.status_code == 404
