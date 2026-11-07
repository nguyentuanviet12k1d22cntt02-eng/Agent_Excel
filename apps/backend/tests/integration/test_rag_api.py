"""Lập chỉ mục giáo trình và tìm đoạn liên quan qua API (T5.4: "hàm VLOOKUP" trả về đúng mục)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tutor_backend.models import User


def upload(client: TestClient, headers, data: bytes, name: str, title: str = "Giáo trình Excel"):
    return client.post(
        "/api/v1/textbooks", data={"title": title}, files={"file": (name, data)}, headers=headers
    )


@pytest.fixture
def indexed(client: TestClient, make_user: Callable[..., User], auth, textbook_docx: bytes):
    teacher = make_user("teacher")
    headers = auth(teacher)
    textbook = upload(client, headers, textbook_docx, "giao-trinh.docx").json()
    return headers, textbook


def test_upload_indexes_textbook(indexed):
    _, textbook = indexed
    assert textbook["status"] == "ready"
    assert textbook["chunk_count"] >= 6


@pytest.mark.parametrize("query", ["hàm VLOOKUP", "ham vlookup", "dò tìm giá trị trong bảng"])
def test_search_finds_vlookup_section(client: TestClient, indexed, query: str):
    headers, _ = indexed
    hits = client.get("/api/v1/textbooks/search", params={"q": query}, headers=headers).json()
    assert hits, "không tìm thấy đoạn nào"
    assert hits[0]["heading"] == "Chương 3. Hàm thông dụng > Bài 30. Hàm VLOOKUP"
    assert hits[0]["textbook_title"] == "Giáo trình Excel"


def test_search_can_be_limited_to_some_textbooks(
    client: TestClient, indexed, text_pdf, make_user: Callable[..., User], auth
):
    headers, docx_book = indexed
    pdf_book = upload(
        client, headers, text_pdf(["Bai 40. Ham VLOOKUP nang cao", "VLOOKUP ket hop IFERROR."]), "b.pdf"
    )
    only_pdf = client.get(
        "/api/v1/textbooks/search",
        params={"q": "vlookup", "textbook_ids": [pdf_book.json()["id"]]},
        headers=headers,
    ).json()
    assert {hit["textbook_id"] for hit in only_pdf} == {pdf_book.json()["id"]}
    both = client.get(
        "/api/v1/textbooks/search", params={"q": "vlookup", "limit": 10}, headers=headers
    ).json()
    assert {hit["textbook_id"] for hit in both} == {docx_book["id"], pdf_book.json()["id"]}


def test_pdf_without_text_fails_with_reason(
    client: TestClient, make_user: Callable[..., User], auth, text_pdf
):
    response = upload(client, auth(make_user("teacher")), text_pdf([]), "scan.pdf")
    body = response.json()
    assert (body["status"], body["chunk_count"]) == ("failed", 0)
    assert "không có chữ" in body["error"]


def test_search_ignores_textbooks_not_ready(
    client: TestClient, make_user: Callable[..., User], auth, text_pdf
):
    headers = auth(make_user("teacher"))
    upload(client, headers, text_pdf([]), "scan.pdf")
    assert client.get("/api/v1/textbooks/search", params={"q": "excel"}, headers=headers).json() == []
