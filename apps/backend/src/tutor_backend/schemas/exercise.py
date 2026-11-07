"""Schema bài tập (openapi.yaml: Exercise)."""

import uuid

from pydantic import BaseModel, Field

from tutor_backend.schemas.common import ApiModel
from tutor_backend.schemas.script import ScriptVersionSummary


class ExerciseOut(ApiModel):
    id: uuid.UUID
    code: str
    title: str
    sheet_name: str
    prompt_text: str | None = None
    textbook_ids: list[uuid.UUID] = []
    latest_version: ScriptVersionSummary | None = None
    published_version: ScriptVersionSummary | None = None
    warnings: list[str] = []


class ExerciseUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    prompt_text: str | None = Field(None, max_length=20000)
    textbook_ids: list[uuid.UUID] | None = None
