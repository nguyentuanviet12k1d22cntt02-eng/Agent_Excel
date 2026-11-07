"""Lắp ráp ứng dụng FastAPI.

Chạy khi phát triển:  .venv\\Scripts\\python -m tutor_backend serve
Hoặc:                 .venv\\Scripts\\uvicorn tutor_backend.main:create_app --factory --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import tutor_backend
from tutor_backend.api import health
from tutor_backend.api.v1 import api_router
from tutor_backend.core.config import Settings, get_settings
from tutor_backend.core.errors import install_error_handlers
from tutor_backend.core.jobs import JobRunner, ThreadJobRunner
from tutor_backend.db.session import create_db_engine, create_session_factory

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None, *, job_runner: JobRunner | None = None) -> FastAPI:
    """Tạo ứng dụng. Test truyền `settings` và `job_runner` riêng; khi chạy thật đọc từ .env."""
    settings = settings or get_settings()
    engine = create_db_engine(settings)
    jobs = job_runner or ThreadJobRunner(settings.job_workers)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings.files_dir.mkdir(parents=True, exist_ok=True)
        yield
        jobs.shutdown()
        engine.dispose()

    app = FastAPI(
        title="Gia sư AI Excel — REST API",
        version=tutor_backend.__version__,
        description="Backend cho Web quản trị và Desktop gia sư. Thiết kế: docs/thiet-ke/openapi.yaml.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.jobs = jobs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["ETag"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=API_PREFIX)
    return app
