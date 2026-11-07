"""Schema giáo trình (openapi.yaml: Textbook)."""

import uuid

from tutor_backend.models.enums import FileType, TextbookStatus
from tutor_backend.schemas.common import ApiModel


class TextbookOut(ApiModel):
    id: uuid.UUID
    title: str
    file_type: FileType
    status: TextbookStatus
    chunk_count: int = 0
    error: str | None = None


class PassageOut(ApiModel):
    """Một đoạn giáo trình tìm được (RAG)."""

    chunk_id: uuid.UUID
    textbook_id: uuid.UUID
    textbook_title: str
    heading: str
    page: int | None = None
    content: str
    score: float
