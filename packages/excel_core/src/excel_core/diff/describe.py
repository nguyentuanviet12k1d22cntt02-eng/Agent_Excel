"""Mô tả ngắn bằng tiếng Việt cho từng thay đổi (đọc được cho cả giảng viên và LLM)."""

import dataclasses
from datetime import datetime

from excel_core.snapshot import AlignmentInfo, BorderInfo, CellSnapshot, FontInfo, NumberFormatInfo

_KIND_NAMES = {
    "empty": "trống",
    "number": "số",
    "text": "chữ",
    "logical": "đúng/sai",
    "date": "ngày",
    "error": "lỗi",
}


def describe_value(cell: CellSnapshot) -> str:
    """Loại giá trị, không kèm số liệu: diff là khung cho AI, không để AI chép số (T2.6 AI bịa số)."""
    return _KIND_NAMES.get(cell.value_kind, cell.value_kind)


def describe_number_format(info: NumberFormatInfo) -> str:
    parts = [info.category]
    if info.decimals is not None:
        parts.append(f"{info.decimals} số lẻ")
    if info.thousands_separator:
        parts.append("dấu nghìn")
    if info.date_pattern:
        parts.append(info.date_pattern)
    return f"{info.code} ({', '.join(parts)})"


def describe_font(font: FontInfo) -> str:
    styles = [
        name
        for name, on in (("đậm", font.bold), ("nghiêng", font.italic), ("gạch chân", font.underline))
        if on
    ]
    return " ".join([f"{font.name} {font.size:g}", *styles, font.color])


def describe_border(border: BorderInfo) -> str:
    sides = [
        f"{side}={style}" for side in ("top", "bottom", "left", "right") if (style := getattr(border, side))
    ]
    return ", ".join(sides) or "không viền"


def describe_alignment(alignment: AlignmentInfo) -> str:
    text = f"ngang={alignment.horizontal}, dọc={alignment.vertical}"
    return text + (", xuống dòng" if alignment.wrap_text else "")


def _plain(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, tuple | list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def object_changes(before: object, after: object) -> list[tuple[str, str]]:
    """So hai đối tượng theo sheet (bộ lọc, trang in, danh sách biểu đồ); mỗi trường khác nhau một cặp."""
    if before == after:
        return []
    if before is None or after is None or not dataclasses.is_dataclass(after):
        return [(_text(before), _text(after))]
    changes = []
    for field in dataclasses.fields(after):  # type: ignore[arg-type]
        old, new = getattr(before, field.name), getattr(after, field.name)
        if old != new:
            changes.append((f"{field.name}={_text(old)}", f"{field.name}={_text(new)}"))
    return changes


def _text(value: object) -> str:
    if value is None:
        return "không có"
    if isinstance(value, tuple) and not value:
        return "không có"
    return str(_plain(value))
