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


def build(path: Path, gap: int, merge: bool = True, hidden: str | None = None) -> Path:
    """Bảng từ cột B; `gap` cột trống chen giữa cột thứ 2 và thứ 3 (đề có 2, đáp án đã xóa nên 0)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET
    ws["B2"] = "DANH SÁCH HÀNG"
    ws["B2"].font = Font(bold=True, size=14)
    if merge:
        ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=5 + gap)
    if hidden:
        ws.column_dimensions[hidden].hidden = True
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
    # Tiêu đề gộp B2:G2 đi qua cột D–E nhưng bấm chuột vào tiêu đề cột vẫn chỉ chọn D–E: khoanh cả hai cột
    # (trên bố cục file đề), không cần dặn gì thêm
    assert (item.range, item.context) == ("D2:E7", "")
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


def test_resizing_columns_inside_a_wide_merge_guards_neighbours(tmp_path: Path):
    starter = build(tmp_path / "de.xlsx", gap=0)
    solution = build(tmp_path / "dap-an.xlsx", gap=0)
    wb = openpyxl.load_workbook(solution)
    ws = wb[SHEET]
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 20
    wb.save(solution)

    analysis = analyze_exercise(starter, solution, SHEET)

    (d, e) = analysis.changes
    assert (d.range, e.range, d.context) == ("D2:D7", "E2:E7", "")
    # Bấm vào ô gộp B2:E2 rồi đổi độ rộng thì đổi cả B–E: kiểm các cột khác của ô gộp giữ nguyên
    guards = [c for c in d.checks if c.get("description", "").endswith("(không chọn lan theo ô gộp).")]
    assert [g["cols"] for g in guards] == ["B", "C"]  # E cũng đổi độ rộng nên không phải giữ nguyên


def test_deleting_a_hidden_column_tells_to_select_through_the_name_box(tmp_path: Path):
    # Như bài 06: cột E của file đề đang ẩn, kéo chuột từ D chỉ chọn được D (hoặc lố sang F)
    starter = build(tmp_path / "de.xlsx", gap=2, hidden="E")
    solution = build(tmp_path / "dap-an.xlsx", gap=0)

    (item,) = analyze_exercise(starter, solution, SHEET).changes

    # Gõ cả cột "D:E" vào Name Box thì Excel nới theo tiêu đề gộp B2:G2: gõ các ô ở một dòng trong bảng
    assert item.range == "D4:E4"
    assert "cột E đang ẩn" in item.context and "gõ D4:E4 vào ô Name Box" in item.context
    assert "Excel chọn lan theo ô gộp" in item.context and "Delete Sheet Columns" in item.context
    assert item.description == "xóa 2 cột trống"


def test_hidden_column_without_merges_still_gets_a_note(tmp_path: Path):
    starter = build(tmp_path / "de.xlsx", gap=2, merge=False, hidden="E")
    solution = build(tmp_path / "dap-an.xlsx", gap=0, merge=False)

    (item,) = analyze_exercise(starter, solution, SHEET).changes

    assert item.range == "D2:E7"  # không có ô gộp: khoanh cả hai cột trong vùng dữ liệu
    assert "cột E đang ẩn" in item.context and "gõ D2:E7 vào ô Name Box" in item.context
    assert "ô gộp" not in item.context


def test_plain_deleted_columns_need_no_note(tmp_path: Path):
    starter = build(tmp_path / "de.xlsx", gap=2, merge=False)
    solution = build(tmp_path / "dap-an.xlsx", gap=0, merge=False)

    (item,) = analyze_exercise(starter, solution, SHEET).changes

    assert (item.range, item.context) == ("D2:E7", "")
