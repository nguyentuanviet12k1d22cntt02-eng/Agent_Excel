"""Đọc bảng có dòng tiêu đề: tìm cột theo tiêu đề (quy tắc code 2.3 mục 9: không giả định vị trí cột)."""

import unicodedata

from excel_core.address import CellRange, cell_address
from excel_core.checks.base import CheckSpecError
from excel_core.snapshot import CellValue, SheetSnapshot


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    return " ".join(text.split()).casefold()


def find_column(sheet: SheetSnapshot, table: CellRange, header: str) -> int:
    """Số cột (1 = A) của cột có tiêu đề `header` trong dòng đầu của bảng."""
    wanted = normalize_header(header)
    for col in table.cols():
        if normalize_header(sheet.cell(cell_address(col, table.min_row)).value) == wanted:
            return col
    raise CheckSpecError(f"Không thấy cột tiêu đề {header!r} trong dòng {table.min_row} của vùng {table}")


def rows_values(sheet: SheetSnapshot, table: CellRange, first_row: int) -> list[tuple[CellValue, ...]]:
    """Giá trị từng dòng của bảng, từ dòng `first_row` tới cuối bảng."""
    return [
        tuple(sheet.cell(cell_address(col, row)).value for col in table.cols())
        for row in range(first_row, table.max_row + 1)
    ]
