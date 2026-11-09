"""Kịch bản: revision, tự kiểm, duyệt, phát hành, tải file đề đã nhúng mã bài (T5.6)."""

import uuid
from typing import Any

from fastapi import APIRouter, UploadFile, status
from fastapi.responses import FileResponse

from tutor_backend.api.deps import AnyRole, AppSettings, DbSession, Staff, Store
from tutor_backend.schemas.script import (
    PreviewBundle,
    RejectRequest,
    ScriptCreate,
    ScriptVersionOut,
    ScriptVersionSummary,
)
from tutor_backend.services import publish_service, script_service
from tutor_backend.services.exercise_service import get_exercise
from tutor_backend.services.uploads import read_limited

router = APIRouter(tags=["scripts"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/exercises/{exercise_id}/scripts", summary="Các revision kịch bản của bài (không kèm nội dung)")
def list_scripts(exercise_id: uuid.UUID, db: DbSession, _: Staff) -> list[ScriptVersionSummary]:
    get_exercise(db, exercise_id)
    return [ScriptVersionSummary.model_validate(v) for v in script_service.list_versions(db, exercise_id)]


@router.post(
    "/exercises/{exercise_id}/scripts",
    status_code=status.HTTP_201_CREATED,
    summary="Lưu một revision mới (giảng viên tạo hoặc sửa)",
)
def save_script(
    exercise_id: uuid.UUID, body: ScriptCreate, db: DbSession, store: Store, user: Staff
) -> ScriptVersionOut:
    exercise = get_exercise(db, exercise_id)
    version = script_service.save_revision(db, store, exercise, body.content, user, body.parent_version_id)
    return ScriptVersionOut.model_validate(version)


@router.get("/scripts/{version_id}", summary="Một revision, kèm nội dung và báo cáo tự kiểm")
def get_script(version_id: uuid.UUID, db: DbSession, _: Staff) -> ScriptVersionOut:
    return ScriptVersionOut.model_validate(script_service.get_version(db, version_id))


@router.get(
    "/scripts/{version_id}/preview-bundle",
    summary="Kịch bản kèm snapshot tham chiếu để chạy thử trên Desktop (mọi trạng thái, kể cả nháp)",
)
def preview_bundle(version_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> PreviewBundle:
    return script_service.preview_bundle(db, store, script_service.get_version(db, version_id))


@router.get(
    "/exercises/{exercise_id}/original-starter-file",
    summary="Tải file đề gốc (chưa nhúng mã bài) để giảng viên chạy thử",
    response_class=FileResponse,
)
def original_starter_file(exercise_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> FileResponse:
    exercise = get_exercise(db, exercise_id)
    return FileResponse(
        store.path(exercise.starter_file_path),
        media_type=XLSX_MEDIA_TYPE,
        filename=f"{exercise.code}-de.xlsx",
    )


@router.post("/scripts/{version_id}/self-check", summary="Chạy lại tự kiểm tầng 3 trên file đề và đáp án")
def self_check(version_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> dict[str, Any]:
    return script_service.refresh_report(db, store, script_service.get_version(db, version_id))


@router.post(
    "/scripts/{version_id}/try-out",
    summary="Chấm thử một file bài làm theo revision này, như Desktop sẽ chấm",
)
def try_out(
    version_id: uuid.UUID, file: UploadFile, db: DbSession, store: Store, settings: AppSettings, _: Staff
) -> dict[str, Any]:
    data = read_limited(file.file, settings.max_upload_bytes, "file")
    return script_service.try_out(db, store, script_service.get_version(db, version_id), data)


@router.post("/scripts/{version_id}/submit", summary="Gửi duyệt (draft → pending_review)")
def submit(version_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> ScriptVersionSummary:
    version = script_service.submit(db, store, script_service.get_version(db, version_id))
    return ScriptVersionSummary.model_validate(version)


@router.post("/scripts/{version_id}/approve", summary="Duyệt (pending_review → approved)")
def approve(version_id: uuid.UUID, db: DbSession, user: Staff) -> ScriptVersionSummary:
    version = script_service.review(db, script_service.get_version(db, version_id), user, approve=True)
    return ScriptVersionSummary.model_validate(version)


@router.post("/scripts/{version_id}/reject", summary="Từ chối kèm góp ý (pending_review → draft)")
def reject(version_id: uuid.UUID, body: RejectRequest, db: DbSession, user: Staff) -> ScriptVersionSummary:
    version = script_service.get_version(db, version_id)
    return ScriptVersionSummary.model_validate(
        script_service.review(db, version, user, approve=False, note=body.note)
    )


@router.post(
    "/scripts/{version_id}/publish",
    summary="Phát hành (approved → published); nhúng mã bài vào file đề; bản phát hành cũ → archived",
)
def publish(version_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> ScriptVersionSummary:
    version = publish_service.publish(db, store, script_service.get_version(db, version_id))
    return ScriptVersionSummary.model_validate(version)


@router.get(
    "/exercises/{exercise_id}/starter-file",
    summary="Tải file đề ĐÃ NHÚNG mã bài (chỉ có khi đã phát hành) để phát cho học viên",
    response_class=FileResponse,
)
def starter_file(exercise_id: uuid.UUID, db: DbSession, store: Store, user: AnyRole) -> FileResponse:
    path, filename = publish_service.starter_file(db, store, exercise_id, user)
    return FileResponse(path, media_type=XLSX_MEDIA_TYPE, filename=filename)
