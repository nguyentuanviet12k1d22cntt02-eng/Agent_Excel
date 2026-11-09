"""Bài chèn/xóa cột: phân tích ra một mục "xóa cột" kiểm bằng layout_matches, không ra hàng loạt mục giả."""

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font

from excel_core.script import self_check_files
from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.plan import Plan, PlanStep
from tutor_backend.ai.script_builder import ExerciseInfo, build_script

SHEET = "Bài tập"
HEADERS = ("Mã hàng", "Tên hàng", "Số lượng", "Đơn giá")
ROWS = (("A01", "Bút bi", 10, 5000), ("A02", "Vở", 20, 12000), ("A03", "Thước", 5, 8000))


def build(path: Path, gap: int) -> Path:
    """Bảng từ cột B; `gap` cột trống chen giữa cột thứ 2 và thứ 3 (đề có 2, đáp án đã xóa nên 0)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET
    ws["B2"] = "DANH SÁCH HÀNG"
    ws["B2"].font = Font(bold=True, size=14)
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=5 + gap)
    for row, values in enumerate((HEADERS, *ROWS), start=4):
        for index, value in enumerate(values):
            col = 2 + index + (gap if index >= 2 else 0)
            cell = ws.cell(row, col, value)
            cell.font = Font(bold=row == 4)
            cell.alignment = Alignment(horizontal="center" if row == 4 else None)
    wb.save(path)
    return path


def test_deleted_columns_become_one_layout_step(tmp_path: Path):
    starter, solution = build(tmp_path / "de.xlsx", gap=2), build(tmp_path / "dap-an.xlsx", gap=0)

    analysis = analyze_exercise(starter, solution, SHEET)

    (item,) = analysis.changes
    assert (item.kind, item.description, item.label) == (
        "col_deleted",
        "xóa 2 cột trống",
        "cột D–E của file đề",
    )
    assert item.range == "D2:E7"  # vùng khoanh trên bố cục học viên đang thấy (file đề)
    assert item.checks == (
        {
            "type": "layout_matches",
            "range": "D4:E7",
            "key_column": "Số lượng",
            "description": "Dữ liệu dời đúng chỗ sau khi chèn/xóa.",
        },
    )
    # Dữ liệu dời chỗ là hợp lệ: không đặt điều kiện "giữ nguyên dữ liệu" theo địa chỉ
    assert analysis.global_checks == ()


def test_layout_step_passes_self_check(tmp_path: Path):
    starter, solution = build(tmp_path / "de.xlsx", gap=2), build(tmp_path / "dap-an.xlsx", gap=0)
    analysis = analyze_exercise(starter, solution, SHEET)
    step = PlanStep(
        title="Xóa cột trống",
        task="Bảng không còn cột trống chen giữa.",
        change_ids=("c1",),
        ui_controls=("CellsDeleteSmart",),
        hint_orientation="Bảng đang có cột trống thừa.",
        hint_tool="Dùng lệnh Delete trên thẻ Home.",
        hint_location="Chọn các cột trống được khoanh.",
        hint_detailed="Chọn hai cột trống rồi xóa cột.",
        actions=("Chọn hai cột trống.", "Home > Delete > Delete Sheet Columns."),
        alternative=None,
        feedback=(),
        reference_ids=(),
    )
    plan = Plan(
        summary="Xóa cột trống.", skills=("sheet_structure",), completion_message="Xong!", steps=(step,)
    )
    script = build_script(analysis, plan, ExerciseInfo("bai-06-cot", "Thao tác với cột", SHEET), {}, "test")

    report = self_check_files(script, starter, solution)

    assert report.errors == ()  # đạt trên đáp án, chưa đạt trên đề
    assert report.diff_coverage == 1.0
