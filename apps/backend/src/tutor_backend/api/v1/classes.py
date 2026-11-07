"""/classes: lớp học, học viên và nhóm thực nghiệm, giao bài."""

import uuid

from fastapi import APIRouter, Response, status

from tutor_backend.api.deps import Admin, DbSession, Staff
from tutor_backend.schemas.class_ import ClassCreate, ClassExerciseIn, ClassOut, MemberIn
from tutor_backend.services import class_service

router = APIRouter(prefix="/classes", tags=["accounts"])


@router.get("", summary="Danh sách lớp (giảng viên chỉ thấy lớp mình)")
def list_classes(db: DbSession, user: Staff) -> list[ClassOut]:
    return class_service.list_classes(db, user)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Tạo lớp")
def create_class(body: ClassCreate, db: DbSession, _: Admin) -> ClassOut:
    return class_service.create_class(db, body)


@router.put(
    "/{class_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đặt danh sách học viên của lớp và nhóm thực nghiệm (thay toàn bộ)",
)
def replace_members(class_id: uuid.UUID, body: list[MemberIn], db: DbSession, _: Admin) -> Response:
    class_service.replace_members(db, class_id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{class_id}/exercises", status_code=status.HTTP_204_NO_CONTENT, summary="Giao bài cho lớp")
def assign_exercise(class_id: uuid.UUID, body: ClassExerciseIn, db: DbSession, user: Staff) -> Response:
    class_service.assign_exercise(db, class_id, body, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
