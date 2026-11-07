"""Revision kịch bản: tạo bản mới (không sửa đè), xem (csdl.md 2.3). Vòng đời duyệt/phát hành ở T5.6."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tutor_backend.core.errors import NotFoundError
from tutor_backend.models import Exercise, ScriptVersion
from tutor_backend.models.enums import ScriptOrigin, ScriptStatus


def next_revision(db: Session, exercise_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.max(ScriptVersion.revision)).where(ScriptVersion.exercise_id == exercise_id)
    )
    return (current or 0) + 1


def create_version(
    db: Session,
    exercise: Exercise,
    content: dict[str, Any],
    *,
    origin: ScriptOrigin,
    created_by: uuid.UUID | None,
    report: dict[str, Any] | None = None,
    parent_version_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
) -> ScriptVersion:
    """Lưu một revision nháp mới; `revision` trong nội dung khớp số revision trong CSDL."""
    revision = next_revision(db, exercise.id)
    content = {**content, "revision": revision}
    version = ScriptVersion(
        exercise_id=exercise.id,
        revision=revision,
        schema_version=str(content.get("schema_version", "1")),
        status=ScriptStatus.DRAFT,
        origin=origin,
        content=content,
        self_check_report=report,
        parent_version_id=parent_version_id,
        job_id=job_id,
        created_by=created_by,
    )
    db.add(version)
    db.flush()
    return version


def get_version(db: Session, version_id: uuid.UUID) -> ScriptVersion:
    version = db.get(ScriptVersion, version_id, populate_existing=True)
    if version is None:
        raise NotFoundError("Không tìm thấy revision kịch bản", code="script_not_found")
    return version


def list_versions(db: Session, exercise_id: uuid.UUID) -> list[ScriptVersion]:
    query = (
        select(ScriptVersion)
        .where(ScriptVersion.exercise_id == exercise_id)
        .order_by(ScriptVersion.revision.desc())
    )
    return list(db.scalars(query))
