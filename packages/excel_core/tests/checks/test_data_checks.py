"""autofilter, visible_rows, sorted_by."""

import pytest

from excel_core.snapshot import AutoFilterInfo


# ---------------------------------------------------------------- autofilter
def filtered(kit, columns: dict[str, tuple[str, ...]] | None, rng: str = "B9:I28"):
    return kit.book(kit.sheet(autofilter=None if columns is None else AutoFilterInfo(rng, columns)))


def test_autofilter(kit):
    check = {"type": "autofilter", "range": "B9:I28", "column": "Đơn giá", "criteria": [">=5"]}
    assert kit.run(check, filtered(kit, {"Đơn giá": (">=5",)})).passed
    assert kit.run(check, filtered(kit, None)).code == "no_filter"
    assert kit.run(check, filtered(kit, {"Số lượng": (">=5",)})).code == "wrong_column"
    assert kit.run(check, filtered(kit, {"Đơn giá": (">5",)})).code == "wrong_criteria"


def test_autofilter_criteria_ignore_leading_equal_and_order(kit):
    check = {"type": "autofilter", "range": "B9:I28", "column": "Loại", "criteria": ["Bút", "Vở"]}
    assert kit.run(check, filtered(kit, {"Loại": ("=vở", "=bút")})).passed


def test_autofilter_on_other_table_does_not_count(kit):
    check = {"type": "autofilter", "range": "B9:I28"}
    assert kit.run(check, filtered(kit, {}, rng="K1:L5")).code == "no_filter"


# ---------------------------------------------------------------- visible_rows
def test_visible_rows_compares_with_solution(kit):
    check = {"type": "visible_rows", "range": "B9:I14", "expected": {"from": "solution"}}
    solution = kit.book(kit.sheet(hidden_rows=frozenset({11, 13})))
    assert kit.run(check, kit.book(kit.sheet(hidden_rows=frozenset({11, 13, 40}))), solution=solution).passed
    result = kit.run(check, kit.book(kit.sheet(hidden_rows=frozenset({11}))), solution=solution)
    assert (result.code, result.cells) == ("wrong_rows_visible", ("13",))


# ---------------------------------------------------------------- sorted_by
def people(kit, rows: list[tuple[str, float | None]]):
    cells = {"B4": kit.text("Họ tên"), "C4": kit.text("Điểm")}
    for i, (name, score) in enumerate(rows, start=5):
        cells[f"B{i}"] = kit.text(name)
        if score is not None:
            cells[f"C{i}"] = kit.number(score)
    return kit.book(cells)


STARTER_ROWS = [("An", 7), ("Bình", 9), ("Chi", 5)]


@pytest.mark.parametrize(
    ("rows", "order", "code"),
    [
        ([("Chi", 5), ("An", 7), ("Bình", 9)], "asc", None),
        ([("Bình", 9), ("An", 7), ("Chi", 5)], "asc", "wrong_order"),
        ([("An", 7), ("Bình", 9), ("Chi", 5)], "asc", "not_sorted"),
        ([("Bình", 9), ("An", 7), ("Chi", 5)], "desc", None),
        ([("An", 5), ("Bình", 7), ("Chi", 9)], "asc", "rows_broken"),  # chỉ sắp cột Điểm, lệch dòng
    ],
)
def test_sorted_by_score(kit, rows, order: str, code: str | None):
    check = {"type": "sorted_by", "range": "B4:C7", "key_column": "Điểm", "order": order}
    assert kit.run(check, people(kit, rows), starter=people(kit, STARTER_ROWS)).code == code


def test_sorted_by_vietnamese_names_and_blanks_last(kit):
    check = {"type": "sorted_by", "range": "B4:C8", "key_column": "Họ tên", "order": "asc"}
    rows = [("An", 1), ("Ánh", 2), ("Đức", 3), ("Dung", None)]
    # "Đức" và "Dung" cùng chữ cái gốc D: thứ tự giữa hai tên không bị bắt lỗi
    assert kit.run(check, people(kit, rows)).passed
    with_blank_first = kit.book({"B4": kit.text("Họ tên"), "C4": kit.text("Điểm"), "B6": kit.text("An")})
    assert kit.run(check, with_blank_first).code == "not_sorted"
