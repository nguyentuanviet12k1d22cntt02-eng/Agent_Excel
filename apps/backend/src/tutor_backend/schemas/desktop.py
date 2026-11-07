"""Schema API cho Desktop (openapi.yaml, tag desktop): bài được giao, kịch bản, phiên, nhật ký, phiếu."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tutor_backend.models.enums import Instrument, SessionMode, SessionStatus, StepStatus
from tutor_backend.schemas.common import ExerciseCode

MAX_EVENTS_PER_BATCH = 500


class Assignment(BaseModel):
    exercise_code: str
    title: str
    revision: int
    due_at: datetime | None = None
    starter_file_url: str
    mode: SessionMode


class DesktopScript(BaseModel):
    version_id: uuid.UUID
    mode: SessionMode
    content: dict[str, Any]
    # Snapshot JSON của file đề/đáp án, chỉ vùng điều kiện cần (snapshot.md mục 7): Desktop không có đáp án
    references: dict[str, Any]


class ClientInfo(BaseModel):
    app_version: str | None = None
    windows_version: str | None = None
    excel_version: str | None = None
    office_ui_language: int | None = Field(None, description="LanguageID, ví dụ 1066 = tiếng Việt")
    dpi: int | None = None
    monitor_count: int | None = None


class SessionUpsert(BaseModel):
    exercise_code: ExerciseCode
    script_version_id: uuid.UUID
    mode: SessionMode
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None
    client_info: ClientInfo = ClientInfo()
    policy_params: dict[str, Any] = {}


class StepProgressIn(BaseModel):
    status: StepStatus
    started_at: datetime | None = None
    done_at: datetime | None = None
    fail_count: int = Field(0, ge=0)
    max_hint_level: int = Field(0, ge=0, le=4)
    help_count: int = Field(0, ge=0)
    idle_seconds: int = Field(0, ge=0)
    score: int | None = Field(None, ge=0, le=2)


class EventIn(BaseModel):
    seq: int = Field(ge=0, description="Số thứ tự tăng dần trong phiên, để chống ghi trùng")
    occurred_at: datetime
    kind: str = Field(min_length=1, max_length=40)
    step_id: str | None = Field(None, max_length=40)
    data: dict[str, Any] = {}


class EventBatch(BaseModel):
    events: list[EventIn] = Field(max_length=MAX_EVENTS_PER_BATCH)


class EventBatchResult(BaseModel):
    accepted: int
    duplicates: int


class SurveyIn(BaseModel):
    instrument: Instrument
    session_id: uuid.UUID | None = None
    answers: int | list[int] | dict[str, Any]
