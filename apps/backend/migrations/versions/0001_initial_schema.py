"""Bảng ban đầu theo ERD (docs/thiet-ke/csdl.md, T5.1).

Revision ID: 0001
Revises:
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# JSON trên SQLite, JSONB trên PostgreSQL
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'teacher', 'student')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "classes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], name=op.f("fk_classes_teacher_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classes")),
    )
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_classes_teacher_id"), ["teacher_id"], unique=False)

    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("sheet_name", sa.String(length=31), nullable=False),
        sa.Column("starter_file_path", sa.String(length=500), nullable=False),
        sa.Column("solution_file_path", sa.String(length=500), nullable=False),
        sa.Column("prompt_file_path", sa.String(length=500), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column(
            "skills",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column(
            "warnings",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_exercises_created_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
        sa.UniqueConstraint("code", name=op.f("uq_exercises_code")),
    )
    op.create_table(
        "skill_states",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("skill", sa.String(length=40), nullable=False),
        sa.Column("support_state", sa.String(length=16), nullable=False),
        sa.Column(
            "recent_scores",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "support_state IN ('struggling', 'developing', 'proficient')",
            name=op.f("ck_skill_states_support_state"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], name=op.f("fk_skill_states_student_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("student_id", "skill", name=op.f("pk_skill_states")),
    )
    op.create_table(
        "textbooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_type IN ('pdf', 'docx')", name=op.f("ck_textbooks_file_type")),
        sa.CheckConstraint(
            "status IN ('uploaded', 'indexing', 'ready', 'failed')", name=op.f("ck_textbooks_status")
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["users.id"], name=op.f("fk_textbooks_uploaded_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_textbooks")),
    )
    op.create_table(
        "class_exercises",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"], name=op.f("fk_class_exercises_class_id_classes"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_class_exercises_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("class_id", "exercise_id", name=op.f("pk_class_exercises")),
    )
    op.create_table(
        "class_members",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("study_group", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "study_group IN ('experimental', 'control')", name=op.f("ck_class_members_study_group")
        ),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"], name=op.f("fk_class_members_class_id_classes"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], name=op.f("fk_class_members_student_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("class_id", "student_id", name=op.f("pk_class_members")),
    )
    op.create_table(
        "exercise_textbooks",
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("textbook_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_exercise_textbooks_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["textbook_id"],
            ["textbooks.id"],
            name=op.f("fk_exercise_textbooks_textbook_id_textbooks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("exercise_id", "textbook_id", name=op.f("pk_exercise_textbooks")),
    )
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name=op.f("ck_generation_jobs_status")
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_generation_jobs_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_generation_jobs_requested_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_jobs")),
    )
    with op.batch_alter_table("generation_jobs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_generation_jobs_exercise_id"), ["exercise_id"], unique=False)

    op.create_table(
        "textbook_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("textbook_id", sa.Uuid(), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["textbook_id"],
            ["textbooks.id"],
            name=op.f("fk_textbook_chunks_textbook_id_textbooks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_textbook_chunks")),
    )
    with op.batch_alter_table("textbook_chunks", schema=None) as batch_op:
        batch_op.create_index("ix_textbook_chunks_textbook_ord", ["textbook_id", "ord"], unique=False)

    op.create_table(
        "script_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("origin", sa.String(length=12), nullable=False),
        sa.Column(
            "content",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column(
            "self_check_report",
            JSON_TYPE,
            nullable=True,
        ),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_file_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "origin IN ('ai', 'teacher', 'ai_edited')", name=op.f("ck_script_versions_origin")
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'published', 'archived')",
            name=op.f("ck_script_versions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_script_versions_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_script_versions_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["generation_jobs.id"],
            name=op.f("fk_script_versions_job_id_generation_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["script_versions.id"],
            name=op.f("fk_script_versions_parent_version_id_script_versions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_script_versions_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_script_versions")),
        sa.UniqueConstraint("exercise_id", "revision", name=op.f("uq_script_versions_exercise_id_revision")),
    )
    with op.batch_alter_table("script_versions", schema=None) as batch_op:
        batch_op.create_index(
            "uq_script_versions_one_published",
            ["exercise_id"],
            unique=True,
            postgresql_where=sa.text("status = 'published'"),
            sqlite_where=sa.text("status = 'published'"),
        )

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("script_version_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "client_info",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column(
            "policy_params",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('tutor', 'control')", name=op.f("ck_practice_sessions_mode")),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'abandoned')",
            name=op.f("ck_practice_sessions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_practice_sessions_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["script_version_id"],
            ["script_versions.id"],
            name=op.f("fk_practice_sessions_script_version_id_script_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name=op.f("fk_practice_sessions_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_sessions")),
    )
    with op.batch_alter_table("practice_sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_practice_sessions_exercise_id"), ["exercise_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_practice_sessions_student_id"), ["student_id"], unique=False)

    op.create_table(
        "event_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("step_id", sa.String(length=40), nullable=True),
        sa.Column("data", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_event_logs_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_logs")),
        sa.UniqueConstraint("session_id", "seq", name=op.f("uq_event_logs_session_id_seq")),
    )
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.create_index("ix_event_logs_session_occurred", ["session_id", "occurred_at"], unique=False)

    op.create_table(
        "step_progress",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fail_count", sa.Integer(), nullable=False),
        sa.Column("max_hint_level", sa.Integer(), nullable=False),
        sa.Column("help_count", sa.Integer(), nullable=False),
        sa.Column("idle_seconds", sa.Integer(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('in_progress', 'done', 'skipped')", name=op.f("ck_step_progress_status")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_step_progress_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "step_id", name=op.f("pk_step_progress")),
    )
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("instrument", sa.String(length=16), nullable=False),
        sa.Column(
            "answers",
            JSON_TYPE,
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "instrument IN ('paas', 'sus', 'satisfaction')", name=op.f("ck_survey_responses_instrument")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_survey_responses_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_survey_responses_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_responses")),
    )
    with op.batch_alter_table("survey_responses", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_survey_responses_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("survey_responses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_survey_responses_user_id"))

    op.drop_table("survey_responses")
    op.drop_table("step_progress")
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_event_logs_session_occurred")

    op.drop_table("event_logs")
    with op.batch_alter_table("practice_sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_practice_sessions_student_id"))
        batch_op.drop_index(batch_op.f("ix_practice_sessions_exercise_id"))

    op.drop_table("practice_sessions")
    with op.batch_alter_table("script_versions", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_script_versions_one_published",
            postgresql_where=sa.text("status = 'published'"),
            sqlite_where=sa.text("status = 'published'"),
        )

    op.drop_table("script_versions")
    with op.batch_alter_table("textbook_chunks", schema=None) as batch_op:
        batch_op.drop_index("ix_textbook_chunks_textbook_ord")

    op.drop_table("textbook_chunks")
    with op.batch_alter_table("generation_jobs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_generation_jobs_exercise_id"))

    op.drop_table("generation_jobs")
    op.drop_table("exercise_textbooks")
    op.drop_table("class_members")
    op.drop_table("class_exercises")
    op.drop_table("textbooks")
    op.drop_table("skill_states")
    op.drop_table("exercises")
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_classes_teacher_id"))

    op.drop_table("classes")
    op.drop_table("users")
