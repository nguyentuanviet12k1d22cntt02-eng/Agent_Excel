"""Revision kịch bản và vòng đời duyệt (csdl.md 2.3, luoc-do-kich-ban.md mục 4.2, T5.6).

- Mỗi lần lưu là một revision mới, không sửa đè; nội dung bản đã duyệt/phát hành không bao giờ đổi.
- Trạng thái: draft → pending_review → approved → published → archived; từ chối: pending_review → draft.
- NFR-13: chỉ gửi duyệt được khi kịch bản qua cả 3 tầng kiểm (lược đồ, tham chiếu chéo, tự kiểm trên file).
"""

import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from excel_core.script import self_check_files, validate_script
from excel_core.script.grade import grade_files
from tutor_backend.core.errors import ConflictError, InvalidError, NotFoundError
from tutor_backend.db.base import utcnow
from tutor_backend.models import Exercise, ScriptVersion, User
from tutor_backend.models.enums import ScriptOrigin, ScriptStatus
from tutor_backend.schemas.script import PreviewBundle
from tutor_backend.services.storage import FileStore
from tutor_backend.services.uploads import require_type

TRANSITIONS: dict[str, tuple[frozenset[ScriptStatus], ScriptStatus]] = {
    "submit": (frozenset({ScriptStatus.DRAFT}), ScriptStatus.PENDING_REVIEW),
    "approve": (frozenset({ScriptStatus.PENDING_REVIEW}), ScriptStatus.APPROVED),
    "reject": (frozenset({ScriptStatus.PENDING_REVIEW}), ScriptStatus.DRAFT),
    "publish": (frozenset({ScriptStatus.APPROVED}), ScriptStatus.PUBLISHED),
}
_ACTION_NAMES = {"submit": "gửi duyệt", "approve": "duyệt", "reject": "từ chối", "publish": "phát hành"}


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


def full_report(content: dict[str, Any], starter: Path, solution: Path) -> tuple[dict[str, Any], list[str]]:
    """Báo cáo 3 tầng (SelfCheckReport trong openapi.yaml) và danh sách lỗi chặn gửi duyệt."""
    validation = validate_script(content)
    report: dict[str, Any] = {
        "schema_ok": validation.schema_ok,
        "cross_reference_errors": [str(i) for i in validation.cross_reference_issues],
    }
    blocking = [str(i) for i in validation.schema_issues + validation.cross_reference_issues]
    if validation.schema_ok:
        self_check = self_check_files(content, starter, solution)
        report |= self_check.to_dict()
        blocking += list(self_check.errors)
    return report, blocking


def _exercise_files(store: FileStore, exercise: Exercise) -> tuple[Path, Path]:
    return store.path(exercise.starter_file_path), store.path(exercise.solution_file_path)


def save_revision(
    db: Session,
    store: FileStore,
    exercise: Exercise,
    content: dict[str, Any],
    user: User,
    parent_version_id: uuid.UUID | None,
) -> ScriptVersion:
    """Giảng viên lưu bản mới (tạo hoặc sửa). Kiểm tầng 1–2 trước khi lưu; tầng 3 lưu vào báo cáo."""
    if content.get("exercise", {}).get("id") != exercise.code:
        errors = [{"path": "/exercise/id", "message": f"phải là mã bài {exercise.code}"}]
        raise InvalidError("Kịch bản không thuộc bài tập này", code="exercise_mismatch", errors=errors)
    validation = validate_script(content)
    if not validation.ok:
        errors = [
            {"path": i.path, "message": i.message}
            for i in validation.schema_issues + validation.cross_reference_issues
        ]
        raise InvalidError("Kịch bản không hợp lệ", code="script_invalid", errors=errors)
    origin = ScriptOrigin.TEACHER
    if parent_version_id is not None:
        parent = get_version(db, parent_version_id)
        if parent.exercise_id != exercise.id:
            raise InvalidError("Revision gốc thuộc bài khác", code="parent_mismatch")
        if parent.origin in (ScriptOrigin.AI, ScriptOrigin.AI_EDITED):
            origin = ScriptOrigin.AI_EDITED  # để so được phần AI sinh với phần giảng viên sửa (T5.8)
    report, _ = full_report(content, *_exercise_files(store, exercise))
    version = create_version(
        db,
        exercise,
        content,
        origin=origin,
        created_by=user.id,
        report=report,
        parent_version_id=parent_version_id,
    )
    db.commit()
    return version


def try_out(db: Session, store: FileStore, version: ScriptVersion, data: bytes) -> dict[str, Any]:
    """Chấm thử một file bài làm theo revision này, như Desktop sẽ chấm (thử trước khi phát hành)."""
    require_type(data, {"xlsx"}, "file")
    exercise = db.get(Exercise, version.exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    with tempfile.TemporaryDirectory(prefix="tutor-try-") as folder:
        current = Path(folder) / "bai-lam.xlsx"
        current.write_bytes(data)
        try:
            report = grade_files(version.content, current, *_exercise_files(store, exercise))
        except (InvalidFileException, zipfile.BadZipFile, KeyError, ValueError) as exc:
            raise InvalidError(
                "Không đọc được file bài làm",
                code="file_invalid",
                errors=[{"path": "/file", "message": "không phải file .xlsx hợp lệ"}],
            ) from exc
    return report.to_dict()


def preview_bundle(db: Session, store: FileStore, version: ScriptVersion) -> PreviewBundle:
    """Kịch bản, snapshot tham chiếu cho chế độ chạy thử của Desktop (như gói học viên nhận khi phát hành)."""
    from tutor_backend.services.desktop_service import reference_snapshots  # noqa: PLC0415 — tránh vòng import

    exercise = db.get(Exercise, version.exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    return PreviewBundle(
        version_id=version.id,
        exercise_id=exercise.id,
        exercise_code=exercise.code,
        exercise_title=exercise.title,
        revision=version.revision,
        status=ScriptStatus(version.status),
        content=version.content,
        references=reference_snapshots(store, exercise, version),
    )


def refresh_report(db: Session, store: FileStore, version: ScriptVersion) -> dict[str, Any]:
    exercise = db.get(Exercise, version.exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    report, _ = full_report(version.content, *_exercise_files(store, exercise))
    version.self_check_report = report
    db.commit()
    return report


def transition(version: ScriptVersion, action: str) -> ScriptStatus:
    allowed, target = TRANSITIONS[action]
    if version.status not in allowed:
        raise ConflictError(
            f"Không {_ACTION_NAMES[action]} được bản đang ở trạng thái {version.status}",
            code="invalid_transition",
        )
    return target


def submit(db: Session, store: FileStore, version: ScriptVersion) -> ScriptVersion:
    target = transition(version, "submit")
    exercise = db.get(Exercise, version.exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    report, blocking = full_report(version.content, *_exercise_files(store, exercise))
    version.self_check_report = report
    if blocking:
        db.commit()
        errors = [{"path": "/self_check", "message": message} for message in blocking]
        raise ConflictError(
            "Kịch bản chưa qua tự kiểm, sửa rồi gửi duyệt lại", code="self_check_failed", errors=errors
        )
    version.status = target
    db.commit()
    return version


def review(
    db: Session, version: ScriptVersion, user: User, *, approve: bool, note: str | None = None
) -> ScriptVersion:
    version.status = transition(version, "approve" if approve else "reject")
    version.reviewed_by, version.reviewed_at, version.review_note = user.id, utcnow(), note
    db.commit()
    db.expire(version, ["reviewer"])  # quan hệ chỉ đọc: nạp lại theo người duyệt mới
    return version
