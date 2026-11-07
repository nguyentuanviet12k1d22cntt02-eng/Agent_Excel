"""Phục vụ Desktop: bài được giao, kịch bản đang phát hành kèm snapshot tham chiếu (FR-D02, FR-D03, T5.7).

Desktop không có file đáp án, nhưng điều kiện `expected: solution` và `data_unchanged` cần giá trị của file
đáp án và file đề. Backend đọc **đúng các vùng kịch bản cần** (`excel_core.checks.reference_requests`) rồi gửi
kèm dạng JSON (snapshot.md mục 7). Bản phát hành không đổi nội dung, nên kết quả được nhớ theo version_id.
"""

import uuid
from collections import OrderedDict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from excel_core.checks import reference_requests
from excel_core.readers import read_workbook
from excel_core.snapshot import snapshot_to_dict
from tutor_backend.core.errors import NotFoundError
from tutor_backend.models import ClassExercise, ClassMember, Exercise, ScriptVersion, User
from tutor_backend.models.enums import ScriptStatus, SessionMode, StudyGroup
from tutor_backend.schemas.desktop import Assignment, DesktopScript
from tutor_backend.services.storage import FileStore

REFERENCE_CACHE_SIZE = 32
_reference_cache: OrderedDict[uuid.UUID, dict[str, Any]] = OrderedDict()


def session_mode(groups: list[str]) -> SessionMode:
    """Học viên ở nhiều lớp: chỉ cần một lớp thuộc nhóm thực nghiệm là có gia sư (FR-D15)."""
    return SessionMode.TUTOR if any(g == StudyGroup.EXPERIMENTAL for g in groups) else SessionMode.CONTROL


def _memberships(
    db: Session, student: User, exercise_id: uuid.UUID | None = None
) -> list[tuple[ClassExercise, str]]:
    """(bài giao cho lớp, nhóm thực nghiệm của học viên trong lớp đó)."""
    query = (
        select(ClassExercise, ClassMember.study_group)
        .join(ClassMember, ClassMember.class_id == ClassExercise.class_id)
        .where(ClassMember.student_id == student.id)
    )
    if exercise_id is not None:
        query = query.where(ClassExercise.exercise_id == exercise_id)
    return [(row[0], row[1]) for row in db.execute(query)]


def _published(db: Session, exercise_id: uuid.UUID) -> ScriptVersion | None:
    query = select(ScriptVersion).where(
        ScriptVersion.exercise_id == exercise_id, ScriptVersion.status == ScriptStatus.PUBLISHED
    )
    return db.scalars(query).first()


def assignments(db: Session, student: User) -> list[Assignment]:
    """Bài đã phát hành được giao cho lớp của học viên; bài giao ở nhiều lớp thì lấy hạn nộp sớm nhất."""
    grouped: dict[uuid.UUID, list[tuple[ClassExercise, str]]] = {}
    for assigned, group in _memberships(db, student):
        grouped.setdefault(assigned.exercise_id, []).append((assigned, group))
    result = []
    for exercise_id, items in grouped.items():
        version, exercise = _published(db, exercise_id), db.get(Exercise, exercise_id)
        if version is None or exercise is None:
            continue
        due_dates = [assigned.due_at for assigned, _ in items if assigned.due_at is not None]
        result.append(
            Assignment(
                exercise_code=exercise.code,
                title=exercise.title,
                revision=version.revision,
                due_at=min(due_dates) if due_dates else None,
                starter_file_url=f"/api/v1/exercises/{exercise.id}/starter-file",
                mode=session_mode([group for _, group in items]),
            )
        )
    return sorted(result, key=lambda a: a.exercise_code)


def reference_snapshots(store: FileStore, exercise: Exercise, version: ScriptVersion) -> dict[str, Any]:
    if version.id in _reference_cache:
        _reference_cache.move_to_end(version.id)
        return _reference_cache[version.id]
    content = version.content
    checks = [*content.get("global_checks", []), *(c for step in content["steps"] for c in step["checks"])]
    files = {"starter": exercise.starter_file_path, "solution": exercise.solution_file_path}
    references = {
        source: snapshot_to_dict(read_workbook(store.path(files[source]), request))
        for source, request in reference_requests(checks, content["exercise"]["sheet"]).items()
    }
    _reference_cache[version.id] = references
    if len(_reference_cache) > REFERENCE_CACHE_SIZE:
        _reference_cache.popitem(last=False)
    return references


def published_script(db: Session, store: FileStore, student: User, exercise_code: str) -> DesktopScript:
    """Kịch bản đang phát hành của bài (theo mã bài đọc từ file đề); học viên phải được giao bài này."""
    exercise = db.scalar(select(Exercise).where(Exercise.code == exercise_code))
    version = _published(db, exercise.id) if exercise is not None else None
    memberships = _memberships(db, student, exercise.id) if exercise is not None else []
    if exercise is None or version is None or not memberships:
        raise NotFoundError("Bài chưa phát hành hoặc không được giao cho bạn", code="script_not_found")
    return DesktopScript(
        version_id=version.id,
        mode=session_mode([group for _, group in memberships]),
        content=version.content,
        references=reference_snapshots(store, exercise, version),
    )
