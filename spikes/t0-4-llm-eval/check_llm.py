"""T0.4 — Kiểm tra key và mô hình LLM của Inception Labs (API tương thích OpenAI).

Chạy:  .venv\\Scripts\\python spikes\\t0-4-llm-eval\\check_llm.py
       .venv\\Scripts\\python spikes\\t0-4-llm-eval\\check_llm.py --models mercury-3 mercury-2

Key lấy theo thứ tự: biến môi trường LLM_API_KEY → file apps/backend/.env → file key.txt ở gốc repo.
Script KHÔNG in key ra màn hình.

Kiểm tra 3 việc: (1) key liệt kê được mô hình, (2) sinh các bước + gợi ý 4 cấp dạng JSON từ đề b09,
(3) structured output (response_format json_schema) có được tôn trọng không.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.inceptionlabs.ai/v1")

TASK = (
    "Đề (sheet Bang_Ke_Ban_Hang): cột Số lượng F10:F14 định dạng 0 chữ số thập phân, có dấu phân cách "
    "hàng nghìn; cột Đơn giá G10:G14 đúng 2 chữ số thập phân; cột Tỉ lệ I10:I14 đúng 3 chữ số thập phân. "
    'Giáo trình: "Quét chọn cột ➔ Home ➔ nhóm Number ➔ Comma Style", "Dùng Increase/Decrease Decimal". '
    "Mỗi cột là một bước. Gợi ý tiếng Việt 4 cấp: định hướng, gợi ý công cụ, chỉ vị trí, hướng dẫn chi tiết. "
    "Không làm thay học viên. Thuộc tính đề không nói tới thì để null."
)

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
                "required": ["id", "title", "target_range", "decimals", "thousands_separator", "hints"],
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "target_range": {"type": "string"},
                    "decimals": {"type": "integer"},
                    "thousands_separator": {"type": ["boolean", "null"]},
                    "hints": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                },
            },
        }
    },
}


def load_key() -> str:
    if key := os.environ.get("LLM_API_KEY"):
        return key.strip()
    env_file = ROOT / "apps" / "backend" / ".env"
    if env_file.exists():
        m = re.search(r"^LLM_API_KEY\s*=\s*(\S+)", env_file.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    key_file = ROOT / "key.txt"
    if key_file.exists():
        return re.split(r"[=:]", key_file.read_text(encoding="utf-8-sig").strip(), maxsplit=1)[-1].strip()
    raise SystemExit("Không tìm thấy key: đặt LLM_API_KEY trong apps/backend/.env (xem .env.example).")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["mercury-3", "mercury-2"])
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {load_key()}"}
    r = httpx.get(f"{BASE_URL}/models", headers=headers, timeout=30)
    print(f"Liệt kê mô hình: HTTP {r.status_code}")
    r.raise_for_status()
    for m in r.json().get("data", []):
        print(f"  - {m['id']} (ngữ cảnh {m.get('context_length')})")

    for model in args.models:
        start = time.perf_counter()
        r = httpx.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            timeout=120,
            json={
                "model": model,
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": TASK}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "script", "strict": True, "schema": SCHEMA},
                },
            },
        )
        elapsed = time.perf_counter() - start
        print(f"\n== {model}: HTTP {r.status_code}, {elapsed:.1f}s")
        if r.status_code != 200:
            print(r.text[:300])
            continue
        data = r.json()
        usage = data.get("usage", {})
        print(f"token vào/ra: {usage.get('prompt_tokens')}/{usage.get('completion_tokens')}")
        steps = json.loads(data["choices"][0]["message"]["content"])["steps"]
        for s in steps:
            sep = s["thousands_separator"]
            print(f"  [{s['id']}] {s['target_range']} decimals={s['decimals']} dấu-nghìn={sep}")
        for i, hint in enumerate(steps[0]["hints"], 1):
            print(f"     cấp {i}: {hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
