"""number_format, alignment, font, fill, border, merged."""

import pytest

from excel_core.snapshot import (
    AlignmentInfo,
    BorderInfo,
    CellSnapshot,
    FillInfo,
    FontInfo,
    parse_number_format,
)

COMMA_2 = '_(* #,##0.00_);_(* \\(#,##0.00\\);_(* "-"??_);_(@_)'
COMMA_0 = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'


# ---------------------------------------------------------------- number_format
@pytest.mark.parametrize(
    ("fmt", "code"),
    [
        (COMMA_0, None),
        ("#,##0", None),
        (COMMA_2, "wrong_decimals"),  # b09: bấm Comma Style mà chưa giảm số lẻ
        ("0", "missing_separator"),
        ("General", "wrong_category"),
        ("0%", "wrong_category"),
    ],
)
def test_number_format_quantity_column(kit, fmt: str, code: str | None):
    # b09 bước 2: Số lượng là số nguyên, có dấu nghìn
    check = {
        "type": "number_format",
        "range": "F10",
        "categories": ["number", "accounting"],
        "decimals": 0,
        "thousands_separator": True,
    }
    assert kit.run(check, kit.book({"F10": kit.number(1250, fmt)})).code == code


def test_number_format_unexpected_separator(kit):
    check = {"type": "number_format", "range": "I10", "decimals": 3, "thousands_separator": False}
    assert kit.run(check, kit.book({"I10": kit.number(0.05, "#,##0.000")})).code == "unexpected_separator"
    assert kit.run(check, kit.book({"I10": kit.number(0.05, "0.000")})).passed


def test_number_format_date_pattern(kit):
    check = {"type": "number_format", "range": "B9", "categories": ["date"], "date_pattern": "dd/mm/yyyy"}
    assert kit.run(check, kit.book({"B9": kit.number(46327, "dd/mm/yyyy")})).passed
    assert kit.run(check, kit.book({"B9": kit.number(46327, "mm-dd-yy")})).code == "wrong_date_pattern"


def test_number_format_unformatted_cell_counts_as_general(kit):
    check = {"type": "number_format", "range": "F10", "decimals": 2}
    assert kit.run(check, kit.book({})).code == "wrong_decimals"


# ---------------------------------------------------------------- alignment
def aligned(kit, value: CellSnapshot | None, horizontal: str = "general", wrap: bool = False) -> CellSnapshot:
    base = value or CellSnapshot()
    return CellSnapshot(
        value=base.value, value_kind=base.value_kind, alignment=AlignmentInfo(horizontal, "bottom", wrap)
    )


def test_alignment_general_number_counts_as_right(kit):
    # T2.6: Excel tự căn phải số. Kiểm theo căn lề người học nhìn thấy
    check = {"type": "alignment", "range": "F10", "horizontal": ["right"]}
    assert kit.run(check, kit.book({"F10": aligned(kit, kit.number(5))})).passed
    assert kit.run(check, kit.book({"F10": aligned(kit, kit.number(5), "right")})).passed


def test_alignment_empty_general_cell_is_not_right(kit):
    # Nhờ vậy bước "căn phải" không đạt sẵn trên file đề còn trống (tự kiểm tầng 3)
    check = {"type": "alignment", "range": "F10", "horizontal": ["right"]}
    assert kit.run(check, kit.book({"F10": aligned(kit, None)})).code == "wrong_alignment"


def test_alignment_general_text_is_left(kit):
    check = {"type": "alignment", "range": "B9", "horizontal": ["center"]}
    assert kit.run(check, kit.book({"B9": aligned(kit, kit.text("STT"))})).code == "wrong_alignment"
    assert kit.run(check, kit.book({"B9": aligned(kit, kit.text("STT"), "center")})).passed


def test_alignment_wrap_text(kit):
    check = {"type": "alignment", "range": "B9", "wrap_text": True}
    assert kit.run(check, kit.book({"B9": aligned(kit, kit.text("Tiêu đề dài"))})).code == "not_wrapped"
    assert kit.run(check, kit.book({"B9": aligned(kit, kit.text("Tiêu đề dài"), wrap=True)})).passed


# ---------------------------------------------------------------- font
def styled(font: FontInfo | None = None, fill: str | None = None, border: BorderInfo | None = None):
    return CellSnapshot(font=font, fill=FillInfo(fill), border=border or BorderInfo())


def test_font_checks_only_listed_attributes(kit):
    check = {"type": "font", "range": "B9", "bold": True, "size": 12}
    bold_12 = FontInfo("Arial", 12, True, False, False, "#FF0000")
    assert kit.run(check, kit.book({"B9": styled(bold_12)})).passed
    not_bold = FontInfo("Arial", 12, False, False, False, "#000000")
    assert kit.run(check, kit.book({"B9": styled(not_bold)})).code == "wrong_font"


def test_font_color_has_tolerance(kit):
    check = {"type": "font", "range": "B9", "color": "#C00000"}
    near = FontInfo("Calibri", 11, False, False, False, "#C10101")
    assert kit.run(check, kit.book({"B9": styled(near)})).passed


# ---------------------------------------------------------------- fill
def test_fill_any_and_specific(kit):
    assert kit.run(
        {"type": "fill", "range": "B9", "color": "any"}, kit.book({"B9": styled(fill="#FFFF00")})
    ).passed
    assert (
        kit.run({"type": "fill", "range": "B9", "color": "any"}, kit.book({"B9": styled()})).code == "no_fill"
    )
    check = {"type": "fill", "range": "B9", "color": "#FFFF00"}
    assert kit.run(check, kit.book({"B9": styled(fill="#00B0F0")})).code == "wrong_fill"


# ---------------------------------------------------------------- border
def boxed(kit, rng_cells: list[str], **sides) -> dict[str, CellSnapshot]:
    return {a: styled(border=BorderInfo(**sides)) for a in rng_cells}


def test_border_all_sides_thin(kit):
    cells = ["B9", "C9", "B10", "C10"]
    current = kit.book(boxed(kit, cells, top="thin", bottom="thin", left="thin", right="thin"))
    check = {"type": "border", "range": "B9:C10", "sides": ["outline", "inside"], "style": "thin"}
    assert kit.run(check, current).passed
    check_double = {**check, "style": "double"}
    assert kit.run(check_double, current).code == "wrong_border_style"


def test_border_edge_stored_on_neighbour_cell(kit):
    # Viền trên của B9 có thể được Excel lưu thành viền dưới của B8
    current = kit.book({"B8": styled(border=BorderInfo(bottom="medium")), "B9": styled()})
    assert kit.run({"type": "border", "range": "B9", "sides": ["top"]}, current).passed
    assert kit.run({"type": "border", "range": "B9", "sides": ["bottom"]}, current).code == "missing_border"


def test_border_dashed_family(kit):
    current = kit.book({"B9": styled(border=BorderInfo(top="mediumDashed"))})
    assert kit.run({"type": "border", "range": "B9", "sides": ["top"], "style": "dashed"}, current).passed


# ---------------------------------------------------------------- merged
def test_merged_requires_exact_range(kit):
    check = {"type": "merged", "range": "B2:I2"}
    assert kit.run(check, kit.book(kit.sheet(merged=("B2:I2",)))).passed
    result = kit.run(check, kit.book(kit.sheet(merged=("B2:H2",))))
    assert (result.code, result.detail) == ("not_merged", "đang gộp: B2:H2")


def test_number_format_info_parsed_once():
    assert parse_number_format(COMMA_0) is parse_number_format(COMMA_0)
