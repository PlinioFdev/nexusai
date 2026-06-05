"""
Storage service — abstração de I/O de arquivos.
Dev:  salva em volume local (UPLOAD_DIR).
Prod: salva/deleta/baixa do Cloudflare R2 via API S3-compatible.
      Callers de save() e delete() não precisam mudar.
"""
import os
import tempfile
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from fastapi import UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

_s3_client = None  # lazy init — nunca instanciar na importação


class StorageError(Exception):
    """Erro de validação de arquivo — mensagem exibida diretamente ao usuário."""


def _validate(filename: str, size: int) -> str:
    """Valida extensão e tamanho. Retorna extensão normalizada ou lança StorageError."""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise StorageError(f"Tipo não suportado: .{ext}. Use PDF ou TXT.")
    if size > MAX_FILE_SIZE_BYTES:
        raise StorageError(f"Arquivo muito grande ({size // 1024 // 1024} MB). Limite: 20 MB.")
    return ext


def _get_s3_client():
    """Lazy init: instancia o cliente boto3 só quando necessário (nunca na importação)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
    return _s3_client


async def save(file: UploadFile, tenant_id: str) -> tuple[str, str, int]:
    """
    Dev:  salva no volume local. Retorna caminho absoluto.
    Prod: faz upload para R2. Retorna chave S3 (ex: "tenants/{tenant_id}/{uuid}.pdf").

    Returns:
        (storage_path, file_type, file_size_bytes)
    Raises:
        StorageError: extensão inválida ou arquivo muito grande.
    """
    content = await file.read()
    file_type = _validate(file.filename or "", len(content))

    if settings.is_development:
        dest_dir = Path(settings.UPLOAD_DIR) / tenant_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        storage_path = str(dest_dir / f"{uuid.uuid4()}.{file_type}")
        Path(storage_path).write_bytes(content)
    else:
        key = f"tenants/{tenant_id}/{uuid.uuid4()}.{file_type}"
        _get_s3_client().put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType="application/pdf" if file_type == "pdf" else "text/plain",
        )
        storage_path = key

    return storage_path, file_type, len(content)


def delete(storage_path: str) -> None:
    """
    Dev:  remove arquivo local. Silencioso se não existir (idempotente).
    Prod: deleta objeto do R2. Silencioso se não existir.
    """
    if settings.is_development:
        try:
            os.remove(storage_path)
        except FileNotFoundError:
            pass
    else:
        try:
            _get_s3_client().delete_object(
                Bucket=settings.AWS_BUCKET_NAME,
                Key=storage_path,
            )
        except Exception:
            pass


def download_to_tmp(storage_path: str, file_type: str) -> Path:
    """
    Baixa objeto do R2 para arquivo temporário em /tmp.
    Retorna o Path do arquivo temporário.

    Atenção: responsabilidade do caller deletar o arquivo após o uso (via finally).
    Nunca chamar em modo development — storage_path é caminho local, não chave S3.
    """
    tmp = tempfile.NamedTemporaryFile(
        suffix=f".{file_type}", delete=False, dir="/tmp"
    )
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        _get_s3_client().download_file(settings.AWS_BUCKET_NAME, storage_path, tmp.name)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path
