"""Dùng chung cho test excel_core: đường dẫn file test, ví dụ kịch bản, bài mẫu."""

import os
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parents[2]
FIXTURES = TESTS / "fixtures"
EXAMPLES = REPO / "schemas" / "tutor-script" / "v1" / "examples"
# Bài của trung tâm (samples/_local/) không lên git và chứa tài liệu chưa được phép công khai:
# chỉ test khi người chạy chủ động bật biến môi trường này trên máy có thư mục đó.
LOCAL_SAMPLES_ENV = "EXCEL_CORE_LOCAL_SAMPLES"


def sample_dirs() -> list[Path]:
    """Thư mục bài mẫu có de.xlsx và dap-an.xlsx: samples/ công khai, cộng samples/_local/ nếu được bật."""
    roots = [REPO / "samples"]
    if os.environ.get(LOCAL_SAMPLES_ENV) == "1":
        roots.append(REPO / "samples" / "_local")
    return sorted(
        d
        for root in roots
        if root.is_dir()
        for d in root.iterdir()
        if (d / "de.xlsx").is_file() and d.name != "_local"
    )


@pytest.fixture
def b09_files() -> tuple[Path, Path]:
    return FIXTURES / "b09" / "de.xlsx", FIXTURES / "b09" / "dap-an.xlsx"


@pytest.fixture
def b22_files() -> tuple[Path, Path]:
    return FIXTURES / "b22" / "de.xlsx", FIXTURES / "b22" / "dap-an.xlsx"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Test nào nhận tham số `sample_folder` sẽ chạy trên mọi bài mẫu và 2 bài tự soạn trong fixtures/."""
    if "sample_folder" in metafunc.fixturenames:
        own = sorted(d for d in FIXTURES.iterdir() if (d / "de.xlsx").is_file())  # bài nhóm tự soạn
        folders = [*sample_dirs(), *own]
        metafunc.parametrize("sample_folder", folders, ids=[f.name for f in folders])
