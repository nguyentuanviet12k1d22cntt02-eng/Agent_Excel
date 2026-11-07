"""So sánh giá trị ô và nhận ra dữ liệu gõ sai kiểu (số/ngày lưu dạng chữ)."""

import math
import re
import unicodedata
from datetime import datetime

from excel_core.snapshot import CellSnapshot, CellValue, ErrorValue

EXCEL_EPOCH = datetime(1899, 12, 30)
FLOAT_EPSILON = 1e-9
_DATE_TEXT = re.compile(r"^\s*(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})\s*$")
_LOGICAL_TEXT = frozenset({"true", "false", "đúng", "sai"})


def excel_serial(value: datetime) -> float:
    """datetime → số seri ngày của Excel (để so ngày với số)."""
    return (value - EXCEL_EPOCH).total_seconds() / 86400


def number_from_text(text: str) -> float | None:
    """Chữ trông như số ("1250", "1,250", "1.250,5", "12%") → số; không phải số → None."""
    cleaned = text.strip().replace(" ", "").replace(" ", "")
    if not cleaned:
        return None
    percent = cleaned.endswith("%")
    cleaned = cleaned.rstrip("%")
    candidates = [cleaned, cleaned.replace(",", ""), cleaned.replace(".", "").replace(",", ".")]
    for candidate in candidates:
        try:
            number = float(candidate)
        except ValueError:
            continue
        if math.isfinite(number):
            return number / 100 if percent else number
    return None


def looks_like_date(text: str) -> bool:
    return _DATE_TEXT.match(text) is not None


def looks_like_logical(text: str) -> bool:
    return text.strip().casefold() in _LOGICAL_TEXT


def _numeric(value: CellValue) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float | int):
        return float(value)
    if isinstance(value, datetime):
        return excel_serial(value)
    return None


def values_equal(actual: CellValue, expected: CellValue, tolerance: float = 0.0) -> bool:
    """So giá trị theo ý nghĩa: số có sai số; ngày so được với số seri; chữ so nguyên văn (chuẩn hóa Unicode).

    Chữ không bỏ khoảng trắng, không bỏ hoa/thường: bài TRIM, UPPER... cần đúng từng ký tự.
    """
    if expected is None or actual is None:
        return actual is None and expected is None
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and actual == expected
    if isinstance(expected, ErrorValue) or isinstance(actual, ErrorValue):
        return actual == expected
    a, e = _numeric(actual), _numeric(expected)
    if a is not None and e is not None:
        return abs(a - e) <= max(tolerance, FLOAT_EPSILON * max(1.0, abs(e)))
    if isinstance(actual, str) and isinstance(expected, str):
        return unicodedata.normalize("NFC", actual) == unicodedata.normalize("NFC", expected)
    return False


def is_number_stored_as_text(cell: CellSnapshot, expected: CellValue = None) -> bool:
    """Ô chứa chữ trông như số (và bằng số kỳ vọng nếu có): lỗi hay gặp stored_as_text."""
    if cell.value_kind != "text" or not isinstance(cell.value, str):
        return False
    number = number_from_text(cell.value)
    if number is None:
        return False
    expected_number = _numeric(expected) if expected is not None else None
    return expected_number is None or abs(number - expected_number) <= FLOAT_EPSILON * max(1.0, abs(number))
