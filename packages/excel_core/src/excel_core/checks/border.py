"""border — viền theo cạnh (outline, inside, top...) và kiểu nét.

Một đường viền giữa hai ô có thể được Excel lưu ở ô bên này hoặc ô bên kia (cạnh dưới của ô trên, hay cạnh
trên của ô dưới), nên đọc rộng ra 1 ô quanh vùng và chấp nhận cả hai phía.
"""

from collections.abc import Iterator

from excel_core.address import MAX_COL, MAX_ROW, CellRange, cell_address
from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.snapshot import PropertyGroup, SheetSnapshot

TYPE = "border"
CODES = ("missing_border", "wrong_border_style")
# Kiểu trong kịch bản → các kiểu Excel tương ứng
STYLE_FAMILIES = {
    "thin": {"thin"},
    "medium": {"medium"},
    "thick": {"thick"},
    "double": {"double"},
    "dashed": {"dashed", "mediumDashed", "dashDot", "mediumDashDot", "dashDotDot", "mediumDashDotDot"},
    "dotted": {"dotted", "hair"},
}
_OPPOSITE = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}
_STEP = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}

type Edge = tuple[int, int, str]  # (cột, dòng, cạnh của ô đó)


def _expanded(rng: CellRange) -> CellRange:
    return CellRange(
        max(1, rng.min_col - 1),
        max(1, rng.min_row - 1),
        min(MAX_COL, rng.max_col + 1),
        min(MAX_ROW, rng.max_row + 1),
    )


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, _expanded(check_range(check)), PropertyGroup.STYLE)]


def _edges(rng: CellRange, side: str) -> Iterator[Edge]:
    if side in ("outline", "top"):
        yield from ((c, rng.min_row, "top") for c in rng.cols())
    if side in ("outline", "bottom"):
        yield from ((c, rng.max_row, "bottom") for c in rng.cols())
    if side in ("outline", "left"):
        yield from ((rng.min_col, r, "left") for r in rng.rows())
    if side in ("outline", "right"):
        yield from ((rng.max_col, r, "right") for r in rng.rows())
    if side in ("inside", "inside_horizontal"):
        yield from ((c, r, "bottom") for r in range(rng.min_row, rng.max_row) for c in rng.cols())
    if side in ("inside", "inside_vertical"):
        yield from ((c, r, "right") for c in range(rng.min_col, rng.max_col) for r in rng.rows())


def _edge_style(sheet: SheetSnapshot, col: int, row: int, side: str) -> str | None:
    """Kiểu nét của một đường viền, xét cả ô kề bên."""
    own = sheet.cell(cell_address(col, row)).border
    if own is not None and getattr(own, side):
        return getattr(own, side)
    dc, dr = _STEP[side]
    if 1 <= col + dc <= MAX_COL and 1 <= row + dr <= MAX_ROW:
        neighbour = sheet.cell(cell_address(col + dc, row + dr)).border
        if neighbour is not None:
            return getattr(neighbour, _OPPOSITE[side])
    return None


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.STYLE)
    style = check.get("style", "any")
    failures = Failures(CODES)
    for side in check["sides"]:
        for col, row, edge in _edges(target, side):
            found = _edge_style(sheet, col, row, edge)
            address = cell_address(col, row)
            if found in (None, "none"):
                failures.add("missing_border", address)
            elif style != "any" and found not in STYLE_FAMILIES.get(style, {style}):
                failures.add("wrong_border_style", address)
    return failures.result()
