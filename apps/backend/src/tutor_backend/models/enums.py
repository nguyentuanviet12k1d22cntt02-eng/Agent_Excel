"""Các giá trị liệt kê dùng trong CSDL và API (khớp openapi.yaml, csdl.md)."""

from enum import StrEnum

from sqlalchemy import CheckConstraint


class Role(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class StudyGroup(StrEnum):
    EXPERIMENTAL = "experimental"
    CONTROL = "control"


class TextbookStatus(StrEnum):
    UPLOADED = "uploaded"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ScriptStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ScriptOrigin(StrEnum):
    AI = "ai"
    TEACHER = "teacher"
    AI_EDITED = "ai_edited"


class SessionMode(StrEnum):
    TUTOR = "tutor"
    CONTROL = "control"


class SessionStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class StepStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"


class SupportState(StrEnum):
    STRUGGLING = "struggling"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"


class Instrument(StrEnum):
    PAAS = "paas"
    SUS = "sus"
    SATISFACTION = "satisfaction"


def enum_check(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """Ràng buộc CHECK cột chỉ nhận các giá trị của enum (chạy được trên PostgreSQL và SQLite)."""
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or column)
