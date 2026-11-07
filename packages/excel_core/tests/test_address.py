import pytest

from excel_core.address import (
    AddressError,
    CellRange,
    column_index,
    column_letter,
    parse_cell,
    parse_cols,
    parse_range,
    parse_rows,
    split_sheet_reference,
)


@pytest.mark.parametrize(("letters", "index"), [("A", 1), ("Z", 26), ("AA", 27), ("AZ", 52), ("XFD", 16384)])
def test_column_letter_and_index_round_trip(letters: str, index: int):
    assert column_index(letters) == index
    assert column_letter(index) == letters


def test_parse_cell_ignores_dollar_signs():
    assert parse_cell("$F$10") == (6, 10)


def test_parse_range_normalizes_reversed_corners():
    rng = parse_range("F14:E10")
    assert (rng.min_col, rng.min_row, rng.max_col, rng.max_row) == (5, 10, 6, 14)
    assert str(rng) == "E10:F14"


def test_single_cell_range_prints_as_cell():
    assert str(parse_range("$H$10")) == "H10"


@pytest.mark.parametrize("bad", ["A1:A5,C1:C5", "Sheet1!A1", "A0", "1A", "A1:B2:C3", ""])
def test_parse_range_rejects_invalid(bad: str):
    with pytest.raises(AddressError):
        parse_range(bad)


def test_range_geometry():
    table = parse_range("B9:I14")
    assert (table.width, table.height, table.size) == (8, 6, 48)
    assert table.contains(parse_range("F10:F14"))
    assert not table.contains(parse_range("F10:F15"))
    assert table.intersects(parse_range("I14:J20"))
    assert not table.intersects(parse_range("J1:J100"))
    assert str(parse_range("C3").union(parse_range("A1"))) == "A1:C3"


def test_cells_are_listed_row_by_row():
    assert list(parse_range("A1:B2").cells()) == ["A1", "B1", "A2", "B2"]
    assert list(parse_range("A1:B2").row_cells()) == [["A1", "B1"], ["A2", "B2"]]


def test_rows_and_cols_ranges():
    assert list(parse_rows("7:5")) == [5, 6, 7]
    assert parse_cols("C:E") == ["C", "D", "E"]
    assert parse_cols("B") == ["B"]


def test_invalid_range_object_rejected():
    with pytest.raises(AddressError):
        CellRange(3, 1, 2, 1)


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("'Bài 01'!$G$10:$G$14", ("Bài 01", "G10:G14")),
        ("Sheet1!A1", ("Sheet1", "A1")),
        ("='It''s'!B2", ("It's", "B2")),
        ("$C$3", (None, "C3")),
    ],
)
def test_split_sheet_reference(reference: str, expected: tuple[str | None, str]):
    assert split_sheet_reference(reference) == expected
