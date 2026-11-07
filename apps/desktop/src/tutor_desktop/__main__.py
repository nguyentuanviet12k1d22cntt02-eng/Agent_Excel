"""Điểm khởi động: `python -m tutor_desktop`. Khung ứng dụng thật được viết ở T7.1."""

import sys


def main() -> int:
    # Console Windows mặc định dùng cp1252, in tiếng Việt sẽ lỗi. Xem quy-tac-code.md mục 2.2.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("tutor_desktop: chưa có giao diện (xem T7.1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
