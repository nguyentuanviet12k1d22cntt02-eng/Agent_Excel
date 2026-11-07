"""page_setup, header_footer, chart, printed_to_pdf, observation_only."""

import pytest

from excel_core.checks import CheckStatus
from excel_core.snapshot import ChartInfo, ChartSeriesInfo, PageSetupInfo


def page(**changes) -> PageSetupInfo:
    values = {
        "orientation": "portrait",
        "paper_size": "A4",
        "margins_cm": (1.91, 1.91, 1.78, 1.78),
        "fit_to_pages": (None, None),
        "center_horizontally": False,
        "print_area": None,
        "header_footer": {},
    }
    return PageSetupInfo(**{**values, **changes})


# ---------------------------------------------------------------- page_setup
@pytest.mark.parametrize(
    ("setup", "code"),
    [
        (page(orientation="landscape", fit_to_pages=(1, None)), None),
        (page(fit_to_pages=(1, None)), "wrong_orientation"),
        (page(orientation="landscape", paper_size="letter"), "wrong_paper_size"),
        (page(orientation="landscape"), "wrong_fit"),
    ],
)
def test_page_setup(kit, setup: PageSetupInfo, code: str | None):
    check = {"type": "page_setup", "orientation": "landscape", "paper_size": "A4", "fit_to_pages_wide": 1}
    assert kit.run(check, kit.book(kit.sheet(page_setup=setup))).code == code


def test_page_setup_margins_and_print_area(kit):
    check = {"type": "page_setup", "margins_cm": {"left": 1.8, "right": 1.8}, "print_area": "B2:I22"}
    assert kit.run(check, kit.book(kit.sheet(page_setup=page(print_area="B2:I22")))).passed
    assert kit.run(check, kit.book(kit.sheet(page_setup=page()))).code == "wrong_print_area"
    wide = page(margins_cm=(1.91, 1.91, 2.5, 2.5), print_area="B2:I22")
    assert kit.run(check, kit.book(kit.sheet(page_setup=wide))).code == "wrong_margins"


# ---------------------------------------------------------------- header_footer
@pytest.mark.parametrize(
    ("parts", "code"),
    [
        ({"footer_center": "Trang &P / &N"}, None),
        ({"footer_right": "&P"}, "wrong_position"),
        ({}, "missing_page_number"),
    ],
)
def test_header_footer_page_number(kit, parts: dict[str, str], code: str | None):
    check = {"type": "header_footer", "position": "footer_center", "contains": "&P"}
    assert kit.run(check, kit.book(kit.sheet(page_setup=page(header_footer=parts)))).code == code


def test_header_footer_text(kit):
    check = {"type": "header_footer", "position": "header_left", "contains": "Bảng kê"}
    assert kit.run(check, kit.book(kit.sheet(page_setup=page()))).code == "missing_header_footer"


# ---------------------------------------------------------------- chart
def chart(kind: str = "column", title: str | None = "Số lượng bán", values: str = "S!F10:F14") -> ChartInfo:
    return ChartInfo(kind, title, (ChartSeriesInfo("S!F9", "S!D10:D14", values),))


@pytest.mark.parametrize(
    ("data_range", "passes"),
    [("F10:F14", True), ("F9:F14", True), ("D9:F14", True), ("D10:F14", True), ("F10:F13", False)],
)
def test_chart_data_range_variants(kit, data_range: str, passes: bool):
    check = {"type": "chart", "data_range": data_range}
    assert kit.run(check, kit.book(kit.sheet(charts=(chart(),)))).passed is passes


def test_chart_type_and_title(kit):
    check = {
        "type": "chart",
        "chart_types": ["column", "bar"],
        "has_title": True,
        "title_contains": "số lượng",
    }
    assert kit.run(check, kit.book(kit.sheet(charts=(chart(),)))).passed
    assert kit.run(check, kit.book(kit.sheet(charts=(chart("pie"),)))).code == "wrong_chart_type"
    assert kit.run(check, kit.book(kit.sheet(charts=(chart(title=None),)))).code == "missing_title"
    assert kit.run(check, kit.book(kit.sheet())).code == "missing_chart"


def test_chart_best_of_several(kit):
    check = {"type": "chart", "chart_types": ["line"]}
    assert kit.run(check, kit.book(kit.sheet(charts=(chart("pie"), chart("line"))))).passed


# ---------------------------------------------------------------- printed_to_pdf, observation_only
def test_printed_to_pdf_needs_live_event(kit):
    check = {"type": "printed_to_pdf"}
    assert kit.run(check, kit.book()).status == CheckStatus.NOT_EVALUABLE
    assert kit.run(check, kit.book(), printed_to_pdf=True).passed
    assert kit.run(check, kit.book(), printed_to_pdf=False).code == "not_printed"


def test_observation_only_needs_learner_confirmation(kit):
    check = {"type": "observation_only", "confirm_text": "Bạn đã xem kết quả lọc chưa?"}
    assert kit.run(check, kit.book()).status == CheckStatus.NOT_EVALUABLE
    assert kit.run(check, kit.book(), learner_confirmed=True).passed
    assert kit.run(check, kit.book(), learner_confirmed=False).code == "not_confirmed"
