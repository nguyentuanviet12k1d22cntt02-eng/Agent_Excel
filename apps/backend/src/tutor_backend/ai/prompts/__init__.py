"""Prompt cho LLM, mỗi prompt một file (quy tắc code 2.4 mục 4: sửa prompt không phải sửa logic).

Chỗ cần điền viết dạng `$ten` (string.Template), không dùng {} để khỏi đụng dấu ngoặc của JSON.
"""

from functools import cache
from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).resolve().parent


@cache
def load_prompt(name: str) -> Template:
    return Template((PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8"))


def render(name: str, **values: str) -> str:
    """Điền giá trị vào prompt; thiếu chỗ nào thì báo lỗi ngay (KeyError) thay vì gửi prompt dở."""
    return load_prompt(name).substitute(values)
