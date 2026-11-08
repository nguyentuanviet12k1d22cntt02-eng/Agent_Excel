"""Chữ hiển thị gần đúng của ô trong lưới mô phỏng (T6.4)."""

from datetime import datetime

import pytest

from excel_core.snapshot import parse_number_format
from excel_core.snapshot.model import CellSnapshot, ErrorValue
from tutor_backend.services.sheet_preview import display_text, format_number


@pytest.mark.parametrize(
    ("value", "decimals", "thousands", "expected"),
    [
        (1234567.891, 2, True, "1.234.567,89"),
        (1250.0, 0, True, "1.250"),
        (999.0, 0, True, "999"),
        (-1234.5, 1, True, "-1.234,5"),
        (12.0, None, False, "12"),
        (0.125, None, False, "0,125"),
        (1 / 3, None, False, "0,3333333333"),
    ],
)
def test_format_number_vietnamese_style(value, decimals, thousands, expected):
    assert format_number(value, decimals, thousands) == expected


def cell(value, kind, code="General") -> CellSnapshot:
    return CellSnapshot(value=value, value_kind=kind, number_format=parse_number_format(code))


def test_display_text_follows_number_format_category():
    assert display_text(cell(0.125, "number", "0.0%")) == "12,5%"
    assert display_text(cell(3.5, "number", "#,##0.00")) == "3,50"
    assert display_text(cell(datetime(2026, 11, 8), "date", "dd/mm/yyyy")) == "08/11/2026"
    assert display_text(cell(True, "logical")) == "TRUE"
    assert display_text(cell(ErrorValue("#DIV/0!"), "error")) == "#DIV/0!"
    assert display_text(cell("Tổng", "text")) == "Tổng"
    assert display_text(CellSnapshot()) == ""
