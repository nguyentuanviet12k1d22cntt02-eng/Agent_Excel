"""Phụ thuộc dùng chung cho router (khai báo bằng `Annotated` để tái dùng và để ruff B008 không báo)."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from tutor_backend.core.config import Settings
from tutor_backend.core.jobs import JobRunner
from tutor_backend.db.session import get_db


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_jobs(request: Request) -> JobRunner:
    return request.app.state.jobs


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
Jobs = Annotated[JobRunner, Depends(get_jobs)]
