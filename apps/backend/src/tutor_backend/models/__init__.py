"""Model ORM SQLAlchemy, mỗi nhóm bảng một file (T3.6, csdl.md mục 5).

Import hết ở đây để `Base.metadata` có đủ bảng cho Alembic.
"""

from tutor_backend.models.class_ import Class, ClassExercise, ClassMember
from tutor_backend.models.exercise import Exercise
from tutor_backend.models.generation_job import GenerationJob
from tutor_backend.models.practice import EventLog, PracticeSession, SkillState, StepProgress, SurveyResponse
from tutor_backend.models.script_version import ScriptVersion
from tutor_backend.models.textbook import Textbook, TextbookChunk, exercise_textbooks
from tutor_backend.models.user import User

__all__ = [
    "Class",
    "ClassExercise",
    "ClassMember",
    "EventLog",
    "Exercise",
    "GenerationJob",
    "PracticeSession",
    "ScriptVersion",
    "SkillState",
    "StepProgress",
    "SurveyResponse",
    "Textbook",
    "TextbookChunk",
    "User",
    "exercise_textbooks",
]
