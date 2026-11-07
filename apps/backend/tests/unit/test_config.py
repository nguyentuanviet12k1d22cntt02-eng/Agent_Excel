from pathlib import Path

from tutor_backend.core.config import Settings


def test_blank_values_from_env_file_fall_back_to_defaults(tmp_path: Path):
    # .env.example để trống DATABASE_URL, LLM_API_KEY: không được hiểu là chuỗi rỗng
    settings = Settings(_env_file=None, database_url="", storage_dir=tmp_path, llm_api_key="", jwt_secret="")
    assert settings.database_url == f"sqlite:///{(tmp_path / 'dev.db').as_posix()}"
    assert settings.is_sqlite
    assert settings.llm_api_key is None
    assert settings.jwt_secret is not None  # khóa tạm khi chưa đặt
    assert settings.files_dir == tmp_path / "files"


def test_postgres_url_is_kept(tmp_path: Path):
    url = "postgresql+psycopg://tutor:matkhau@localhost:5432/tutor"
    settings = Settings(_env_file=None, database_url=url, storage_dir=tmp_path, jwt_secret="x" * 32)
    assert settings.database_url == url
    assert not settings.is_sqlite


def test_secrets_are_not_printed(tmp_path: Path):
    settings = Settings(_env_file=None, storage_dir=tmp_path, llm_api_key="sk-bi-mat", jwt_secret="x" * 32)
    assert "sk-bi-mat" not in repr(settings)


def test_blank_storage_dir_uses_default():
    from tutor_backend.core.config import DEFAULT_STORAGE_DIR

    settings = Settings(_env_file=None, storage_dir="", jwt_secret="x" * 32)
    assert settings.storage_dir == DEFAULT_STORAGE_DIR
