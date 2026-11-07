"""sorted_by — vùng được sắp xếp theo cột khóa (tìm theo tiêu đề), tăng hoặc giảm.

Kiểm bằng thứ tự dữ liệu thật, không dùng Sort.SortFields (quy tắc code 2.3 mục 9). Thứ tự so như Excel:
số < chữ < đúng/sai < lỗi; ô trống luôn ở cuối. Chữ so theo chữ cái gốc (bỏ dấu, không phân biệt hoa thường)
để không lệch với thứ tự tiếng Việt của Excel. `rows_broken`: sắp xếp riêng một cột làm lệch các dòng, so
tập dòng với file đề.
"""

import unicodedata
from collections import Counter
from datetime import datetime

from excel_core.address import cell_address
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, cell_read, check_range
from excel_core.checks.table import find_column, rows_values
from excel_core.checks.values import excel_serial
from excel_core.snapshot import CellValue, ErrorValue, PropertyGroup

TYPE = "sorted_by"
CODES = ("rows_broken", "wrong_order", "not_sorted")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [
        cell_read("current", sheet, check["range"], PropertyGroup.VALUES),
        cell_read("starter", sheet, check["range"], PropertyGroup.VALUES),
    ]


def _text_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold().strip()


def sort_key(value: CellValue) -> tuple[int, object]:
    if isinstance(value, bool):
        return 2, value
    if isinstance(value, float | int):
        return 0, float(value)
    if isinstance(value, datetime):
        return 0, excel_serial(value)
    if isinstance(value, str):
        return 1, _text_key(value)
    if isinstance(value, ErrorValue):
        return 3, value.code
    return 4, ""


def _is_ordered(keys: list[CellValue], descending: bool) -> bool:
    filled = [k for k in keys if k is not None]
    if keys[: len(filled)] != filled:
        return False  # ô trống phải nằm cuối dù tăng hay giảm
    ordered = [sort_key(k) for k in filled]
    pairs = zip(ordered, ordered[1:], strict=False)
    if descending:
        return all(a[0] > b[0] or (a[0] == b[0] and a[1] >= b[1]) for a, b in pairs)
    return all(a[0] < b[0] or (a[0] == b[0] and a[1] <= b[1]) for a, b in pairs)


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    table = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(table, PropertyGroup.VALUES)
    has_header = bool(check.get("has_header", True))
    first_row = table.min_row + 1 if has_header else table.min_row
    key_col = find_column(sheet, table, check["key_column"]) if has_header else table.min_col
    keys = [sheet.cell(cell_address(key_col, row)).value for row in range(first_row, table.max_row + 1)]
    descending = check["order"] == "desc"
    if not _is_ordered(keys, descending):
        code = "wrong_order" if _is_ordered(keys, not descending) else "not_sorted"
        return CheckResult.fail(code, [cell_address(key_col, first_row)])
    if ctx.starter is None:
        return CheckResult.ok()
    starter = ctx.sheet(check, "starter")
    starter.require(table, PropertyGroup.VALUES)
    if Counter(rows_values(sheet, table, first_row)) != Counter(rows_values(starter, table, first_row)):
        return CheckResult.fail("rows_broken", [str(table)], "các dòng không còn giữ nguyên như file đề")
    return CheckResult.ok()
