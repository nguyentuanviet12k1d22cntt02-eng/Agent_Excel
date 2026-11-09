"""Kịch bản theo quy trình (bước có `operation`): tự kiểm theo trạng thái ngay trước/sau từng thao tác, chấm
thử biết học viên đã làm tới bước nào. Bài nhỏ kiểu bài 06: hiện cột E đang ẩn rồi xóa hai cột trống D, E."""

import copy
from pathlib import Path
from typing import Any

import openpyxl
import pytest
from openpyxl.styles import Font

from excel_core.script import self_check_files, validate_script
from excel_core.script.grade import grade_files

SHEET = "S"
HEADERS = ("Mã hàng", "Tên hàng", "Số lượng", "Đơn giá")


def build(path: Path, gap: int, hidden: str | None = None) -> Path:
    """Bảng từ cột B; `gap` cột trống chen giữa cột thứ 2 và thứ 3, tiêu đề gộp cả bảng."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET
    ws["B2"] = "DANH SÁCH HÀNG"
    ws["B2"].font = Font(bold=True)
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=5 + gap)
    rows = (HEADERS, ("A01", "Bút", 10, 5000), ("A02", "Vở", 20, 12000))
    for row, values in enumerate(rows, start=4):
        for index, value in enumerate(values):
            ws.cell(row, 2 + index + (gap if index >= 2 else 0), value)
    if hidden:
        ws.column_dimensions[hidden].hidden = True
    wb.save(path)
    return path


def step(step_id: str, operation: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": step_id,
        "task": "Làm theo yêu cầu của đề.",
        "targets": {"cells": [{"range": "D4:E6", "role": "target"}]},
        "operation": operation,
        "checks": checks,
        "hints": [
            {"level": 1, "text": "Nhớ lại yêu cầu."},
            {"level": 2, "text": "Dùng nhóm Cells trên thẻ Home."},
            {
                "level": 3,
                "text": "Chọn vùng được khoanh.",
                "highlight": [{"cells": {"range": "D4:E6", "role": "target"}}],
            },
            {"level": 4, "text": "Làm như sau:", "actions": ["Chọn cột.", "Bấm lệnh."]},
        ],
    }


def literal(address: str, value: str) -> dict[str, Any]:
    return {"type": "value_equals", "range": address, "expected": {"from": "literal", "value": value}}


SCRIPT: dict[str, Any] = {
    "schema_version": "1",
    "exercise": {"id": "quy-trinh-cot", "title": "Thao tác với cột", "sheet": SHEET},
    "revision": 1,
    "meta": {"origin": "teacher"},
    "steps": [
        step(
            "s1_hien_e",
            {"action": "unhide", "axis": "cols", "lines": ["E"]},
            [{"type": "row_col_hidden", "cols": "E", "hidden": False}],
        ),
        step(
            "s2_xoa_d_e",
            {"action": "delete", "axis": "cols", "lines": ["D", "E"]},
            [literal("C4", "Tên hàng"), literal("D4", "Số lượng"), literal("E4", "Đơn giá")],
        ),
    ],
}


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    return build(tmp_path / "de.xlsx", gap=2, hidden="E"), build(tmp_path / "dap-an.xlsx", gap=0)


def test_procedure_script_is_valid_and_passes_self_check(files: tuple[Path, Path]):
    assert validate_script(SCRIPT).ok
    report = self_check_files(SCRIPT, *files)
    assert report.ok, report.errors
    # Hiện cột E: đạt sau bước, chưa đạt trước bước (trên file đáp án cột E là cột khác, không còn ý nghĩa)
    assert all(c.passes_on_solution and c.fails_on_starter for c in report.checks if c.step_id == "s1_hien_e")
    assert report.warnings == ()  # ô mốc C4 vốn đúng từ trước: không cảnh báo "đạt sẵn" ở bước quy trình


def test_steps_in_the_wrong_order_are_an_error(files: tuple[Path, Path]):
    swapped = copy.deepcopy(SCRIPT)
    swapped["steps"].reverse()
    report = self_check_files(swapped, *files)
    assert not report.ok
    assert any("quy trình không làm được" in e for e in report.errors)  # xóa xong thì không còn E để hiện


def test_procedure_not_reaching_the_solution_is_an_error(files: tuple[Path, Path]):
    partial = copy.deepcopy(SCRIPT)
    partial["steps"][1]["operation"]["lines"] = ["D"]  # quên xóa cột E
    report = self_check_files(partial, *files)
    assert any("còn khác đáp án" in e for e in report.errors)


def test_grading_finds_how_far_the_learner_got(files: tuple[Path, Path], tmp_path: Path):
    starter, solution = files
    middle = build(tmp_path / "giua-chung.xlsx", gap=2)  # đã hiện cột E, chưa xóa

    def statuses(current: Path) -> list[str]:
        return [s.status.value for s in grade_files(SCRIPT, current, starter, solution).steps]

    assert statuses(starter) == ["failed", "not_evaluable"]  # bước 2 "chưa tới"
    assert statuses(middle) == ["passed", "failed"]
    # Làm xong: cột E đã bị xóa (cột E bây giờ là Đơn giá), bước 1 tính là đã qua
    report = grade_files(SCRIPT, solution, starter, solution)
    assert [s.status.value for s in report.steps] == ["passed", "passed"] and report.current_step_id is None
