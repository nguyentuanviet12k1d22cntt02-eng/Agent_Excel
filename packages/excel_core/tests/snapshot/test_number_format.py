import pytest
from openpyxl.styles.numbers import BUILTIN_FORMATS

from excel_core.snapshot import SHORT_DATE, parse_number_format

# (mã, loại, số chữ số thập phân, dấu nghìn)
CASES = [
    ("General", "general", None, False),
    (None, "general", None, False),
    ("", "general", None, False),
    ("0", "number", 0, False),
    ("0.000", "number", 3, False),
    ("#,##0", "number", 0, True),
    ("#,##0.00", "number", 2, True),
    ("#,##0.00_);[Red](#,##0.00)", "number", 2, True),
    ("0,", "number", 0, False),  # dấu phẩy cuối là chia 1.000, không phải dấu nghìn
    ("#,##0,", "number", 0, True),
    ("0%", "percent", 0, False),
    ("0.00%", "percent", 2, False),
    ("0.00E+00", "scientific", 2, False),
    ("# ?/?", "fraction", 0, False),
    ("@", "text", None, False),
    # Comma Style: en-US và vi-VN (đọc bằng LCID 1033)
    ('_(* #,##0.00_);_(* \\(#,##0.00\\);_(* "-"??_);_(@_)', "accounting", 2, True),
    ('_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)', "accounting", 0, True),
    ('_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-', "accounting", 2, True),
    ('_("$"* #,##0.00_);_("$"* \\(#,##0.00\\);_("$"* "-"??_);_(@_)', "accounting", 2, True),
    # Tiền tệ
    ('"$"#,##0.00_);("$"#,##0.00)', "currency", 2, True),
    ('#,##0 "₫"', "currency", 0, True),
    ('#,##0 "đ"', "currency", 0, True),
    ("[$€-x-euro2] #,##0.00", "currency", 2, True),
    ('0 "kg"', "number", 0, False),
    ("[$-409]#,##0.00", "number", 2, True),  # [$-409] chỉ là mã vùng
    # Ngày giờ
    ("mm-dd-yy", "date", None, False),
    ("dd/mm/yyyy", "date", None, False),
    ("[$-42A]dd/mm/yyyy;@", "date", None, False),
    ("mmmm", "date", None, False),
    ("h:mm", "time", None, False),
    ("[h]:mm:ss", "time", None, False),
    ("mm:ss", "time", None, False),
    ('"Ngày" dd', "date", None, False),
]


@pytest.mark.parametrize(("code", "category", "decimals", "thousands"), CASES)
def test_parse_number_format(code: str | None, category: str, decimals: int | None, thousands: bool):
    info = parse_number_format(code)
    assert (info.category, info.decimals, info.thousands_separator) == (category, decimals, thousands)


@pytest.mark.parametrize("code", ["mm-dd-yy", "m/d/yyyy", "M/D/YYYY"])
def test_builtin_short_date_is_normalized_for_both_readers(code: str):
    # id 14: openpyxl đọc "mm-dd-yy", COM (LCID 1033) đọc "m/d/yyyy" (T2.1)
    assert parse_number_format(code).date_pattern == SHORT_DATE


def test_custom_date_pattern_keeps_order_without_locale_tag():
    assert parse_number_format("[$-42A]dd/mm/yyyy;@").date_pattern == "dd/mm/yyyy"


def test_every_builtin_format_has_a_known_category():
    expected = {
        0: "general",
        1: "number",
        4: "number",
        5: "currency",
        9: "percent",
        11: "scientific",
        12: "fraction",
        14: "date",
        18: "time",
        22: "date",
        41: "accounting",
        44: "accounting",
        46: "time",
        47: "time",
        48: "scientific",
        49: "text",
    }
    for builtin_id, code in BUILTIN_FORMATS.items():
        info = parse_number_format(code)
        assert info.category != "custom", f"id {builtin_id}: {code!r}"
        if builtin_id in expected:
            assert info.category == expected[builtin_id], f"id {builtin_id}: {code!r}"
