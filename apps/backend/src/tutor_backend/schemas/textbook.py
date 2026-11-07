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
