import pytest

from excel_core.address import AddressError
from excel_core.snapshot import PropertyGroup, RangeRequest, ReadRequest, SheetRequest, merge_requests

V = PropertyGroup.VALUES
F = PropertyGroup.FORMULAS
NF = PropertyGroup.NUMBER_FORMAT


def test_merge_combines_groups_of_same_range():
    merged = merge_requests(
        [
            RangeRequest("S", "F10:F14", frozenset({V})),
            RangeRequest("S", "$F$10:$F$14", frozenset({NF})),
            RangeRequest("S", "H10:H14", frozenset({F})),
            SheetRequest("S", frozenset({PropertyGroup.PAGE_SETUP})),
            ReadRequest(sheets=(SheetRequest("S", frozenset({PropertyGroup.CHARTS})),)),
        ]
    )
    by_range = {r.range: r.groups for r in merged.ranges}
    assert by_range == {"F10:F14": {V, NF}, "H10:H14": {F}}
    assert merged.sheet_groups("S") == {PropertyGroup.PAGE_SETUP, PropertyGroup.CHARTS}
    assert merged.sheet_names == ("S",)


def test_range_request_rejects_sheet_level_groups():
    with pytest.raises(ValueError, match="theo sheet"):
        RangeRequest("S", "A1", frozenset({PropertyGroup.PAGE_SETUP}))


def test_sheet_request_rejects_cell_groups():
    with pytest.raises(ValueError, match="theo ô"):
        SheetRequest("S", frozenset({V}))


def test_range_request_rejects_multi_area_address():
    with pytest.raises(AddressError):
        RangeRequest("S", "A1:A5,C1:C5", frozenset({V}))
