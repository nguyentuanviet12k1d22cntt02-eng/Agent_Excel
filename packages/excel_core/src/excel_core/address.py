"""Địa chỉ ô kiểu A1: chuyển đổi chữ cột, phân tích vùng, duyệt ô.

Chỉ nhận **một vùng liền kề** (quy tắc code 2.3 mục 7). Mọi địa chỉ trả ra đều bỏ dấu `$`.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

MAX_ROW = 1_048_576
MAX_COL = 16_384

_CELL = re.compile(r"^\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})$")
_COLS = re.compile(r"^\$?([A-Za-z]{1,3})(?::\$?([A-Za-z]{1,3}))?$")
_ROWS = re.compile(r"^\$?([1-9][0-9]{0,6})(?::\$?([1-9][0-9]{0,6}))?$")


class AddressError(ValueError):
    """Địa chỉ ô/vùng không hợp lệ."""


def column_index(letters: str) -> int:
    """Chữ cột → số thứ tự (A → 1, AA → 27)."""
    if not letters.isalpha():
        raise AddressError(f"Chữ cột không hợp lệ: {letters!r}")
    index = 0
    for char in letters.upper():
        index = index * 26 + (ord(char) - ord("A") + 1)
    if index > MAX_COL:
        raise AddressError(f"Cột vượt giới hạn Excel: {letters!r}")
    return index


def column_letter(index: int) -> str:
    """Số thứ tự cột → chữ cột (1 → A, 27 → AA)."""
    if not 1 <= index <= MAX_COL:
        raise AddressError(f"Số cột ngoài giới hạn: {index}")
    letters = ""
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def cell_address(col: int, row: int) -> str:
    """(cột, dòng) → "F10"."""
    return f"{column_letter(col)}{row}"


def parse_cell(address: str) -> tuple[int, int]:
    """ "$F$10" → (6, 10) theo thứ tự (cột, dòng)."""
    match = _CELL.match(address.strip())
    if not match:
        raise AddressError(f"Địa chỉ ô không hợp lệ: {address!r}")
    row = int(match.group(2))
    if row > MAX_ROW:
        raise AddressError(f"Dòng vượt giới hạn Excel: {address!r}")
    return column_index(match.group(1)), row


@dataclass(frozen=True, order=True)
class CellRange:
    """Một vùng chữ nhật liền kề, đánh số từ 1, gồm cả hai biên."""

    min_col: int
    min_row: int
    max_col: int
    max_row: int

    def __post_init__(self) -> None:
        if not (
            1 <= self.min_col <= self.max_col <= MAX_COL and 1 <= self.min_row <= self.max_row <= MAX_ROW
        ):
            raise AddressError(
                f"Vùng không hợp lệ: {self.min_col},{self.min_row},{self.max_col},{self.max_row}"
            )

    @property
    def width(self) -> int:
        return self.max_col - self.min_col + 1

    @property
    def height(self) -> int:
        return self.max_row - self.min_row + 1

    @property
    def size(self) -> int:
        return self.width * self.height

    @property
    def top_left(self) -> str:
        return cell_address(self.min_col, self.min_row)

    def __str__(self) -> str:
        start = self.top_left
        end = cell_address(self.max_col, self.max_row)
        return start if start == end else f"{start}:{end}"

    def rows(self) -> range:
        return range(self.min_row, self.max_row + 1)

    def cols(self) -> range:
        return range(self.min_col, self.max_col + 1)

    def cells(self) -> Iterator[str]:
        """Địa chỉ các ô theo thứ tự từng dòng, trái sang phải."""
        for row in self.rows():
            for col in self.cols():
                yield cell_address(col, row)

    def row_cells(self) -> Iterator[list[str]]:
        """Từng dòng của vùng, mỗi dòng là danh sách địa chỉ ô."""
        for row in self.rows():
            yield [cell_address(col, row) for col in self.cols()]

    def contains(self, other: CellRange) -> bool:
        return (
            self.min_col <= other.min_col
            and self.min_row <= other.min_row
            and self.max_col >= other.max_col
            and self.max_row >= other.max_row
        )

    def contains_cell(self, col: int, row: int) -> bool:
        return self.min_col <= col <= self.max_col and self.min_row <= row <= self.max_row

    def intersects(self, other: CellRange) -> bool:
        return not (
            other.min_col > self.max_col
            or other.max_col < self.min_col
            or other.min_row > self.max_row
            or other.max_row < self.min_row
        )

    def union(self, other: CellRange) -> CellRange:
        """Vùng chữ nhật nhỏ nhất chứa cả hai."""
        return CellRange(
            min(self.min_col, other.min_col),
            min(self.min_row, other.min_row),
            max(self.max_col, other.max_col),
            max(self.max_row, other.max_row),
        )

    def offset(self, rows: int = 0, cols: int = 0) -> CellRange:
        return CellRange(self.min_col + cols, self.min_row + rows, self.max_col + cols, self.max_row + rows)


def parse_range(address: str) -> CellRange:
    """ "F10:F14", "$H$10", "F14:F10" → CellRange (tự sắp lại biên). Không nhận vùng ghép."""
    text = address.strip()
    if "," in text or "!" in text:
        raise AddressError(f"Chỉ nhận một vùng liền kề, không tên sheet: {address!r}")
    parts = text.split(":")
    if len(parts) > 2:
        raise AddressError(f"Địa chỉ vùng không hợp lệ: {address!r}")
    col1, row1 = parse_cell(parts[0])
    col2, row2 = parse_cell(parts[-1])
    return CellRange(min(col1, col2), min(row1, row2), max(col1, col2), max(row1, row2))


def parse_rows(text: str) -> range:
    """ "5:7" → range(5, 8); "5" → range(5, 6)."""
    match = _ROWS.match(text.strip())
    if not match:
        raise AddressError(f"Dải dòng không hợp lệ: {text!r}")
    first, last = int(match.group(1)), int(match.group(2) or match.group(1))
    return range(min(first, last), max(first, last) + 1)


def parse_cols(text: str) -> list[str]:
    """ "C:E" → ["C", "D", "E"]."""
    match = _COLS.match(text.strip())
    if not match:
        raise AddressError(f"Dải cột không hợp lệ: {text!r}")
    first, last = column_index(match.group(1)), column_index(match.group(2) or match.group(1))
    return [column_letter(i) for i in range(min(first, last), max(first, last) + 1)]


def split_sheet_reference(reference: str) -> tuple[str | None, str]:
    """ "'Bài 01'!$G$10:$G$14" → ("Bài 01", "G10:G14"). Không có sheet thì phần đầu là None."""
    text = reference.strip()
    if text.startswith("="):
        text = text[1:]
    sheet: str | None = None
    if "!" in text:
        sheet, text = text.rsplit("!", 1)
        if sheet.startswith("'") and sheet.endswith("'"):
            sheet = sheet[1:-1].replace("''", "'")
    return sheet, text.replace("$", "")
