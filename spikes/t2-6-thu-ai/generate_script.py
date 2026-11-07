"""T2.6 — Thử AI sinh kịch bản từ DIFF file đề ↔ file đáp án, rồi tự kiểm kịch bản trên chính hai file đó.

Chạy:  .venv\\Scripts\\python spikes\\t2-6-thu-ai\\generate_script.py b09
       .venv\\Scripts\\python spikes\\t2-6-thu-ai\\generate_script.py b22 --model mercury-2

Quy trình (bản thử sớm của T4.3 diff + T5.5 tác tử + T4.5 tự kiểm):
  1. diff: so từng ô của sheet làm bài giữa de.xlsx và dap-an.xlsx (giá trị, công thức, định dạng số, căn lề),
     gom các ô liền nhau cùng loại thay đổi thành vùng.
  2. Lấy đề bài: chữ trong ô của sheet làm bài + chữ trong text box + sheet hướng dẫn (nếu có).
  3. Gọi LLM (Inception Labs, structured output) sinh kịch bản: bước, điều kiện kiểm chứng, gợi ý 4 cấp.
  4. Tự kiểm: mỗi điều kiện phải ĐẠT trên dap-an.xlsx và KHÔNG ĐẠT trên de.xlsx.
  5. Độ phủ: mọi vùng thay đổi trong diff có được ít nhất một điều kiện kiểm tới không.
Kết quả lưu vào samples/_local/<bài>/kich-ban-ai.json (không lên git).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import httpx
import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from dump_workbook import textbox_texts  # noqa: E402 — tái dùng hàm đọc text box

LESSONS = {
    "b09": ("b09-du-lieu-dang-so", "2. Bang_Ke_Ban_Hang", "1. Thuc_Hanh_Tung_Buoc"),
    "b22": ("b22-ham-tinh-tong", "Bài 01", None),
}
CHECK_TYPES = ["value_equals", "is_formula", "formula_uses_function", "number_format", "alignment"]


# ---------------------------------------------------------------- 1. diff
@dataclass
class Change:
    range: str
    kind: str  # value | formula | number_format | alignment
    after: str


def cell_signature(cell: object, cached: object) -> dict[str, str]:
    v = cell.value
    is_formula = isinstance(v, str) and v.startswith("=")
    return {
        "value": "" if is_formula or v is None else repr(v),
        "formula": v if is_formula else "",
        "number_format": cell.number_format or "General",
        "alignment": (cell.alignment.horizontal or "general") if cell.alignment else "general",
    }


def diff_sheet(de_path: Path, da_path: Path, sheet: str) -> list[Change]:
    de, da = openpyxl.load_workbook(de_path)[sheet], openpyxl.load_workbook(da_path)[sheet]
    changes: dict[tuple[str, str, int], list[int]] = {}  # (kind, after, col) -> rows
    for row in da.iter_rows():
        for cell in row:
            before = cell_signature(de[cell.coordinate], None)
            after = cell_signature(cell, None)
            for kind in after:
                if before[kind] != after[kind] and after[kind] not in ("", "General", "general"):
                    label = after[kind] if kind != "value" else "(giá trị mới)"
                    changes.setdefault((kind, label, cell.column), []).append(cell.row)
    result = []
    for (kind, after, col), rows in sorted(changes.items(), key=lambda x: (x[0][2], x[0][0])):
        rows.sort()
        start = prev = rows[0]
        for r in [*rows[1:], None]:
            if r is not None and r == prev + 1:
                prev = r
                continue
            letter = get_column_letter(col)
            rng = f"{letter}{start}" if start == prev else f"{letter}{start}:{letter}{prev}"
            result.append(Change(rng, kind, after))
            if r is not None:
                start = prev = r
    return result


# ---------------------------------------------------------------- 2. đề bài
def instructions(de_path: Path, sheet: str, guide_sheet: str | None) -> str:
    wb = openpyxl.load_workbook(de_path)
    parts = []
    for name in [sheet, guide_sheet]:
        if not name:
            continue
        texts = [
            f"{c.coordinate}: {c.value}"
            for row in wb[name].iter_rows()
            for c in row
            if isinstance(c.value, str) and len(c.value) > 15
        ]
        parts.append(f"[Sheet {name}]\n" + "\n".join(texts[:25]))
    boxes = [t for s, t in textbox_texts(de_path) if s == sheet]
    if boxes:
        parts.append("[Text box]\n" + "\n".join(boxes))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- 3. gọi LLM
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["steps"],
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "requirement_card", "checks", "hints", "textbook_quote"],
                "properties": {
                    "title": {"type": "string"},
                    "requirement_card": {
                        "type": "string",
                        "description": "Một câu: phải đạt gì, KHÔNG nói cách làm",
                    },
                    "checks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "type",
                                "range",
                                "decimals",
                                "thousands_separator",
                                "function",
                                "horizontal",
                            ],
                            "properties": {
                                "type": {"type": "string", "enum": CHECK_TYPES},
                                "range": {"type": "string", "description": "Vùng ô, ví dụ F10:F14"},
                                "decimals": {"type": ["integer", "null"]},
                                "thousands_separator": {
                                    "type": ["boolean", "null"],
                                    "description": "null nếu đề không yêu cầu",
                                },
                                "function": {
                                    "type": ["string", "null"],
                                    "description": "Hàm bắt buộc, ví dụ SUM",
                                },
                                "horizontal": {
                                    "type": ["string", "null"],
                                    "enum": ["left", "center", "right", None],
                                },
                            },
                        },
                    },
                    "hints": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                    "textbook_quote": {"type": ["string", "null"]},
                },
            },
        }
    },
}

SYSTEM = """Bạn là trợ giảng Excel, soạn kịch bản hướng dẫn thực hành từng bước cho học viên.
Nguyên tắc:
- Dựa vào DANH SÁCH THAY ĐỔI (diff giữa file đề và file đáp án): mọi thay đổi phải thuộc một bước, có điều kiện kiểm chứng tương ứng.
- Thứ tự bước theo cách học viên làm tự nhiên (nhập dữ liệu trước, định dạng sau).
- requirement_card chỉ nói PHẢI ĐẠT GÌ, không nói cách làm.
- hints gồm đúng 4 cấp tăng dần: định hướng → gợi ý công cụ → chỉ vị trí → hướng dẫn chi tiết. Không làm thay học viên.
- Chỉ dùng công cụ, hàm có trong đề bài/hướng dẫn. Thuộc tính đề không yêu cầu thì để null (không tự thêm ràng buộc).
- Loại điều kiện: value_equals (giá trị bằng đáp án), is_formula (ô phải là công thức), formula_uses_function (có dùng hàm, điền function),
  number_format (decimals, thousands_separator), alignment (horizontal).
- Viết tiếng Việt, không ghi cứng chuỗi hiển thị số (máy Việt Nam hiển thị 1.250 thay vì 1,250)."""


def load_key() -> str:
    if key := os.environ.get("LLM_API_KEY"):
        return key
    text = (ROOT / "apps" / "backend" / ".env").read_text(encoding="utf-8")
    return re.search(r"^LLM_API_KEY\s*=\s*(\S+)", text, re.M).group(1)


def call_llm(model: str, user: str) -> tuple[dict, dict, float]:
    start = time.perf_counter()
    r = httpx.post(
        "https://api.inceptionlabs.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {load_key()}"},
        timeout=180,
        json={
            "model": model,
            "max_tokens": 8000,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "script", "strict": True, "schema": SCHEMA},
            },
        },
    )
    r.raise_for_status()
    data = r.json()
    return (
        json.loads(data["choices"][0]["message"]["content"]),
        data.get("usage", {}),
        time.perf_counter() - start,
    )


# ---------------------------------------------------------------- 4. tự kiểm
def fmt_semantics(fmt: str) -> tuple[int, bool]:
    section = (fmt or "General").split(";")[0]
    m = re.search(r"\.(0+)", section)
    return (len(m.group(1)) if m else 0), ("," in section.split(".")[0])


def cells(ws: object, rng: str) -> list[object]:
    min_col, min_row, max_col, max_row = range_boundaries(rng)
    return [ws.cell(r, c) for r in range(min_row, max_row + 1) for c in range(min_col, max_col + 1)]


def evaluate(check: dict, ws: object, ws_val: object, ws_solution_val: object) -> bool:
    cs = cells(ws, check["range"])
    t = check["type"]
    if t == "value_equals":
        return all(
            ws_val[c.coordinate].value is not None
            and ws_val[c.coordinate].value == ws_solution_val[c.coordinate].value
            for c in cs
        )
    if t == "is_formula":
        return all(isinstance(c.value, str) and c.value.startswith("=") for c in cs)
    if t == "formula_uses_function":
        fn = (check.get("function") or "").upper()
        return all(isinstance(c.value, str) and f"{fn}(" in c.value.upper() for c in cs)
    if t == "number_format":
        for c in cs:
            decimals, sep = fmt_semantics(c.number_format)
            if check.get("decimals") is not None and decimals != check["decimals"]:
                return False
            if check.get("thousands_separator") is not None and sep != check["thousands_separator"]:
                return False
        return True
    if t == "alignment":
        want = check.get("horizontal")
        return all(
            (c.alignment.horizontal or "general") in (want, "general" if want == "right" else want)
            for c in cs
        )
    return False


def self_check(script: dict, de_path: Path, da_path: Path, sheet: str) -> list[tuple[str, str, bool, bool]]:
    de, de_v = openpyxl.load_workbook(de_path)[sheet], openpyxl.load_workbook(de_path, data_only=True)[sheet]
    da, da_v = openpyxl.load_workbook(da_path)[sheet], openpyxl.load_workbook(da_path, data_only=True)[sheet]
    out = []
    for i, step in enumerate(script["steps"], 1):
        for chk in step["checks"]:
            on_solution = evaluate(chk, da, da_v, da_v)
            on_starter = evaluate(chk, de, de_v, da_v)
            desc = f"{chk['type']} {chk['range']}" + "".join(
                f" {k}={chk[k]}"
                for k in ("decimals", "thousands_separator", "function", "horizontal")
                if chk.get(k) is not None
            )
            out.append((f"bước {i}", desc, on_solution, on_starter))
    return out


def coverage(changes: list[Change], script: dict) -> list[Change]:
    covered = []
    for step in script["steps"]:
        for chk in step["checks"]:
            covered.append(range_boundaries(chk["range"]))
    missing = []
    for ch in changes:
        a = range_boundaries(ch.range)
        if not any(b[0] <= a[0] and b[1] <= a[1] and b[2] >= a[2] and b[3] >= a[3] for b in covered):
            missing.append(ch)
    return missing


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("lesson", choices=sorted(LESSONS))
    parser.add_argument("--model", default="mercury-3")
    args = parser.parse_args()
    folder, sheet, guide = LESSONS[args.lesson]
    base = ROOT / "samples" / "_local" / folder
    de_path, da_path = base / "de.xlsx", base / "dap-an.xlsx"

    changes = diff_sheet(de_path, da_path, sheet)
    print(f"1) Diff sheet '{sheet}': {len(changes)} vùng thay đổi")
    for ch in changes:
        print(f"   {ch.range:<10} {ch.kind:<14} → {ch.after}")
    diff_text = "\n".join(f"{ch.range}: {ch.kind} → {ch.after}" for ch in changes)
    user = f"ĐỀ BÀI VÀ HƯỚNG DẪN TRONG FILE:\n{instructions(de_path, sheet, guide)}\n\nDANH SÁCH THAY ĐỔI (đề → đáp án):\n{diff_text}"

    script, usage, secs = call_llm(args.model, user)
    print(
        f"\n2) {args.model}: {secs:.1f} s, token vào/ra {usage.get('prompt_tokens')}/{usage.get('completion_tokens')}, {len(script['steps'])} bước"
    )
    for i, step in enumerate(script["steps"], 1):
        print(f"   [{i}] {step['title']}  |  thẻ: {step['requirement_card']}")
        print(f"       gợi ý cấp 1: {step['hints'][0]}")
        print(f"       gợi ý cấp 4: {step['hints'][3]}")

    print("\n3) Tự kiểm (đạt trên đáp án, KHÔNG đạt trên đề):")
    results = self_check(script, de_path, da_path, sheet)
    good = 0
    for step, desc, sol, start in results:
        ok = sol and not start
        good += ok
        note = "✅" if ok else ("❌ sai trên đáp án" if not sol else "⚠️ đạt sẵn trên đề (vô nghĩa)")
        print(f"   {note:<26} {step}: {desc}")
    print(f"   → {good}/{len(results)} điều kiện hợp lệ")

    missing = coverage(changes, script)
    print(
        f"\n4) Độ phủ diff: {len(changes) - len(missing)}/{len(changes)} vùng thay đổi có điều kiện kiểm tới"
    )
    for ch in missing:
        print(f"   chưa phủ: {ch.range} {ch.kind}")

    out = base / "kich-ban-ai.json"
    out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
