"""Bài tập: tạo (kèm kiểm file đề/đáp án), xem, sửa, xóa (FR-W04, FR-W05)."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.orm import Session

from tutor_backend.core.errors import ConflictError, InvalidError, NotFoundError
from tutor_backend.models import Exercise, PracticeSession, ScriptVersion, Textbook, User, exercise_textbooks
from tutor_backend.models.enums import ScriptStatus
from tutor_backend.schemas.exercise import ExerciseOut, ExerciseUpdate
from tutor_backend.schemas.script import ScriptVersionSummary
from tutor_backend.services.exercise_files import check_exercise_files
from tutor_backend.services.storage import FileStore
from tutor_backend.services.uploads import require_type

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExerciseFiles:
    starter: bytes
    solution: bytes
    prompt: bytes | None = None
    prompt_name: str | None = None


@dataclass(frozen=True)
class ExerciseFields:
    code: str
    title: str
    sheet_name: str
    prompt_text: str | None = None
    textbook_ids: tuple[uuid.UUID, ...] = ()


def get_exercise(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    return exercise


def _textbook_ids(db: Session, exercise_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(exercise_textbooks.c.textbook_id).where(exercise_textbooks.c.exercise_id == exercise_id)
        )
    )


def _set_textbooks(
    db: Session, exercise_id: uuid.UUID, textbook_ids: tuple[uuid.UUID, ...] | list[uuid.UUID]
) -> None:
    ids = list(dict.fromkeys(textbook_ids))
    found = set(db.scalars(select(Textbook.id).where(Textbook.id.in_(ids)))) if ids else set()
    missing = [str(i) for i in ids if i not in found]
    if missing:
        raise InvalidError(
            "Có giáo trình không tồn tại",
            code="textbook_not_found",
            errors=[{"path": "/textbook_ids", "message": i} for i in missing],
        )
    db.execute(delete(exercise_textbooks).where(exercise_textbooks.c.exercise_id == exercise_id))
    if ids:
        db.execute(insert(exercise_textbooks), [{"exercise_id": exercise_id, "textbook_id": i} for i in ids])


def _summary(version: ScriptVersion | None) -> ScriptVersionSummary | None:
    return ScriptVersionSummary.model_validate(version) if version is not None else None


def exercise_out(db: Session, exercise: Exercise) -> ExerciseOut:
    latest = db.scalars(
        select(ScriptVersion)
        .where(ScriptVersion.exercise_id == exercise.id)
        .order_by(ScriptVersion.revision.desc())
    ).first()
    published = db.scalars(
        select(ScriptVersion).where(
            ScriptVersion.exercise_id == exercise.id, ScriptVersion.status == ScriptStatus.PUBLISHED
        )
    ).first()
    return ExerciseOut.model_validate(exercise).model_copy(
        update={
            "textbook_ids": _textbook_ids(db, exercise.id),
            "latest_version": _summary(latest),
            "published_version": _summary(published),
        }
    )


def create_exercise(
    db: Session, store: FileStore, fields: ExerciseFields, files: ExerciseFiles, user: User
) -> Exercise:
    if db.scalar(select(Exercise.id).where(Exercise.code == fields.code)) is not None:
        raise ConflictError(f"Mã bài {fields.code} đã tồn tại", code="exercise_code_taken")
    require_type(files.starter, {"xlsx"}, "starter_file")
    require_type(files.solution, {"xlsx"}, "solution_file")
    exercise_id = uuid.uuid4()
    folder = f"exercises/{exercise_id}"
    try:
        starter = store.save(f"{folder}/de.xlsx", files.starter)
        solution = store.save(f"{folder}/dap-an.xlsx", files.solution)
        warnings = check_exercise_files(store.path(starter), store.path(solution), fields.sheet_name)
        prompt = None
        if files.prompt is not None:
            suffix = (files.prompt_name or "").rsplit(".", 1)[-1].lower()[:8] or "bin"
            prompt = store.save(f"{folder}/de-bai.{suffix}", files.prompt)
        exercise = Exercise(
            id=exercise_id,
            code=fields.code,
            title=fields.title.strip(),
            sheet_name=fields.sheet_name,
            starter_file_path=starter,
            solution_file_path=solution,
            prompt_file_path=prompt,
            prompt_text=(fields.prompt_text or "").strip() or None,
            warnings=warnings,
            created_by=user.id,
        )
        db.add(exercise)
        db.flush()
        _set_textbooks(db, exercise_id, fields.textbook_ids)
        db.commit()
    except Exception:
        db.rollback()
        store.discard_dir(folder)  # không để lại file của bài tạo hỏng
        raise
    logger.info("Tạo bài %s (%s), %d cảnh báo", exercise.code, exercise_id, len(warnings))
    return exercise


def list_exercises(db: Session, q: str | None) -> list[ExerciseOut]:
    query = select(Exercise).order_by(Exercise.code)
    if q:
        pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(func.lower(Exercise.code).like(pattern), func.lower(Exercise.title).like(pattern))
        )
    return [exercise_out(db, e) for e in db.scalars(query)]


def update_exercise(db: Session, exercise_id: uuid.UUID, data: ExerciseUpdate) -> ExerciseOut:
    exercise = get_exercise(db, exercise_id)
    if data.title is not None:
        exercise.title = data.title.strip()
    if data.prompt_text is not None:
        exercise.prompt_text = data.prompt_text.strip() or None
    if data.textbook_ids is not None:
        _set_textbooks(db, exercise_id, data.textbook_ids)
    db.commit()
    return exercise_out(db, exercise)


def delete_exercise(db: Session, store: FileStore, exercise_id: uuid.UUID) -> None:
    exercise = get_exercise(db, exercise_id)
    sessions = db.scalar(select(func.count()).where(PracticeSession.exercise_id == exercise_id)) or 0
    if sessions:
        raise ConflictError(f"Bài đã có {sessions} phiên thực hành, không xóa được", code="exercise_in_use")
    db.delete(exercise)
    db.commit()
    store.delete_dir(f"exercises/{exercise_id}")
