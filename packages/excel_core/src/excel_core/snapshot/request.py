"""Yêu cầu đọc: đọc vùng nào, nhóm thuộc tính nào (docs/thiet-ke/snapshot.md mục 3).

Snapshot chụp theo phạm vi, không chụp cả workbook, vì đọc định dạng từng ô qua COM chậm (~2 ms/ô, T2.1).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from excel_core.address import parse_range


class PropertyGroup(StrEnum):
    VALUES = "values"  # giá trị, kiểu dữ liệu
    FORMULAS = "formulas"  # công thức A1 + R1C1
    NUMBER_FORMAT = "number_format"
    STYLE = "style"  # font, nền, viền, căn lề (chậm qua COM: chỉ vùng nhỏ)
    STRUCTURE = "structure"  # ô gộp, dòng/cột ẩn, kích thước
    FILTER = "filter"  # AutoFilter (theo sheet)
    PAGE_SETUP = "page_setup"  # hướng, khổ, lề, đầu/cuối trang (theo sheet; COM chậm)
    CHARTS = "charts"  # theo sheet


CELL_GROUPS = frozenset(
    {
        PropertyGroup.VALUES,
        PropertyGroup.FORMULAS,
        PropertyGroup.NUMBER_FORMAT,
        PropertyGroup.STYLE,
        PropertyGroup.STRUCTURE,
    }
)
SHEET_GROUPS = frozenset({PropertyGroup.FILTER, PropertyGroup.PAGE_SETUP, PropertyGroup.CHARTS})
ALL_GROUPS = CELL_GROUPS | SHEET_GROUPS


@dataclass(frozen=True)
class RangeRequest:
    sheet: str
    range: str  # một vùng liền kề, ví dụ "F10:F14"
    groups: frozenset[PropertyGroup]

    def __post_init__(self) -> None:
        parse_range(self.range)
        if not self.groups <= CELL_GROUPS:
            raise ValueError(
                f"Nhóm theo sheet không đặt trong RangeRequest: {set(self.groups - CELL_GROUPS)}"
            )


@dataclass(frozen=True)
class SheetRequest:
    sheet: str
    groups: frozenset[PropertyGroup]

    def __post_init__(self) -> None:
        if not self.groups <= SHEET_GROUPS:
            raise ValueError(f"Nhóm theo ô không đặt trong SheetRequest: {set(self.groups - SHEET_GROUPS)}")


@dataclass(frozen=True)
class ReadRequest:
    ranges: tuple[RangeRequest, ...] = ()
    sheets: tuple[SheetRequest, ...] = ()

    @property
    def sheet_names(self) -> tuple[str, ...]:
        """Các sheet được nhắc tới, theo thứ tự xuất hiện."""
        names = [r.sheet for r in self.ranges] + [s.sheet for s in self.sheets]
        return tuple(dict.fromkeys(names))

    def sheet_groups(self, sheet: str) -> frozenset[PropertyGroup]:
        groups: frozenset[PropertyGroup] = frozenset()
        for request in self.sheets:
            if request.sheet == sheet:
                groups |= request.groups
        return groups


def merge_requests(requests: Iterable[ReadRequest | RangeRequest | SheetRequest]) -> ReadRequest:
    """Gộp nhiều yêu cầu thành một: cùng sheet + cùng vùng thì gộp nhóm thuộc tính."""
    ranges: dict[tuple[str, str], frozenset[PropertyGroup]] = {}
    sheets: dict[str, frozenset[PropertyGroup]] = {}

    def add_range(request: RangeRequest) -> None:
        key = (request.sheet, str(parse_range(request.range)))
        ranges[key] = ranges.get(key, frozenset()) | request.groups

    def add_sheet(request: SheetRequest) -> None:
        sheets[request.sheet] = sheets.get(request.sheet, frozenset()) | request.groups

    for item in requests:
        if isinstance(item, RangeRequest):
            add_range(item)
        elif isinstance(item, SheetRequest):
            add_sheet(item)
        else:
            for r in item.ranges:
                add_range(r)
            for s in item.sheets:
                add_sheet(s)
    return ReadRequest(
        ranges=tuple(RangeRequest(sheet, rng, groups) for (sheet, rng), groups in ranges.items()),
        sheets=tuple(SheetRequest(sheet, groups) for sheet, groups in sheets.items()),
    )
