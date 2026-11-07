"""Kiểu dữ liệu snapshot workbook (thiết kế: docs/thiet-ke/snapshot.md mục 4).

Hai bộ đọc (openpyxl, COM) cùng trả ra các kiểu này, đã chuẩn hóa; `checks/` chỉ làm việc với chúng.
Mọi lớp đều bất biến (`frozen`). Các trường kiểu `Mapping` là `dict` thường: không sửa sau khi tạo.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from excel_core.address import CellRange, parse_range
from excel_core.snapshot.request import PropertyGroup

ValueKind = Literal["empty", "number", "text", "logical", "date", "error"]
NumberCategory = Literal[
    "general",
    "number",
    "currency",
    "accounting",
    "percent",
    "date",
    "time",
    "text",
    "scientific",
    "fraction",
    "custom",
]


class SnapshotMissingError(LookupError):
    """Điều kiện cần dữ liệu mà yêu cầu đọc không có: lỗi lập trình, không phải "không đạt"."""


@dataclass(frozen=True)
class ErrorValue:
    """Giá trị lỗi của ô, ví dụ "#DIV/0!"."""

    code: str


type CellValue = None | float | str | bool | datetime | ErrorValue


@dataclass(frozen=True)
class NumberFormatInfo:
    """Định dạng số đã phân tích theo ý nghĩa (`parse_number_format`)."""

    code: str  # mã en-US, ví dụ "#,##0.00"
    category: NumberCategory
    decimals: int | None
    thousands_separator: bool
    date_pattern: str | None = None  # "short_date" cho định dạng ngày dựng sẵn


@dataclass(frozen=True)
class FontInfo:
    name: str
    size: float
    bold: bool
    italic: bool
    underline: bool
    color: str  # "#RRGGBB"; màu tự động quy về "#000000"


@dataclass(frozen=True)
class FillInfo:
    color: str | None  # None = không tô


@dataclass(frozen=True)
class BorderInfo:
    """Kiểu viền từng cạnh: "thin", "medium", "thick", "double", "dashed", "dotted"... None = không có."""

    top: str | None = None
    bottom: str | None = None
    left: str | None = None
    right: str | None = None


@dataclass(frozen=True)
class AlignmentInfo:
    horizontal: str  # general | left | center | right | justify | center_across | fill | distributed
    vertical: str  # top | center | bottom | justify | distributed
    wrap_text: bool


@dataclass(frozen=True)
class CellSnapshot:
    """Một ô. Trường thuộc nhóm thuộc tính không được đọc thì là None."""

    value: CellValue = None
    value_kind: ValueKind = "empty"
    formula: str | None = None  # "=SUM(C9:E9)", cú pháp tiếng Anh
    formula_r1c1: str | None = None  # "=SUM(RC[-3]:RC[-1])", đã chuẩn hóa
    number_format: NumberFormatInfo | None = None
    font: FontInfo | None = None
    fill: FillInfo | None = None
    border: BorderInfo | None = None
    alignment: AlignmentInfo | None = None

    @property
    def is_formula(self) -> bool:
        return self.formula is not None

    @property
    def is_empty(self) -> bool:
        return self.value_kind == "empty" and self.formula is None


EMPTY_CELL = CellSnapshot()


@dataclass(frozen=True)
class AutoFilterInfo:
    range: str  # vùng bộ lọc, gồm dòng tiêu đề
    columns: Mapping[str, tuple[str, ...]]  # tiêu đề cột → tiêu chí (đã bỏ dấu "=" đầu)


@dataclass(frozen=True)
class PageSetupInfo:
    orientation: Literal["portrait", "landscape"]
    paper_size: str | None  # "A4", "A3", "A5", "letter", "legal"; None = file không ghi
    margins_cm: tuple[float, float, float, float]  # trên, dưới, trái, phải
    fit_to_pages: tuple[int | None, int | None]  # (rộng, cao); None = không ép số trang
    center_horizontally: bool
    print_area: str | None  # "A1:H20"
    header_footer: Mapping[str, str]  # "header_center" → "Trang &P"


@dataclass(frozen=True)
class ChartSeriesInfo:
    """Tham chiếu của một chuỗi dữ liệu, dạng "Tên sheet!G10:G14" (không $, không nháy)."""

    name_ref: str | None
    categories_ref: str | None
    values_ref: str | None


@dataclass(frozen=True)
class ChartInfo:
    chart_type: str  # column | bar | line | pie | doughnut | area | scatter | other
    title: str | None
    series: tuple[ChartSeriesInfo, ...]

    @property
    def data_ranges(self) -> tuple[str, ...]:
        refs = []
        for s in self.series:
            refs += [r for r in (s.name_ref, s.categories_ref, s.values_ref) if r]
        return tuple(refs)


@dataclass(frozen=True)
class RangeRead:
    """Vùng đã đọc và các nhóm thuộc tính đã đọc trên vùng đó."""

    range: str
    groups: frozenset[PropertyGroup]


@dataclass(frozen=True)
class SheetSnapshot:
    name: str
    cells: Mapping[str, CellSnapshot] = field(default_factory=dict)  # khóa "F10"; ô trống có thể vắng mặt
    read_ranges: tuple[RangeRead, ...] = ()
    sheet_groups: frozenset[PropertyGroup] = frozenset()  # FILTER / PAGE_SETUP / CHARTS đã đọc
    merged: tuple[str, ...] = ()
    hidden_rows: frozenset[int] = frozenset()
    hidden_cols: frozenset[str] = frozenset()
    row_heights: Mapping[int, float] = field(default_factory=dict)  # điểm (pt)
    col_widths: Mapping[str, float] = field(default_factory=dict)  # số ký tự như Excel hiển thị
    autofilter: AutoFilterInfo | None = None
    page_setup: PageSetupInfo | None = None
    charts: tuple[ChartInfo, ...] = ()

    def has_read(self, cell_range: CellRange, group: PropertyGroup) -> bool:
        return any(
            group in read.groups and parse_range(read.range).contains(cell_range) for read in self.read_ranges
        )

    def require(self, cell_range: CellRange | str, group: PropertyGroup) -> CellRange:
        """Bảo đảm vùng đã được đọc với nhóm thuộc tính này; trả về vùng đã phân tích."""
        rng = parse_range(cell_range) if isinstance(cell_range, str) else cell_range
        if not self.has_read(rng, group):
            raise SnapshotMissingError(f"Sheet {self.name!r}: vùng {rng} chưa đọc nhóm {group.value}")
        return rng

    def require_sheet_group(self, group: PropertyGroup) -> None:
        if group not in self.sheet_groups:
            raise SnapshotMissingError(f"Sheet {self.name!r}: chưa đọc nhóm {group.value}")

    def cell(self, address: str) -> CellSnapshot:
        """Ô theo địa chỉ "F10"; ô không có trong snapshot là ô trống."""
        return self.cells.get(address, EMPTY_CELL)

    def iter_cells(self, cell_range: CellRange) -> Iterator[tuple[str, CellSnapshot]]:
        for address in cell_range.cells():
            yield address, self.cell(address)

    def is_row_hidden(self, row: int) -> bool:
        return row in self.hidden_rows


@dataclass(frozen=True)
class WorkbookSnapshot:
    source: Literal["openpyxl", "com"]
    taken_at: datetime
    exercise_id: str | None  # thuộc tính tùy chỉnh tutor_exercise_id
    sheet_names: tuple[str, ...]
    active_sheet: str | None
    sheets: Mapping[str, SheetSnapshot]  # chỉ các sheet có trong yêu cầu đọc

    def sheet(self, name: str) -> SheetSnapshot:
        try:
            return self.sheets[name]
        except KeyError:
            if name not in self.sheet_names:
                raise SnapshotMissingError(f"Workbook không có sheet {name!r}") from None
            raise SnapshotMissingError(f"Sheet {name!r} chưa được đọc") from None

    def has_sheet(self, name: str) -> bool:
        return name in self.sheet_names
