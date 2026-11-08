"""Schema xem trước trang tính (openapi.yaml: SheetPreview, T6.4)."""

from typing import Literal

from pydantic import BaseModel


class PreviewCell(BaseModel):
    address: str  # "F10"
    text: str  # chữ hiển thị gần đúng
    formula: str | None = None
    bold: bool = False
    italic: bool = False
    color: str | None = None  # màu chữ khác đen, "#RRGGBB"
    fill: str | None = None  # màu nền
    align: str | None = None  # căn ngang khác General
    number: bool = False  # số/ngày: mặc định căn phải như Excel
    wrap: bool = False


class SheetPreview(BaseModel):
    sheet: str
    sheet_names: list[str]
    range: str  # vùng hiện, luôn bắt đầu từ A1
    rows: int
    cols: int
    truncated: bool  # trang tính lớn hơn vùng hiện
    cells: list[PreviewCell]  # chỉ ô có nội dung hoặc định dạng đáng kể
    merged: list[str]
    col_widths: dict[str, float]  # số ký tự như Excel
    row_heights: dict[int, float]  # điểm
    hidden_rows: list[int]
    hidden_cols: list[str]


PreviewFile = Literal["starter", "solution"]
