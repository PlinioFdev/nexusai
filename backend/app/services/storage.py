"""
Storage service — abstração de I/O de arquivos.

Dev (M2): salva em volume local (UPLOAD_DIR).
Prod (M5): trocar `save` e `delete` por chamadas S3/R2
           sem alterar nenhum caller.
"""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


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


async def save(file: UploadFile, tenant_id: str) -> tuple[str, str, int]:
    """
    Salva o arquivo no volume local.

    Returns:
        (storage_path, file_type, file_size_bytes)

    Raises:
        StorageError: extensão inválida ou arquivo muito grande.
    """
    content = await file.read()
    file_type = _validate(file.filename or "", len(content))

    dest_dir = Path(settings.UPLOAD_DIR) / tenant_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    storage_path = str(dest_dir / f"{uuid.uuid4()}.{file_type}")
    Path(storage_path).write_bytes(content)

    return storage_path, file_type, len(content)


def delete(storage_path: str) -> None:
    """Remove o arquivo. Silencioso se não existir (idempotente)."""
    try:
        os.remove(storage_path)
    except FileNotFoundError:
        pass
