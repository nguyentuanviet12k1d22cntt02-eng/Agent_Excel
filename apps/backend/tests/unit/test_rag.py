"""Tách từ tiếng Việt, cắt đoạn, xếp hạng BM25 (T5.4)."""

from tutor_backend.ai.rag import Bm25Index, chunk_sections, tokenize
from tutor_backend.ai.textbook_parser import Section
from tutor_backend.ai.vietnamese import strip_accents


def test_tokenize_adds_unaccented_forms_and_bigrams():
    tokens = tokenize("Hàm VLOOKUP dò tìm")
    assert {"hàm", "vlookup", "dò", "tìm"} <= set(tokens)
    assert {"ham", "do", "tim"} <= set(tokens)  # truy vấn gõ không dấu vẫn khớp
    assert "ham_vlookup" in tokens
    assert "và" not in tokenize("SUM và AVERAGE")  # từ dừng


def test_strip_accents_handles_d_stroke():
    assert strip_accents("Định dạng đường viền") == "Dinh dang duong vien"


def test_long_section_is_split_by_paragraph():
    long_text = "\n".join(f"Đoạn {i}: " + "chữ " * 60 for i in range(6))
    chunks = chunk_sections([Section("Bài 5", 3, long_text), Section("Bài 6", 4, "Ngắn.")])
    assert len(chunks) > 2
    assert all(len(content) <= 1400 for _, _, content in chunks)
    assert chunks[-1] == ("Bài 6", 4, "Ngắn.")


def test_bm25_ranks_matching_document_first():
    docs = [
        tokenize("Hàm SUM tính tổng"),
        tokenize("Hàm VLOOKUP dò tìm trong bảng"),
        tokenize("Định dạng số"),
    ]
    scores = Bm25Index(docs).scores(tokenize("vlookup"))
    assert scores.index(max(scores)) == 1
    assert scores[2] == 0
