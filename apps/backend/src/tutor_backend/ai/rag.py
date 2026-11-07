"""RAG giáo trình bước 1: tìm toàn văn BM25 (kien-truc.md A7; embedding thêm khi chọn được nhà cung cấp).

BM25 tính trong Python nên chạy giống nhau trên PostgreSQL và SQLite. Giáo trình một khóa chỉ vài trăm đoạn,
dựng chỉ mục mỗi lần tìm vẫn nhanh (vài ms). Tách từ cho tiếng Việt: âm tiết + cặp âm tiết, kèm bản bỏ dấu để
truy vấn gõ không dấu ("ham vlookup") vẫn khớp.
"""

import math
import re
import unicodedata
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from tutor_backend.ai.textbook_parser import Section
from tutor_backend.ai.vietnamese import strip_accents
from tutor_backend.models import Textbook, TextbookChunk
from tutor_backend.models.enums import TextbookStatus

CHUNK_TARGET_CHARS = 900  # đủ một mục ngắn; mục dài cắt theo đoạn văn
CHUNK_MAX_CHARS = 1400
BM25_K1 = 1.5
BM25_B = 0.75
HEADING_WEIGHT = 3  # từ trong tiêu đề mục tính nặng hơn từ trong thân
STOPWORDS = frozenset(
    (
        "và",
        "của",
        "các",
        "là",
        "có",
        "cho",
        "một",
        "những",
        "trong",
        "được",
        "để",
        "khi",
        "với",
        "này",
        "đó",
        "thì",
        "ra",
        "vào",
        "lên",
        "xuống",
        "từ",
        "theo",
        "như",
        "cũng",
        "đã",
        "sẽ",
        "đang",
        "rồi",
        "nếu",
        "hoặc",
        "hay",
        "tại",
        "về",
        "bằng",
        "nhưng",
        "mà",
        "thế",
        "nên",
        "vì",
        "do",
        "sau",
        "trước",
        "trên",
        "dưới",
        "không",
        "chỉ",
        "ta",
        "bạn",
    )
)
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class Passage:
    chunk_id: uuid.UUID
    textbook_id: uuid.UUID
    textbook_title: str
    heading: str
    page: int | None
    content: str
    score: float


def tokenize(text: str) -> list[str]:
    """Âm tiết (có dấu và không dấu) + cặp âm tiết liền nhau (không dấu); bỏ từ dừng."""
    words = [w for w in _WORD.findall(unicodedata.normalize("NFC", text).lower()) if w not in STOPWORDS]
    plain = [strip_accents(w) for w in words]
    tokens = words + [p for p, w in zip(plain, words, strict=True) if p != w]
    tokens += [f"{a}_{b}" for a, b in zip(plain, plain[1:], strict=False)]
    return tokens


def chunk_sections(sections: Iterable[Section]) -> list[tuple[str, int | None, str]]:
    """(tiêu đề, trang, nội dung): mục ngắn giữ nguyên, mục dài cắt theo đoạn văn."""
    chunks: list[tuple[str, int | None, str]] = []
    for section in sections:
        current: list[str] = []
        size = 0
        for paragraph in section.text.split("\n"):
            if current and size + len(paragraph) > CHUNK_TARGET_CHARS:
                chunks.append((section.heading, section.page, "\n".join(current)))
                current, size = [], 0
            while len(paragraph) > CHUNK_MAX_CHARS:  # đoạn văn quá dài: cắt cứng
                chunks.append((section.heading, section.page, paragraph[:CHUNK_MAX_CHARS]))
                paragraph = paragraph[CHUNK_MAX_CHARS:]
            current.append(paragraph)
            size += len(paragraph)
        if current:
            chunks.append((section.heading, section.page, "\n".join(current)))
    return chunks


class Bm25Index:
    def __init__(self, documents: Sequence[list[str]]) -> None:
        self.documents = [Counter(doc) for doc in documents]
        self.lengths = [len(doc) for doc in documents]
        self.average = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        frequency: Counter[str] = Counter()
        for doc in self.documents:
            frequency.update(doc.keys())
        total = len(self.documents)
        self.idf = {term: math.log((total - df + 0.5) / (df + 0.5) + 1) for term, df in frequency.items()}

    def scores(self, query: list[str]) -> list[float]:
        results = []
        for doc, length in zip(self.documents, self.lengths, strict=True):
            score = 0.0
            for term in set(query):
                tf = doc.get(term, 0)
                if tf:
                    norm = BM25_K1 * (1 - BM25_B + BM25_B * length / (self.average or 1))
                    score += self.idf[term] * tf * (BM25_K1 + 1) / (tf + norm)
            results.append(score)
        return results


def _document_tokens(chunk: TextbookChunk) -> list[str]:
    return tokenize(chunk.heading) * HEADING_WEIGHT + tokenize(chunk.content)


def search(
    db: Session, query: str, textbook_ids: Sequence[uuid.UUID] | None = None, limit: int = 5
) -> list[Passage]:
    """Các đoạn giáo trình liên quan nhất tới `query`, trong các giáo trình đã lập chỉ mục xong."""
    terms = tokenize(query)
    if not terms:
        return []
    statement = (
        select(TextbookChunk, Textbook.title)
        .join(Textbook, Textbook.id == TextbookChunk.textbook_id)
        .where(Textbook.status == TextbookStatus.READY)
    )
    if textbook_ids is not None:
        if not textbook_ids:
            return []
        statement = statement.where(TextbookChunk.textbook_id.in_(list(textbook_ids)))
    rows = list(db.execute(statement.order_by(TextbookChunk.textbook_id, TextbookChunk.ord)))
    if not rows:
        return []
    index = Bm25Index([_document_tokens(chunk) for chunk, _ in rows])
    ranked = sorted(zip(index.scores(terms), rows, strict=True), key=lambda item: item[0], reverse=True)
    return [
        Passage(chunk.id, chunk.textbook_id, title, chunk.heading, chunk.page, chunk.content, round(score, 3))
        for score, (chunk, title) in ranked[:limit]
        if score > 0
    ]
