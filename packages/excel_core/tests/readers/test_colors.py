import pytest
from openpyxl.styles import Color

from excel_core.readers.colors import apply_tint, resolve_color, theme_palette

# Giá trị Excel hiển thị trong bảng màu theme (Office 2013+)
TINT_CASES = [
    ("4472C4", 0.3999755851924192, "8EA9DB"),  # Blue, Accent 1, Lighter 40%
    ("4472C4", 0.5999938962981048, "B4C6E7"),  # Lighter 60%
    ("4472C4", 0.7999816888943144, "D9E1F2"),  # Lighter 80%
    ("4472C4", -0.249977111117893, "305496"),  # Darker 25%
    ("FFFFFF", -0.1499984740745262, "D9D9D9"),  # White, Darker 15%
    ("000000", 0.499984740745262, "808080"),  # Black, Lighter 50%
    ("ED7D31", 0.7999816888943144, "FBE5D6"),  # Orange, Accent 2, Lighter 80%
    ("70AD47", -0.499984740745262, "375623"),  # Green, Accent 6, Darker 50%
    ("4F81BD", 0.3999755851924192, "95B3D7"),  # theme Office 2007
]


@pytest.mark.parametrize(("rgb", "tint", "expected"), TINT_CASES)
def test_apply_tint_matches_excel_palette(rgb: str, tint: float, expected: str):
    got = apply_tint(rgb, tint)
    assert all(abs(int(got[i : i + 2], 16) - int(expected[i : i + 2], 16)) <= 1 for i in (0, 2, 4)), got


def test_default_palette_swaps_light_and_dark():
    palette = theme_palette(None)
    assert palette[0] == "FFFFFF"  # theme 0 = lt1
    assert palette[1] == "000000"  # theme 1 = dk1
    assert palette[4] == "4472C4"  # accent1


def test_resolve_color_kinds():
    palette = theme_palette(None)
    assert resolve_color(Color(rgb="FFC00000"), palette, None) == "#C00000"
    assert resolve_color(Color(theme=1), palette, None) == "#000000"
    assert resolve_color(Color(indexed=2), palette, None) == "#FF0000"
    assert resolve_color(Color(indexed=64), palette, "#000000") == "#000000"  # màu hệ thống "tự động"
    assert resolve_color(Color(auto=True), palette, "#000000") == "#000000"
    assert resolve_color(None, palette, None) is None
