"""Xử lý chữ tiếng Việt dùng chung cho RAG: bỏ dấu (truy vấn và tài liệu gõ không dấu vẫn khớp)."""

import unicodedata


def strip_accents(text: str) -> str:
    """Bỏ dấu: "Định dạng" thành "Dinh dang" (đ/Đ không phải dấu kết hợp nên đổi riêng)."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
