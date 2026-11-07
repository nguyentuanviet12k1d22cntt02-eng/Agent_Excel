"""Bảng thực hành và thực nghiệm: `practice_sessions`, `step_progress`, `event_logs`, `skill_states`,
`survey_responses` (csdl.md mục 2.4).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, CreatedAtMixin, JsonType, TimestampMixin, utcnow, uuid_pk
from tutor_backend.models.enums import (
    Instrument,
    SessionMode,
    SessionStatus,
    StepStatus,
    SupportState,
    enum_check,
)


class PracticeSession(TimestampMixin, Base):
    """`id` do Desktop sinh (UUID) để tạo phiên được cả khi mất mạng; `script_version_id` cố định cả phiên."""

    __tablename__ = "practice_sessions"
    __table_args__ = (enum_check("mode", SessionMode), enum_check("status", SessionStatus))

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    script_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("script_versions.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(16))
    client_info: Mapped[dict[str, Any]] = mapped_column(default=dict)
    policy_params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]


class StepProgress(Base):
    __tablename__ = "step_progress"
    __table_args__ = (enum_check("status", StepStatus),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    step_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime | None]
    done_at: Mapped[datetime | None]
    fail_count: Mapped[int] = mapped_column(default=0)
    max_hint_level: Mapped[int] = mapped_column(default=0)
    help_count: Mapped[int] = mapped_column(default=0)
    idle_seconds: Mapped[int] = mapped_column(default=0)
    score: Mapped[int | None] = mapped_column(SmallInteger)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class EventLog(CreatedAtMixin, Base):
    """`UNIQUE (session_id, seq)`: Desktop gửi lại một lô bị lỗi mạng thì không ghi trùng."""

    __tablename__ = "event_logs"
    __table_args__ = (
        UniqueConstraint("session_id", "seq"),
        Index("ix_event_logs_session_occurred", "session_id", "occurred_at"),
    )

    # SQLite chỉ tự tăng với INTEGER PRIMARY KEY
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"))
    seq: Mapped[int]
    occurred_at: Mapped[datetime]
    kind: Mapped[str] = mapped_column(String(40))
    step_id: Mapped[str | None] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)


class SkillState(Base):
    __tablename__ = "skill_states"
    __table_args__ = (enum_check("support_state", SupportState),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill: Mapped[str] = mapped_column(String(40), primary_key=True)
    support_state: Mapped[str] = mapped_column(String(16), default=SupportState.DEVELOPING)
    recent_scores: Mapped[list[Any]] = mapped_column(default=list)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SurveyResponse(CreatedAtMixin, Base):
    __tablename__ = "survey_responses"
    __table_args__ = (enum_check("instrument", Instrument),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE")
    )
    instrument: Mapped[str] = mapped_column(String(16))
    answers: Mapped[Any] = mapped_column(JsonType)  # paas: số; sus: 10 số; satisfaction: đối tượng
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
