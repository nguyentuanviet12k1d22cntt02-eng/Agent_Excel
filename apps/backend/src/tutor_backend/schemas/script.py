"""Schema revision kịch bản (openapi.yaml: ScriptVersionSummary, ScriptVersion)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tutor_backend.models.enums import ScriptOrigin, ScriptStatus
from tutor_backend.schemas.common import ApiModel


class ScriptVersionSummary(ApiModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    revision: int
    status: ScriptStatus
    origin: ScriptOrigin
    parent_version_id: uuid.UUID | None = None
    created_at: datetime
    created_by: uuid.UUID | None = None
    created_by_name: str | None = None
    reviewed_by: uuid.UUID | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    published_at: datetime | None = None


class ScriptVersionOut(ScriptVersionSummary):
    content: dict[str, Any]
    self_check_report: dict[str, Any] | None = None


class ScriptCreate(BaseModel):
    """Lưu revision mới; nội dung kiểm theo lược đồ v1 ở service (lỗi trả về kèm đường dẫn JSON)."""

    parent_version_id: uuid.UUID | None = None
    content: dict[str, Any]


class PreviewBundle(BaseModel):
    """Một revision bất kỳ (kể cả nháp) kèm snapshot tham chiếu, để giảng viên chạy thử trên Desktop."""

    version_id: uuid.UUID
    exercise_id: uuid.UUID
    exercise_code: str
    exercise_title: str
    revision: int
    status: ScriptStatus
    content: dict[str, Any]
    references: dict[str, Any]  # như DesktopScript.references (snapshot.md mục 7)


class RejectRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
