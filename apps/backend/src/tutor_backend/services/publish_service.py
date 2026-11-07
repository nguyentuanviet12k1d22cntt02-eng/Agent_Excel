"""Phát hành kịch bản (FR-W11, T5.6): nhúng mã bài vào file đề, bản phát hành cũ chuyển sang lưu trữ.

Mỗi bài tối đa một bản `published` (chỉ mục duy nhất có điều kiện trong CSDL). Học viên mở file đề đã nhúng
mã bài thì Desktop tự nhận ra bài (kien-truc.md A5).
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from excel_core.package_props import set_custom_properties
from excel_core.readers import EXERCISE_ID_PROPERTY
from tutor_backend.core.errors import NotFoundError
from tutor_backend.db.base import utcnow
from tutor_backend.models import ClassExercise, ClassMember, Exercise, ScriptVersion, User
from tutor_backend.models.enums import Role, ScriptStatus
from tutor_backend.services.script_service import transition
from tutor_backend.services.storage import FileStore

logger = logging.getLogger(__name__)

REVISION_PROPERTY = "tutor_script_revision"


def published_version(db: Session, exercise_id: uuid.UUID) -> ScriptVersion | None:
    query = select(ScriptVersion).where(
        ScriptVersion.exercise_id == exercise_id, ScriptVersion.status == ScriptStatus.PUBLISHED
    )
    return db.scalars(query).first()


def publish(db: Session, store: FileStore, version: ScriptVersion) -> ScriptVersion:
    target = transition(version, "publish")
    exercise = db.get(Exercise, version.exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    relative = f"exercises/{exercise.id}/phat-hanh-r{version.revision}.xlsx"
    set_custom_properties(
        store.path(exercise.starter_file_path),
        store.path(relative),
        {EXERCISE_ID_PROPERTY: exercise.code, REVISION_PROPERTY: str(version.revision)},
    )
    previous = published_version(db, exercise.id)
    if previous is not None:
        previous.status = ScriptStatus.ARCHIVED
        db.flush()  # lưu trữ bản cũ trước, để chỉ mục "một bản published" không báo trùng
    version.status, version.published_at, version.published_file_path = target, utcnow(), relative
    db.commit()
    logger.info("Phát hành %s revision %d", exercise.code, version.revision)
    return version


def _student_assigned(db: Session, student: User, exercise_id: uuid.UUID) -> bool:
    query = select(
        exists().where(
            ClassExercise.exercise_id == exercise_id,
            ClassExercise.class_id == ClassMember.class_id,
            ClassMember.student_id == student.id,
        )
    )
    return bool(db.scalar(query))


def starter_file(db: Session, store: FileStore, exercise_id: uuid.UUID, user: User) -> tuple[Path, str]:
    """File đề đã nhúng mã bài (chỉ có khi đã phát hành). Học viên chỉ tải được bài được giao cho lớp mình."""
    exercise = db.get(Exercise, exercise_id)
    version = published_version(db, exercise_id) if exercise is not None else None
    allowed = user.role != Role.STUDENT or (exercise is not None and _student_assigned(db, user, exercise_id))
    if exercise is None or version is None or version.published_file_path is None or not allowed:
        raise NotFoundError("Bài chưa phát hành hoặc không được giao cho bạn", code="starter_file_not_found")
    return store.path(version.published_file_path), f"{exercise.code}.xlsx"
