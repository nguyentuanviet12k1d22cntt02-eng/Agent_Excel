"""Schema job sinh kịch bản (openapi.yaml: GenerationJob, /exercises/{id}/generation-jobs)."""

import uuid

from pydantic import BaseModel, Field

from tutor_backend.models.enums import JobStatus
from tutor_backend.schemas.common import ApiModel


class GenerationRequest(BaseModel):
    model: str | None = Field(None, max_length=80, description="Ghi đè mô hình mặc định, ví dụ mercury-2")
    instructions: str | None = Field(None, max_length=2000, description="Lưu ý thêm của giảng viên cho AI")


class GenerationJobOut(ApiModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    status: JobStatus
    stage: str | None = None
    attempts: int = 0
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    result_version_id: uuid.UUID | None = None
    error: str | None = None
