"""Schema lớp học, nhóm thực nghiệm, giao bài (openapi.yaml: Class, /classes/*)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from tutor_backend.models.enums import StudyGroup
from tutor_backend.schemas.common import ApiModel


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    teacher_id: uuid.UUID
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def _dates_in_order(self) -> ClassCreate:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
        return self


class ClassOut(ApiModel):
    id: uuid.UUID
    name: str
    teacher_id: uuid.UUID
    starts_on: date | None = None
    ends_on: date | None = None
    member_count: int = 0
    teacher_name: str | None = None


class MemberIn(BaseModel):
    student_id: uuid.UUID
    study_group: StudyGroup


class ClassExerciseIn(BaseModel):
    exercise_id: uuid.UUID
    due_at: datetime | None = None


class MemberOut(BaseModel):
    student_id: uuid.UUID
    email: str
    full_name: str
    study_group: StudyGroup


class ClassExerciseOut(BaseModel):
    exercise_id: uuid.UUID
    code: str
    title: str
    due_at: datetime | None = None
    published_revision: int | None = None  # None: chưa phát hành, học viên chưa làm được
