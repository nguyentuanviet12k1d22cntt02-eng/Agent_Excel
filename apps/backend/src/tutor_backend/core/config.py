"""Cấu hình Backend, đọc từ biến môi trường và `apps/backend/.env` (quy tắc code 2.4 mục 3).

Mẫu: `.env.example` ở gốc repo. Không đọc `os.environ` rải rác ở nơi khác.
"""

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[3]  # apps/backend
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_STORAGE_DIR = BACKEND_DIR / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # ----- CSDL và kho file -----
    # Bỏ trống: SQLite trong apps/backend/storage/ (phát triển). Triển khai: postgresql+psycopg://...
    database_url: str = ""
    storage_dir: Path = DEFAULT_STORAGE_DIR
    database_echo: bool = False

    # ----- Xác thực (kien-truc.md mục 2: access 60 phút, refresh 14 ngày) -----
    jwt_secret: SecretStr | None = None
    access_token_minutes: int = 60
    refresh_token_days: int = 14

    # ----- Web quản trị khi phát triển (Vite) -----
    cors_origins: list[str] = ["http://localhost:5173"]

    # ----- LLM (T0.4: Inception Labs, API tương thích OpenAI) -----
    llm_provider: str = "inceptionlabs"
    llm_base_url: str = "https://api.inceptionlabs.ai/v1"
    llm_model: str = "mercury-3"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = 120.0
    llm_max_tokens: int = 12000

    # ----- Sinh kịch bản, tiến trình nền (kien-truc.md A6) -----
    generation_max_attempts: int = 3
    job_workers: int = 2

    @field_validator("llm_api_key", "jwt_secret", mode="before")
    @classmethod
    def _blank_secret_is_none(cls, value: object) -> object:
        return None if value in ("", None) else value

    @field_validator("storage_dir", mode="before")
    @classmethod
    def _blank_storage_dir_is_default(cls, value: object) -> object:
        # STORAGE_DIR= (để trống trong .env) không được hiểu là thư mục hiện tại
        return DEFAULT_STORAGE_DIR if value in ("", None) else value

    @model_validator(mode="after")
    def _fill_defaults(self) -> Settings:
        if not self.database_url:
            self.database_url = f"sqlite:///{(self.storage_dir / 'dev.db').as_posix()}"
        if self.jwt_secret is None:
            # Chỉ để chạy thử: token mất hiệu lực sau mỗi lần khởi động lại
            logger.warning("JWT_SECRET chưa đặt trong .env: dùng khóa ngẫu nhiên tạm thời")
            self.jwt_secret = SecretStr(secrets.token_urlsafe(32))
        return self

    @property
    def files_dir(self) -> Path:
        """Thư mục lưu file tải lên (xlsx, pdf, docx), tên file theo id."""
        return self.storage_dir / "files"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
