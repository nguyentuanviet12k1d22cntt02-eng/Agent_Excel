"""Quy đổi màu của openpyxl (rgb / theme + tint / indexed) về "#RRGGBB".

COM trả màu đã quy đổi sẵn; openpyxl chỉ cho chỉ số màu theme và độ sáng (tint), nên phải tự tính theo
bảng màu theme lưu trong file. Kết quả có thể lệch ±1 mỗi kênh so với Excel: điều kiện so màu có ngưỡng.
"""

import colorsys
import xml.etree.ElementTree as ET
from collections.abc import Sequence

from openpyxl.styles.colors import COLOR_INDEX

_DRAWING_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
# Thứ tự trong file theme: dk1, lt1, dk2, lt2, accent1–6, hlink, folHlink
_SCHEME_ORDER = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6")
# Theme Office 2013+, dùng khi file không có theme
_OFFICE_THEME = (
    "000000",
    "FFFFFF",
    "44546A",
    "E7E6E6",
    "4472C4",
    "ED7D31",
    "A5A5A5",
    "FFC000",
    "5B9BD5",
    "70AD47",
)
_SYSTEM_FOREGROUND = 64  # chỉ số màu "tự động"
_HLS_MAX = 255


def theme_palette(theme_xml: bytes | None) -> tuple[str, ...]:
    """Bảng màu theo **chỉ số theme của ô**: Excel đảo cặp đầu (0 = lt1, 1 = dk1, 2 = lt2, 3 = dk2)."""
    colors = dict(zip(_SCHEME_ORDER, _OFFICE_THEME, strict=True))
    if theme_xml:
        scheme = ET.fromstring(theme_xml).find(f".//{_DRAWING_NS}clrScheme")
        if scheme is not None:
            for name in _SCHEME_ORDER:
                node = scheme.find(f"{_DRAWING_NS}{name}")
                if node is None or len(node) == 0:
                    continue
                child = node[0]
                value = child.get("val") if child.tag.endswith("srgbClr") else child.get("lastClr")
                if value:
                    colors[name] = value.upper()
    ordered = [colors["lt1"], colors["dk1"], colors["lt2"], colors["dk2"]]
    ordered += [colors[f"accent{i}"] for i in range(1, 7)]
    return tuple(ordered)


def apply_tint(rgb: str, tint: float) -> str:
    """Làm sáng/tối màu theo tint của Excel: tính trên độ sáng HLS thang nguyên 0–255 như Excel."""
    if not tint:
        return rgb
    r, g, b = (int(rgb[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, lum, s = (round(v * _HLS_MAX) for v in colorsys.rgb_to_hls(r, g, b))
    lum = lum * (1 + tint) if tint < 0 else lum * (1 - tint) + (_HLS_MAX - _HLS_MAX * (1 - tint))
    r, g, b = colorsys.hls_to_rgb(h / _HLS_MAX, round(lum) / _HLS_MAX, s / _HLS_MAX)
    return "".join(f"{round(c * 255):02X}" for c in (r, g, b))


def resolve_color(color: object, palette: Sequence[str], default: str | None) -> str | None:
    """Màu openpyxl → "#RRGGBB"; màu tự động hoặc không đọc được → `default`."""
    # Thuộc tính chưa đặt của Color trả về chuỗi mô tả lỗi (khác rỗng), nên phải so `is True`
    if color is None or getattr(color, "auto", None) is True:
        return default
    kind = getattr(color, "type", None)
    rgb: str | None = None
    if kind == "rgb" and isinstance(color.rgb, str) and len(color.rgb) in (6, 8):  # type: ignore[attr-defined]
        rgb = color.rgb[-6:]  # type: ignore[attr-defined]
    elif kind == "theme" and isinstance(color.theme, int) and 0 <= color.theme < len(palette):  # type: ignore[attr-defined]
        rgb = apply_tint(palette[color.theme], float(color.tint or 0))  # type: ignore[attr-defined]
    elif kind == "indexed" and isinstance(color.indexed, int):  # type: ignore[attr-defined]
        if color.indexed >= _SYSTEM_FOREGROUND or color.indexed >= len(COLOR_INDEX):  # type: ignore[attr-defined]
            return default
        rgb = COLOR_INDEX[color.indexed][-6:]  # type: ignore[attr-defined]
    return f"#{rgb.upper()}" if rgb else default
