"""Schema revision kịch bản (openapi.yaml: ScriptVersionSummary, ScriptVersion)."""

import uuid
from datetime import datetime
from typing import Any

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
    reviewed_by: uuid.UUID | None = None
    review_note: str | None = None
    published_at: datetime | None = None


class ScriptVersionOut(ScriptVersionSummary):
    content: dict[str, Any]
    self_check_report: dict[str, Any] | None = None
