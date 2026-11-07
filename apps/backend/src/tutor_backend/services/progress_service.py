"""Phiên thực hành, tiến độ từng bước, nhật ký, mức kỹ năng, phiếu khảo sát (FR-D11 – FR-D13, T5.7).

- Phiên do Desktop sinh id (UUID) để tạo được cả khi mất mạng; gửi lại nhiều lần không sao (PUT).
- Nhật ký gửi theo lô; sự kiện trùng `seq` trong phiên bị bỏ qua, nên gửi lại một lô lỗi mạng là an toàn.
- Mức hỗ trợ theo kỹ năng (fading) tính lại khi một bước xong: luat-goi-y.md mục 5.
"""

import uuid
from decimal import Decimal
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tutor_backend.core.errors import ConflictError, InvalidError, NotFoundError
from tutor_backend.models import (
    EventLog,
    Exercise,
    PracticeSession,
    ScriptVersion,
    SkillState,
    StepProgress,
    SurveyResponse,
    User,
)
from tutor_backend.models.enums import Instrument, StepStatus, SupportState
from tutor_backend.schemas.desktop import EventBatchResult, EventIn, SessionUpsert, StepProgressIn, SurveyIn

RECENT_STEPS = 3  # mức hỗ trợ = trung bình điểm 3 bước gần nhất của kỹ năng
STRUGGLING_BELOW = 0.75
PROFICIENT_FROM = 1.5
PAAS_RANGE = range(1, 10)
SUS_ITEMS = 10
SUS_RANGE = range(1, 6)
SUS_SCALE = 2.5
FINAL_STEP_STATES = frozenset({StepStatus.DONE, StepStatus.SKIPPED})


def step_score(progress: StepProgressIn) -> int:
    """Điểm độc lập của bước (luat-goi-y.md mục 5): Desktop gửi kèm thì dùng, không thì tính lại."""
    if progress.status == StepStatus.SKIPPED:
        return 0
    if progress.score is not None:
        return progress.score
    if progress.max_hint_level == 0 and progress.fail_count <= 1:
        return 2
    return 1 if progress.max_hint_level <= 2 else 0


def support_state(scores: list[int]) -> SupportState:
    if not scores:
        return SupportState.DEVELOPING
    average = mean(scores[-RECENT_STEPS:])
    if average < STRUGGLING_BELOW:
        return SupportState.STRUGGLING
    return SupportState.PROFICIENT if average >= PROFICIENT_FROM else SupportState.DEVELOPING


def _session(db: Session, session_id: uuid.UUID, student: User) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if session is None or session.student_id != student.id:
        raise NotFoundError("Không tìm thấy phiên thực hành", code="session_not_found")
    return session


def upsert_session(db: Session, session_id: uuid.UUID, student: User, data: SessionUpsert) -> bool:
    """Tạo hoặc cập nhật phiên; trả True nếu vừa tạo. Phiên đã có thì không đổi bài/revision được."""
    exercise = db.scalar(select(Exercise).where(Exercise.code == data.exercise_code))
    version = db.get(ScriptVersion, data.script_version_id)
    if exercise is None or version is None or version.exercise_id != exercise.id:
        raise InvalidError("Mã bài hoặc revision kịch bản không khớp", code="script_mismatch")
    session = db.get(PracticeSession, session_id)
    fields = data.model_dump(exclude={"exercise_code", "client_info"})
    fields["client_info"] = data.client_info.model_dump(exclude_none=True)
    if session is None:
        db.add(PracticeSession(id=session_id, student_id=student.id, exercise_id=exercise.id, **fields))
        db.commit()
        return True
    if session.student_id != student.id:
        raise ConflictError("Mã phiên đã được dùng", code="session_conflict")
    if session.script_version_id != data.script_version_id:
        # Phiên đang dở giữ nguyên revision (luoc-do-kich-ban.md 4.2): nhật ký không trộn hai phiên bản
        raise ConflictError("Phiên đã gắn với revision khác của kịch bản", code="session_revision_locked")
    for key, value in fields.items():
        setattr(session, key, value)
    db.commit()
    return False


def _step_skills(version: ScriptVersion, step_id: str) -> list[str]:
    content = version.content
    step = next((s for s in content["steps"] if s["id"] == step_id), None)
    if step is None:
        raise InvalidError(f"Kịch bản không có bước {step_id}", code="unknown_step")
    return list(step.get("skills") or content["exercise"].get("skills") or [])


def _update_skills(db: Session, student: User, skills: list[str], score: int) -> None:
    for skill in skills:
        state = db.get(SkillState, (student.id, skill))
        if state is None:
            state = SkillState(student_id=student.id, skill=skill, recent_scores=[])
            db.add(state)
        scores = [*state.recent_scores, score][-RECENT_STEPS:]
        state.recent_scores = scores
        state.support_state = support_state(scores)


def record_step(
    db: Session, session_id: uuid.UUID, step_id: str, student: User, data: StepProgressIn
) -> None:
    session = _session(db, session_id, student)
    version = db.get(ScriptVersion, session.script_version_id)
    if version is None:
        raise NotFoundError("Không tìm thấy kịch bản của phiên", code="script_not_found")
    skills = _step_skills(version, step_id)
    progress = db.get(StepProgress, (session_id, step_id))
    newly_final = data.status in FINAL_STEP_STATES and (
        progress is None or progress.status not in FINAL_STEP_STATES
    )
    values = data.model_dump()
    values["score"] = step_score(data) if data.status in FINAL_STEP_STATES else data.score
    if progress is None:
        db.add(StepProgress(session_id=session_id, step_id=step_id, **values))
    else:
        for key, value in values.items():
            setattr(progress, key, value)
    if newly_final:  # gửi lại bước đã xong thì không tính điểm hai lần
        _update_skills(db, student, skills, values["score"])
    db.commit()


def record_events(
    db: Session, session_id: uuid.UUID, student: User, events: list[EventIn]
) -> EventBatchResult:
    _session(db, session_id, student)
    seqs = [e.seq for e in events]
    existing = set(
        db.scalars(select(EventLog.seq).where(EventLog.session_id == session_id, EventLog.seq.in_(seqs)))
    )
    fresh: dict[int, EventIn] = {}
    for event in events:
        if event.seq not in existing and event.seq not in fresh:
            fresh[event.seq] = event
    db.add_all(EventLog(session_id=session_id, **event.model_dump()) for event in fresh.values())
    db.commit()
    return EventBatchResult(accepted=len(fresh), duplicates=len(events) - len(fresh))


def skill_states(db: Session, student: User) -> dict[str, SupportState]:
    rows = db.scalars(select(SkillState).where(SkillState.student_id == student.id))
    return {row.skill: SupportState(row.support_state) for row in rows}


def _survey_score(instrument: Instrument, answers: Any) -> Decimal | None:
    if instrument == Instrument.PAAS:
        if not isinstance(answers, int) or isinstance(answers, bool) or answers not in PAAS_RANGE:
            raise InvalidError("Phiếu Paas: một số nguyên từ 1 đến 9", code="survey_invalid")
        return Decimal(answers)
    if instrument == Instrument.SUS:
        if (
            not isinstance(answers, list)
            or len(answers) != SUS_ITEMS
            or any(a not in SUS_RANGE for a in answers)
        ):
            raise InvalidError("Phiếu SUS: 10 số nguyên từ 1 đến 5", code="survey_invalid")
        # Câu lẻ (1, 3, 5…) tích cực: điểm − 1; câu chẵn tiêu cực: 5 − điểm; tổng × 2,5 → thang 0–100
        total = sum(a - 1 if i % 2 == 0 else 5 - a for i, a in enumerate(answers))
        return Decimal(str(total * SUS_SCALE))
    if not isinstance(answers, dict):
        raise InvalidError("Phiếu hài lòng: một đối tượng JSON", code="survey_invalid")
    return None


def record_survey(db: Session, user: User, data: SurveyIn) -> SurveyResponse:
    if data.session_id is not None:
        _session(db, data.session_id, user)
    response = SurveyResponse(
        user_id=user.id,
        session_id=data.session_id,
        instrument=data.instrument,
        answers=data.answers,
        score=_survey_score(data.instrument, data.answers),
    )
    db.add(response)
    db.commit()
    return response
