"""Tách giáo trình PDF/DOCX thành mục theo tiêu đề (T5.4)."""

import pytest

from tutor_backend.ai.textbook_parser import TextbookParseError, heading_level, parse_docx, parse_pdf


@pytest.mark.parametrize(
    ("line", "level"),
    [
        ("Chương 3. Hàm thông dụng", 1),
        ("BÀI 22: HÀM TÍNH TỔNG", 2),
        ("1.2 Định dạng số", 2),
        ("2.3.1 Comma Style", 3),
        ("Hàm SUM tính tổng các số trong một vùng ô.", None),
        ("Bài tập này có rất nhiều chữ nên không thể là tiêu đề " * 3, None),
    ],
)
def test_heading_level(line: str, level: int | None):
    assert heading_level(line) == level


def test_parse_docx_follows_heading_styles_and_manual_headings(textbook_docx: bytes):
    sections = parse_docx(textbook_docx)
    headings = [s.heading for s in sections]
    assert "Chương 3. Hàm thông dụng > Bài 30. Hàm VLOOKUP" in headings
    # Tiêu đề gõ tay "BÀI 25: ..." (kiểu Normal) vẫn tách thành mục, cùng chương 3
    min_max = next(s for s in sections if s.heading.endswith("BÀI 25: HÀM MIN, MAX"))
    assert min_max.heading.startswith("Chương 3")
    assert "MAX | Giá trị lớn nhất" in min_max.text  # bảng giữ dạng dòng chữ


def test_parse_pdf_keeps_page_numbers(text_pdf):
    data = text_pdf(["Chuong 2. Dinh dang", "Bai 9. Dinh dang so", "Nut Comma Style them dau phan cach."])
    (section,) = parse_pdf(data)
    assert section.heading == "Chuong 2. Dinh dang > Bai 9. Dinh dang so"
    assert section.page == 1
    assert "Comma Style" in section.text


def test_pdf_without_text_is_rejected(text_pdf):
    with pytest.raises(TextbookParseError, match="không có chữ"):
        parse_pdf(text_pdf([]))


def test_broken_file_is_rejected():
    with pytest.raises(TextbookParseError):
        parse_docx(b"PK\x03\x04 khong phai docx")
