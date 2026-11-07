"""Đọc mọi bài mẫu (T4.2: "đọc đúng trên mọi bài trong samples/").

samples/ công khai luôn được test. Bài của trung tâm trong samples/_local/ chỉ test khi bật:
    $env:EXCEL_CORE_LOCAL_SAMPLES = "1"
    .venv\\Scripts\\pytest packages/excel_core/tests/readers/test_samples.py
"""

from pathlib import Path

import pytest

from excel_core.readers import read_workbook


def test_starter_and_solution_are_readable(sample_folder: Path):
    for name in ("de.xlsx", "dap-an.xlsx"):
        path = sample_folder / name
        if not path.is_file():
            continue
        snapshot = read_workbook(path)
        assert snapshot.sheet_names
        assert set(snapshot.sheets) <= set(snapshot.sheet_names)


def test_solution_was_saved_by_excel(sample_folder: Path):
    # File đáp án phải có giá trị đã tính cho mọi ô công thức (Backend kiểm khi giảng viên tải lên, FR-W05)
    path = sample_folder / "dap-an.xlsx"
    if not path.is_file():
        pytest.skip("bài chưa có đáp án")
    snapshot = read_workbook(path)
    missing = [
        f"{sheet.name}!{address}"
        for sheet in snapshot.sheets.values()
        for address, cell in sheet.cells.items()
        if cell.is_formula and cell.value_kind == "empty"
    ]
    assert not missing, f"Ô công thức chưa có giá trị (cần mở bằng Excel và lưu lại): {missing[:5]}"
