"""Nhúng mã bài vào file đề mà không làm hỏng nội dung (T5.6)."""

import zipfile
from pathlib import Path

import openpyxl
import pytest

from excel_core.package_props import PackageError, set_custom_properties
from excel_core.readers import EXERCISE_ID_PROPERTY, find_uncalculated_formulas, read_workbook


def custom_props(path: Path) -> dict[str, str]:
    return {p.name: p.value for p in openpyxl.load_workbook(path).custom_doc_props.props}


def test_embeds_exercise_id_and_keeps_everything_else(tmp_path: Path, b22_files):
    _, solution = b22_files
    target = tmp_path / "phat-hanh.xlsx"
    set_custom_properties(
        solution, target, {EXERCISE_ID_PROPERTY: "b22-ham-tinh-tong", "tutor_script_revision": "3"}
    )
    assert custom_props(target) == {EXERCISE_ID_PROPERTY: "b22-ham-tinh-tong", "tutor_script_revision": "3"}
    assert read_workbook(target).exercise_id == "b22-ham-tinh-tong"
    assert find_uncalculated_formulas(target) == []  # giá trị công thức Excel đã tính vẫn còn
    with zipfile.ZipFile(solution) as before, zipfile.ZipFile(target) as after:
        for name in before.namelist():
            if name not in ("[Content_Types].xml", "_rels/.rels"):
                assert before.read(name) == after.read(name), name


def test_overwrites_existing_property_without_duplicating(tmp_path: Path, b22_files):
    starter, _ = b22_files
    first, second = tmp_path / "1.xlsx", tmp_path / "2.xlsx"
    set_custom_properties(starter, first, {EXERCISE_ID_PROPERTY: "cu"})
    set_custom_properties(first, second, {EXERCISE_ID_PROPERTY: "moi", "khac": "x"})
    assert custom_props(second) == {EXERCISE_ID_PROPERTY: "moi", "khac": "x"}
    with zipfile.ZipFile(second) as package:
        rels = package.read("_rels/.rels").decode("utf-8")
        assert rels.count("custom-properties") == 1


def test_rejects_non_office_file(tmp_path: Path):
    bad = tmp_path / "x.xlsx"
    bad.write_bytes(b"khong phai zip")
    with pytest.raises(PackageError):
        set_custom_properties(bad, tmp_path / "y.xlsx", {"a": "b"})
