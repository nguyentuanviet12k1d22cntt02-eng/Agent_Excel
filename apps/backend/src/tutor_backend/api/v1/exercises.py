"""/exercises: bài tập (file đề, file đáp án cùng bố cục, đề bài, giáo trình liên quan)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Query, Response, UploadFile, status

from tutor_backend.api.deps import AppSettings, DbSession, Staff, Store
from tutor_backend.schemas.exercise import ExerciseOut, ExerciseUpdate
from tutor_backend.services import exercise_service
from tutor_backend.services.exercise_service import ExerciseFields, ExerciseFiles
from tutor_backend.services.uploads import read_limited

router = APIRouter(prefix="/exercises", tags=["materials"])

CODE_PATTERN = r"^[a-z0-9][a-z0-9-]{2,63}$"


@router.get("", summary="Danh sách bài tập")
def list_exercises(
    db: DbSession, _: Staff, q: Annotated[str | None, Query(description="Tìm theo tên hoặc mã bài")] = None
) -> list[ExerciseOut]:
    return exercise_service.list_exercises(db, q)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Tạo bài tập (file đề, file đáp án cùng bố cục, đề bài, giáo trình liên quan)",
)
def create_exercise(
    db: DbSession,
    store: Store,
    settings: AppSettings,
    user: Staff,
    code: Annotated[str, Form(pattern=CODE_PATTERN)],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    sheet_name: Annotated[str, Form(min_length=1, max_length=31)],
    starter_file: UploadFile,
    solution_file: UploadFile,
    prompt_file: UploadFile | None = None,
    prompt_text: Annotated[str | None, Form(max_length=20000)] = None,
    textbook_ids: Annotated[list[uuid.UUID] | None, Form()] = None,
) -> ExerciseOut:
    limit = settings.max_upload_bytes
    files = ExerciseFiles(
        starter=read_limited(starter_file.file, limit, "starter_file"),
        solution=read_limited(solution_file.file, limit, "solution_file"),
        prompt=read_limited(prompt_file.file, limit, "prompt_file") if prompt_file else None,
        prompt_name=prompt_file.filename if prompt_file else None,
    )
    fields = ExerciseFields(code, title, sheet_name, prompt_text, tuple(textbook_ids or ()))
    exercise = exercise_service.create_exercise(db, store, fields, files, user)
    return exercise_service.exercise_out(db, exercise)


@router.get("/{exercise_id}", summary="Chi tiết bài tập (kèm revision mới nhất và bản đang phát hành)")
def get_exercise(exercise_id: uuid.UUID, db: DbSession, _: Staff) -> ExerciseOut:
    return exercise_service.exercise_out(db, exercise_service.get_exercise(db, exercise_id))


@router.patch("/{exercise_id}", summary="Sửa thông tin bài tập (không đổi được mã bài)")
def update_exercise(exercise_id: uuid.UUID, body: ExerciseUpdate, db: DbSession, _: Staff) -> ExerciseOut:
    return exercise_service.update_exercise(db, exercise_id, body)


@router.delete(
    "/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa bài tập (khi chưa có phiên)"
)
def delete_exercise(exercise_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> Response:
    exercise_service.delete_exercise(db, store, exercise_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
