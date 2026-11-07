"""Bộ đọc workbook thành snapshot: openpyxl (T4.2), COM (T7.2).

`com_reader` không được import ở đây: nó cần pywin32, chỉ Desktop import khi chạy trên Windows.
"""

from excel_core.readers.openpyxl_reader import (
    EXERCISE_ID_PROPERTY,
    display_column_width,
    find_uncalculated_formulas,
    full_request,
    normalize_value,
    read_workbook,
    used_range,
)

__all__ = [
    "EXERCISE_ID_PROPERTY",
    "display_column_width",
    "find_uncalculated_formulas",
    "full_request",
    "normalize_value",
    "read_workbook",
    "used_range",
]
