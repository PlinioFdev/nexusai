from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
