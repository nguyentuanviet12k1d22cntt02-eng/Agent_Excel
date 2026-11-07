"""Sinh kịch bản bằng AI: yêu cầu sinh (chạy nền), xem trạng thái job."""

import uuid

from fastapi import APIRouter, Request, status

from tutor_backend.api.deps import AppSettings, DbSession, Jobs, SessionFactory, Staff, Store
from tutor_backend.schemas.generation import GenerationJobOut, GenerationRequest
from tutor_backend.services import generation_service

router = APIRouter(tags=["scripts"])


@router.post(
    "/exercises/{exercise_id}/generation-jobs",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Yêu cầu AI sinh kịch bản (chạy nền)",
)
def request_generation(
    exercise_id: uuid.UUID,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    jobs: Jobs,
    store: Store,
    session_factory: SessionFactory,
    user: Staff,
    body: GenerationRequest | None = None,
) -> GenerationJobOut:
    job = generation_service.request_generation(db, exercise_id, user, body or GenerationRequest(), settings)
    llm_factory = request.app.state.llm_factory
    jobs.submit(generation_service.run_generation_job, session_factory, store, settings, llm_factory, job.id)
    return generation_service.job_out(db, generation_service.get_job(db, job.id))


@router.get("/generation-jobs/{job_id}", summary="Trạng thái job sinh kịch bản (Web hỏi định kỳ)")
def get_job(job_id: uuid.UUID, db: DbSession, _: Staff) -> GenerationJobOut:
    return generation_service.job_out(db, generation_service.get_job(db, job_id))
