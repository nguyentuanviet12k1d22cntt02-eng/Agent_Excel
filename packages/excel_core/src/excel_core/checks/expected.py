"""Giá trị kỳ vọng `expected` của điều kiện: từ file đáp án, từ vùng khác trong bài, hoặc ghi sẵn.

Mặc định lấy từ đáp án cùng bố cục; không ghi cứng số liệu trong kịch bản (T2.6: AI bịa số).
"""

from excel_core.address import CellRange, parse_range
from excel_core.checks.base import CheckContext, CheckSpec, CheckSpecError, Read, cell_read
from excel_core.snapshot import CellValue, PropertyGroup


def expected_reads(check: CheckSpec, sheet: str, group: PropertyGroup = PropertyGroup.VALUES) -> list[Read]:
    expected = check["expected"]
    match expected["from"]:
        case "solution":
            return [cell_read("solution", sheet, check["range"], group)]
        case "range":
            return [cell_read("current", expected.get("sheet") or sheet, expected["range"], group)]
        case _:
            return []


def expected_values(check: CheckSpec, target: CellRange, ctx: CheckContext) -> list[CellValue]:
    """Giá trị kỳ vọng cho từng ô của `target`, theo thứ tự từng dòng."""
    expected = check["expected"]
    match expected["from"]:
        case "literal":
            return [expected["value"]] * target.size
        case "solution":
            sheet = ctx.sheet(check, "solution")
            sheet.require(target, PropertyGroup.VALUES)
            return [sheet.cell(address).value for address in target.cells()]
        case "range":
            source = parse_range(expected["range"])
            if (source.width, source.height) != (target.width, target.height):
                raise CheckSpecError(f"Vùng kỳ vọng {source} khác kích thước vùng kiểm {target}")
            sheet = ctx.sheet(check, "current", expected.get("sheet") or ctx.sheet_name(check))
            sheet.require(source, PropertyGroup.VALUES)
            return [sheet.cell(address).value for address in source.cells()]
    raise CheckSpecError(f"Nguồn kỳ vọng không hỗ trợ: {expected!r}")
