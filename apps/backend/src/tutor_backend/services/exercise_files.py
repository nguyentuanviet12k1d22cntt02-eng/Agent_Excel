"""Kiểm file đề và file đáp án khi giảng viên tải lên (FR-W05).

Lỗi chặn (không tạo được bài): file không mở được, thiếu sheet làm bài, đáp án chưa có giá trị đã tính.
Điểm cần xem (vẫn tạo bài, trả về `warnings`): hai file lệch bố cục, đáp án không khác đề.
"""

import zipfile
from pathlib import Path

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from excel_core.address import group_into_ranges, parse_cell
from excel_core.diff import diff_workbooks, pair_request
from excel_core.readers import find_uncalculated_formulas, read_workbook
from excel_core.snapshot import SheetSnapshot
from tutor_backend.core.errors import InvalidError

MAX_LISTED = 8  # số vùng liệt kê trong một cảnh báo


def _sheet_names(path: Path, field: str, label: str) -> list[str]:
    try:
        workbook = openpyxl.load_workbook(path, read_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise InvalidError(
            f"Không mở được {label}: {exc}",
            code="file_invalid",
            errors=[{"path": f"/{field}", "message": "không phải file .xlsx hợp lệ"}],
        ) from exc
    try:
        return workbook.sheetnames
    finally:
        workbook.close()  # chế độ read_only giữ file mở: không đóng thì Windows không xóa được file


def _ranges(addresses: list[str]) -> str:
    ranges = [str(r) for r in group_into_ranges(parse_cell(a) for a in addresses)]
    more = f" (và {len(ranges) - MAX_LISTED} vùng khác)" if len(ranges) > MAX_LISTED else ""
    return ", ".join(ranges[:MAX_LISTED]) + more


def _layout_warnings(starter: SheetSnapshot, solution: SheetSnapshot) -> list[str]:
    warnings = []
    labels = [
        address
        for address, cell in starter.cells.items()
        if cell.value_kind == "text" and not cell.is_formula and solution.cell(address).value != cell.value
    ]
    if labels:
        warnings.append(
            f"Ô chữ khác nhau giữa đề và đáp án ở {_ranges(labels)}: kiểm tra hai file có cùng bố cục"
        )
    formulas = [
        address
        for address, cell in starter.cells.items()
        if cell.is_formula and solution.cell(address).formula != cell.formula
    ]
    if formulas:
        warnings.append(f"Công thức có sẵn trong đề bị đổi hoặc mất trong đáp án ở {_ranges(formulas)}")
    return warnings


def check_exercise_files(starter: Path, solution: Path, sheet: str) -> list[str]:
    """Kiểm hai file; lỗi chặn ném InvalidError, còn lại trả danh sách cảnh báo."""
    names = {
        "starter_file": _sheet_names(starter, "starter_file", "file đề"),
        "solution_file": _sheet_names(solution, "solution_file", "file đáp án"),
    }
    for field, sheet_names in names.items():
        if sheet not in sheet_names:
            raise InvalidError(
                f"Không có sheet {sheet!r} trong {'file đề' if field == 'starter_file' else 'file đáp án'}",
                code="sheet_not_found",
                errors=[{"path": "/sheet_name", "message": f"các sheet có: {', '.join(sheet_names)}"}],
            )
    missing = find_uncalculated_formulas(solution)
    if missing:
        raise InvalidError(
            "File đáp án chưa có giá trị của công thức: mở file bằng Excel, bấm Lưu rồi tải lên lại",
            code="solution_not_calculated",
            errors=[{"path": "/solution_file", "message": cell} for cell in missing[:MAX_LISTED]],
        )
    request = pair_request(starter, solution)
    starter_snapshot, solution_snapshot = read_workbook(starter, request), read_workbook(solution, request)
    warnings = [
        f"Sheet {name!r} chỉ có trong {where}"
        for name, where in [(n, "file đề") for n in names["starter_file"] if n not in names["solution_file"]]
        + [(n, "file đáp án") for n in names["solution_file"] if n not in names["starter_file"]]
    ]
    warnings += _layout_warnings(starter_snapshot.sheet(sheet), solution_snapshot.sheet(sheet))
    changes = [c for c in diff_workbooks(starter_snapshot, solution_snapshot) if c.sheet == sheet]
    if not changes:
        warnings.append("File đáp án không khác file đề ở sheet làm bài: không có gì để hướng dẫn")
    return warnings
