"""Diff chạy được trên mọi bài mẫu (T4.3).

Bài trong samples/_local/ chỉ chạy khi bật EXCEL_CORE_LOCAL_SAMPLES=1.
"""

from pathlib import Path

import pytest

from excel_core.diff import diff_files


def test_solution_differs_from_starter(sample_folder: Path):
    starter, solution = sample_folder / "de.xlsx", sample_folder / "dap-an.xlsx"
    if not solution.is_file():
        pytest.skip("bài chưa có đáp án")
    diff = diff_files(starter, solution)
    assert diff.cell_changes(), "file đáp án không khác file đề ở vùng ô nào"
    assert all(change.range for change in diff.cell_changes())
