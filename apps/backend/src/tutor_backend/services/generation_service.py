"""Sinh kịch bản bằng AI chạy nền (FR-W06): xếp hàng job, chạy tác tử, lưu revision nháp `origin=ai`.

Trạng thái job ghi vào `generation_jobs` (stage: diff → rag → llm → self_check) để Web hỏi định kỳ.
Số lần thử, token, thời gian là dữ liệu cho đánh giá kỹ thuật (đề cương 5.2, T5.8).
"""

import logging
import time
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tutor_backend.ai import rag
from tutor_backend.ai.exercise_analysis import KIND_NAMES, ExerciseAnalysis, analyze_exercise
from tutor_backend.ai.llm_client import LLMClient, LLMError, OpenAICompatibleClient
from tutor_backend.ai.script_agent import generate_script
from tutor_backend.ai.script_builder import ExerciseInfo
from tutor_backend.core.config import Settings
from tutor_backend.core.errors import ConflictError, NotFoundError
from tutor_backend.db.base import utcnow
from tutor_backend.models import Exercise, GenerationJob, ScriptVersion, User, exercise_textbooks
from tutor_backend.models.enums import JobStatus, ScriptOrigin
from tutor_backend.schemas.generation import GenerationJobOut, GenerationRequest
from tutor_backend.services import script_service
from tutor_backend.services.exercise_service import get_exercise
from tutor_backend.services.storage import FileStore

logger = logging.getLogger(__name__)

type LLMFactory = Callable[[Settings, str], LLMClient]

RAG_PASSAGES = 5
MAX_ERROR_REASONS = 3
MAX_ERROR_CHARS = 1000  # lỗi hiện trên Web: đủ đọc, không chép cả đầu ra của AI
JOB_HISTORY_LIMIT = 20
MAX_QUERY_PROMPT_CHARS = 400


def default_llm_factory(settings: Settings, model: str) -> LLMClient:
    if settings.llm_api_key is None:
        raise LLMError("Chưa cấu hình LLM_API_KEY trong apps/backend/.env")
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=model,
        timeout=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
    )


def job_out(db: Session, job: GenerationJob) -> GenerationJobOut:
    version_id = db.scalar(select(ScriptVersion.id).where(ScriptVersion.job_id == job.id))
    return GenerationJobOut.model_validate(job).model_copy(update={"result_version_id": version_id})


def list_jobs(db: Session, exercise_id: uuid.UUID) -> list[GenerationJobOut]:
    """Các lần sinh của bài, mới nhất trước: Web mở lại trang vẫn thấy job đang chạy và lịch sử sinh."""
    get_exercise(db, exercise_id)
    jobs = list(
        db.scalars(
            select(GenerationJob)
            .where(GenerationJob.exercise_id == exercise_id)
            .order_by(GenerationJob.created_at.desc())
            .limit(JOB_HISTORY_LIMIT)
        )
    )
    versions = dict(
        db.execute(
            select(ScriptVersion.job_id, ScriptVersion.id).where(
                ScriptVersion.job_id.in_([j.id for j in jobs])
            )
        )
        .tuples()
        .all()
    )
    return [
        GenerationJobOut.model_validate(job).model_copy(update={"result_version_id": versions.get(job.id)})
        for job in jobs
    ]


def get_job(db: Session, job_id: uuid.UUID) -> GenerationJob:
    job = db.get(GenerationJob, job_id, populate_existing=True)
    if job is None:
        raise NotFoundError("Không tìm thấy job sinh kịch bản", code="job_not_found")
    return job


def request_generation(
    db: Session, exercise_id: uuid.UUID, user: User, body: GenerationRequest, settings: Settings
) -> GenerationJob:
    get_exercise(db, exercise_id)
    busy = db.scalar(
        select(GenerationJob.id).where(
            GenerationJob.exercise_id == exercise_id,
            GenerationJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
    )
    if busy is not None:
        raise ConflictError(
            "Bài này đang được sinh kịch bản, chờ xong rồi sinh lại", code="generation_in_progress"
        )
    job = GenerationJob(
        exercise_id=exercise_id,
        requested_by=user.id,
        status=JobStatus.QUEUED,
        model=body.model or settings.llm_model,
        instructions=body.instructions,
    )
    db.add(job)
    db.commit()
    return job


def rag_query(exercise: Exercise, analysis: ExerciseAnalysis) -> str:
    """Truy vấn giáo trình: tên bài, đề bài, loại việc và tên hàm trong các thay đổi."""
    parts = [exercise.title, (exercise.prompt_text or "")[:MAX_QUERY_PROMPT_CHARS]]
    parts += sorted({KIND_NAMES.get(c.kind, c.kind) for c in analysis.changes})
    parts += sorted({f for c in analysis.changes for check in c.checks for f in check.get("functions", [])})
    return " ".join(p for p in parts if p)


def _set_stage(db: Session, job: GenerationJob, stage: str) -> None:
    job.stage = stage
    db.commit()


def _generate(
    db: Session, store: FileStore, settings: Settings, llm_factory: LLMFactory, job: GenerationJob
) -> None:
    exercise = db.get(Exercise, job.exercise_id)
    if exercise is None:
        raise NotFoundError("Bài tập đã bị xóa", code="exercise_not_found")
    files = (store.path(exercise.starter_file_path), store.path(exercise.solution_file_path))
    _set_stage(db, job, "diff")
    analysis = analyze_exercise(*files, exercise.sheet_name)
    if not analysis.changes:
        raise LLMError("File đáp án không khác file đề: không có gì để hướng dẫn")
    _set_stage(db, job, "rag")
    linked = list(
        db.scalars(
            select(exercise_textbooks.c.textbook_id).where(exercise_textbooks.c.exercise_id == exercise.id)
        )
    )
    passages = rag.search(db, rag_query(exercise, analysis), linked or None, RAG_PASSAGES)
    info = ExerciseInfo(
        exercise.code, exercise.title, exercise.sheet_name, exercise.prompt_text, job.instructions
    )
    outcome = generate_script(
        analysis,
        info,
        passages,
        llm_factory(settings, job.model),
        files,
        settings.generation_max_attempts,
        on_stage=lambda stage: _set_stage(db, job, stage),
    )
    job.attempts, job.prompt_tokens, job.completion_tokens = (
        outcome.attempts,
        outcome.prompt_tokens,
        outcome.completion_tokens,
    )
    if outcome.script is None:
        db.commit()  # giữ số lần gọi, token của job thất bại (đánh giá kỹ thuật)
        reasons = "; ".join(outcome.remaining_issues[:MAX_ERROR_REASONS])
        raise LLMError(f"AI chưa tạo được kế hoạch hợp lệ sau {outcome.attempts} lần gọi: {reasons}")
    script_service.create_version(
        db,
        exercise,
        outcome.script,
        origin=ScriptOrigin.AI,
        created_by=job.requested_by,
        report=outcome.report,
        job_id=job.id,
    )


def run_generation_job(
    session_factory: sessionmaker[Session],
    store: FileStore,
    settings: Settings,
    llm_factory: LLMFactory,
    job_id: uuid.UUID,
) -> None:
    """Tiến trình nền. Mọi lỗi ghi vào job (status failed + error), không để job treo ở "running"."""
    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        job.status, job.started_at = JobStatus.RUNNING, utcnow()
        db.commit()
        start = time.perf_counter()
        try:
            _generate(db, store, settings, llm_factory, job)
            job.status, job.stage = JobStatus.SUCCEEDED, None
        except LLMError as exc:
            db.rollback()
            job.status, job.error = JobStatus.FAILED, str(exc)[:MAX_ERROR_CHARS]
        except Exception as exc:  # noqa: BLE001 — tiến trình nền phải ghi lỗi vào job thay vì treo
            logger.exception("Job sinh kịch bản %s lỗi", job_id)
            db.rollback()
            job.status, job.error = JobStatus.FAILED, f"Lỗi khi sinh kịch bản: {type(exc).__name__}: {exc}"
        job.duration_ms = int((time.perf_counter() - start) * 1000)
        job.finished_at = utcnow()
        db.commit()
        logger.info("Job %s: %s sau %d ms, %d lần gọi AI", job_id, job.status, job.duration_ms, job.attempts)
