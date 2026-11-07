"""alignment — căn lề ngang/dọc, xuống dòng.

Căn ngang so theo **căn lề hiển thị thực tế**: ô General chứa số/ngày hiện căn phải, chứa chữ hiện căn trái,
đúng/sai và lỗi hiện căn giữa (T2.6: Excel tự căn phải số). Ô trống General không có căn lề thực tế nào,
nên kiểm `["right"]` không đạt sẵn trên file đề còn trống. Giá trị "general" trong danh sách vẫn nhận ô
để General theo nghĩa đen.
"""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.snapshot import AlignmentInfo, CellSnapshot, PropertyGroup

TYPE = "alignment"
CODES = ("wrong_alignment", "not_wrapped")
DEFAULT_ALIGNMENT = AlignmentInfo("general", "bottom", False)
_GENERAL_SHOWS_AS = {
    "number": "right",
    "date": "right",
    "text": "left",
    "logical": "center",
    "error": "center",
}


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.STYLE, PropertyGroup.VALUES)]


def effective_horizontal(cell: CellSnapshot) -> str:
    """Căn ngang người học nhìn thấy trên màn hình."""
    alignment = cell.alignment or DEFAULT_ALIGNMENT
    if alignment.horizontal != "general":
        return alignment.horizontal
    return _GENERAL_SHOWS_AS.get(cell.value_kind, "general")


def _cell_code(cell: CellSnapshot, check: CheckSpec) -> str | None:
    alignment = cell.alignment or DEFAULT_ALIGNMENT
    horizontal = check.get("horizontal")
    if horizontal and effective_horizontal(cell) not in horizontal and alignment.horizontal not in horizontal:
        return "wrong_alignment"
    vertical = check.get("vertical")
    if vertical and alignment.vertical not in vertical:
        return "wrong_alignment"
    wrap = check.get("wrap_text")
    if wrap is True and not alignment.wrap_text:
        return "not_wrapped"
    if wrap is False and alignment.wrap_text:
        return "wrong_alignment"
    return None


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.STYLE)
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        code = _cell_code(cell, check)
        if code:
            failures.add(code, address)
    return failures.result()
