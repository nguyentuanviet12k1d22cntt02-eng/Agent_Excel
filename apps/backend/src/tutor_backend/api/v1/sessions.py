"""/sessions, /surveys: Desktop gửi phiên thực hành, tiến độ bước, nhật ký theo lô, phiếu Paas/SUS."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from tutor_backend.api.deps import DbSession, Student, StudentOrTeacher
from tutor_backend.schemas.desktop import (
    EventBatch,
    EventBatchResult,
    SessionUpsert,
    StepProgressIn,
    SurveyIn,
)
from tutor_backend.services import progress_service

router = APIRouter(tags=["desktop"])

STEP_PATTERN = r"^[a-z][a-z0-9_]{0,39}$"


@router.put(
    "/sessions/{session_id}",
    summary="Tạo hoặc cập nhật phiên thực hành (id do Desktop sinh, gọi lại nhiều lần không sao)",
    responses={201: {"description": "Đã tạo"}},
)
def upsert_session(session_id: uuid.UUID, body: SessionUpsert, db: DbSession, student: Student) -> Response:
    created = progress_service.upsert_session(db, session_id, student, body)
    return Response(status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@router.put(
    "/sessions/{session_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ghi kết quả một bước (Backend cập nhật mức kỹ năng khi bước xong)",
)
def record_step(
    session_id: uuid.UUID,
    step_id: Annotated[str, Path(pattern=STEP_PATTERN)],
    body: StepProgressIn,
    db: DbSession,
    student: Student,
) -> Response:
    progress_service.record_step(db, session_id, step_id, student, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/events",
    summary="Gửi nhật ký theo lô; sự kiện trùng seq bị bỏ qua (gửi lại an toàn)",
)
def record_events(
    session_id: uuid.UUID, body: EventBatch, db: DbSession, student: Student
) -> EventBatchResult:
    return progress_service.record_events(db, session_id, student, body.events)


@router.post("/surveys", status_code=status.HTTP_201_CREATED, summary="Gửi phiếu Paas / SUS / hài lòng")
def record_survey(body: SurveyIn, db: DbSession, user: StudentOrTeacher) -> Response:
    progress_service.record_survey(db, user, body)
    return Response(status_code=status.HTTP_201_CREATED)
