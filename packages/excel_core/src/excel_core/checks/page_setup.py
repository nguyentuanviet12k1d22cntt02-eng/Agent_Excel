"""page_setup — hướng giấy, khổ giấy, lề, ép vừa trang, căn giữa ngang, vùng in.

COM đọc PageSetup chậm (gọi driver máy in, T2.3): Desktop chỉ đọc khi bước hiện tại cần.
"""

from excel_core.address import parse_range
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, sheet_read
from excel_core.snapshot import PageSetupInfo, PropertyGroup

TYPE = "page_setup"
CODES = (
    "wrong_orientation",
    "wrong_paper_size",
    "wrong_margins",
    "wrong_fit",
    "wrong_centering",
    "wrong_print_area",
)
DEFAULT_MARGIN_TOLERANCE_CM = 0.1
_MARGIN_INDEX = {"top": 0, "bottom": 1, "left": 2, "right": 3}


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [sheet_read("current", sheet, PropertyGroup.PAGE_SETUP)]


def _margins_ok(info: PageSetupInfo, wanted: dict) -> bool:  # type: ignore[type-arg]
    tolerance = float(wanted.get("tolerance", DEFAULT_MARGIN_TOLERANCE_CM))
    return all(
        abs(info.margins_cm[index] - float(wanted[side])) <= tolerance
        for side, index in _MARGIN_INDEX.items()
        if side in wanted
    )


def _first_problem(info: PageSetupInfo, check: CheckSpec) -> str | None:
    if "orientation" in check and info.orientation != check["orientation"]:
        return "wrong_orientation"
    if "paper_size" in check and (info.paper_size or "").casefold() != check["paper_size"].casefold():
        return "wrong_paper_size"
    if "margins_cm" in check and not _margins_ok(info, check["margins_cm"]):
        return "wrong_margins"
    wide, tall = info.fit_to_pages
    if ("fit_to_pages_wide" in check and wide != check["fit_to_pages_wide"]) or (
        "fit_to_pages_tall" in check and tall != check["fit_to_pages_tall"]
    ):
        return "wrong_fit"
    if "center_horizontally" in check and info.center_horizontally != check["center_horizontally"]:
        return "wrong_centering"
    if "print_area" in check and (
        info.print_area is None or parse_range(info.print_area) != parse_range(check["print_area"])
    ):
        return "wrong_print_area"
    return None


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    sheet = ctx.sheet(check)
    sheet.require_sheet_group(PropertyGroup.PAGE_SETUP)
    if sheet.page_setup is None:
        return CheckResult.fail(CODES[0], detail="không đọc được thiết lập trang")
    code = _first_problem(sheet.page_setup, check)
    return CheckResult.fail(code) if code else CheckResult.ok()
