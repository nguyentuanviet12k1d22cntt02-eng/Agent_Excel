"""T1.2 — Chuẩn hóa bài học gốc của trung tâm vào samples/_local/ theo quy tắc đặt tên.

Đọc thư mục bài học gốc (mặc định "Cơ bản/"), mỗi bài tạo một thư mục samples/_local/b<NN>-<mô-tả>/:
  - de.xlsx        bản sao NGUYÊN VẸN file gốc (không mở/lưu lại để tránh mất định dạng)
  - giao-trinh.pdf với bài chỉ có PDF lý thuyết
  - thong-tin.md   nguồn, nhóm kỹ năng, vai trò từng sheet

samples/_local/ nằm trong .gitignore vì repo là public và tài liệu chưa được phép công khai.

Chạy:  python scripts/import_lessons.py            (chạy thử, chỉ in ra)
       python scripts/import_lessons.py --apply    (tạo thật)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "Cơ bản"
TARGET = ROOT / "samples" / "_local"

# Vai trò sheet
DE = "đề"  # học viên làm trên sheet này
HUONG_DAN = "hướng dẫn + bài luyện"  # sheet có hướng dẫn từng bước, cũng có ô để học viên làm
DAP_AN = "đáp án"
MAU = "bài mẫu (cần GV xác nhận là ví dụ hay đáp án)"
DU_LIEU = "dữ liệu tham chiếu"
BO_QUA = "bỏ qua (sheet rỗng do add-in)"


@dataclass(frozen=True)
class Lesson:
    number: int
    slug: str
    skill_group: str
    sheets: dict[str, str]

    @property
    def code(self) -> str:
        return f"b{self.number:02d}-{self.slug}"


LESSONS: list[Lesson] = [
    Lesson(3, "khoi-dong-excel", "Làm quen", {}),
    Lesson(4, "thao-tac-voi-sheet", "Làm quen", {}),
    Lesson(5, "thao-tac-voi-dong", "Tổ chức và nhập liệu", {"Bài tập": DE}),
    Lesson(6, "thao-tac-voi-cot", "Tổ chức và nhập liệu", {"Bài tập": DE}),
    Lesson(7, "dia-chi-o", "Tổ chức và nhập liệu", {"Bài 01": DE, "Bài 02": DE}),
    Lesson(
        8,
        "chuan-bi-nhap-lieu",
        "Tổ chức và nhập liệu",
        {"1. Thuc_Hanh_Tung_Buoc": HUONG_DAN, "2. Bang_Tong_Hop": DE, "3. Dap_An_Mau": DAP_AN},
    ),
    Lesson(
        9,
        "du-lieu-dang-so",
        "Định dạng dữ liệu",
        {"1. Thuc_Hanh_Tung_Buoc": HUONG_DAN, "2. Bang_Ke_Ban_Hang": DE, "3. Dap_An_Mau": DAP_AN},
    ),
    Lesson(
        10,
        "du-lieu-ngay-thang",
        "Định dạng dữ liệu",
        {"1. Thuc_Hanh_Tung_Buoc": HUONG_DAN, "2. Bang_Ke_Ban_Hang": DE, "3. Dap_An_Mau": DAP_AN},
    ),
    Lesson(
        11,
        "dinh-dang-khac",
        "Định dạng dữ liệu",
        {"1. Thuc_Hanh_Tung_Buoc": HUONG_DAN, "2. Danh_Sach_Thu_Nhap": DE, "3. Dap_An_Mau": DAP_AN},
    ),
    Lesson(12, "trang-in-co-ban", "Thiết lập trang in", {"Bài tập 1": DE, "Bài tập 2": DE}),
    Lesson(13, "huong-kho-giay-so-trang", "Thiết lập trang in", {"Bài tập 1": DE, "Bài tập 2": DE}),
    Lesson(
        14,
        "tao-bang-tinh",
        "Định dạng, trình bày bảng tính",
        {"Bảng Báo Giá": DE, "Phiếu Nhập Kho": DE, "Phiếu Thu": DE, "Bảng Chấm Công": DE},
    ),
    Lesson(15, "loc-du-lieu", "Lọc dữ liệu", {f"Bai 0{i}": DE for i in range(1, 7)}),
    Lesson(16, "sap-xep-du-lieu", "Sắp xếp dữ liệu", {f"Bai 0{i}": DE for i in range(1, 4)}),
    Lesson(17, "quy-tac-phep-tinh", "Công thức", {"Bai 01": DE, "Bai 02": DE, "Dữ liệu": DU_LIEU}),
    Lesson(18, "sao-chep-cong-thuc", "Công thức", {"Bai 01": DE}),
    Lesson(
        19,
        "luu-y-truoc-khi-dung-ham",
        "Hàm (nhập môn)",
        {"Data": DU_LIEU, "Bài tập": DE, "Bài mẫu": MAU, "GPT cache": BO_QUA},
    ),
    Lesson(20, "goi-va-chon-ham", "Hàm (nhập môn)", {"Bài tập": DE, "GPT cache": BO_QUA}),
    Lesson(21, "cu-phap-ham", "Hàm (nhập môn)", {"Bài tập": DE, "Bài mẫu": MAU, "GPT cache": BO_QUA}),
    Lesson(22, "ham-tinh-tong", "Hàm toán học – thống kê", {"Bài 01": DE, "Bài 02": DE}),
    Lesson(23, "ham-dem", "Hàm toán học – thống kê", {"Bài 1": DE}),
    Lesson(24, "ham-trung-binh", "Hàm toán học – thống kê", {"Bài 01": DE}),
    Lesson(25, "ham-min-max", "Hàm toán học – thống kê", {"Hàm MIN": DE, "Hàm MAX": DE}),
    Lesson(26, "ham-left-right-mid", "Hàm xử lý chuỗi", {f"Bài 0{i}": DE for i in range(1, 5)}),
    Lesson(27, "ham-len-trim", "Hàm xử lý chuỗi", {"Bài 01": DE}),
]


def find_source(source_dir: Path, number: int) -> Path:
    matches = sorted(source_dir.glob(f"Bài {number:02d}.*"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Bài {number:02d}: tìm thấy {len(matches)} file trong {source_dir}")
    return matches[0]


def info_markdown(lesson: Lesson, source: Path) -> str:
    has_solution = (TARGET / lesson.code / "dap-an.xlsx").exists()
    lines = [
        f"# {lesson.code}",
        "",
        f"- **Nguồn:** `{source.name}` (thư mục bài học gốc của trung tâm)",
        f"- **Nhóm kỹ năng:** {lesson.skill_group}",
        "- **Đề bài:** nằm ngay trong file Excel (các ô hướng dẫn, yêu cầu trên từng sheet)",
        f"- **Đáp án tách riêng (`dap-an.xlsx`):** {'có' if has_solution else 'chưa có'}",
        "",
    ]
    if lesson.sheets:
        lines += ["| Sheet | Vai trò |", "|---|---|"]
        lines += [f"| `{name}` | {role} |" for name, role in lesson.sheets.items()]
    else:
        lines.append("Bài lý thuyết dạng PDF, lưu thành `giao-trinh.pdf`.")
    return "\n".join(lines) + "\n"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chuẩn hóa bài học gốc vào samples/_local/.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Thư mục bài học gốc")
    parser.add_argument("--apply", action="store_true", help="Tạo thật (mặc định chỉ chạy thử)")
    args = parser.parse_args()

    for lesson in LESSONS:
        source = find_source(args.source, lesson.number)
        target_dir = TARGET / lesson.code
        target_file = target_dir / ("de.xlsx" if source.suffix == ".xlsx" else "giao-trinh.pdf")
        print(f"{source.name}  →  {target_file.relative_to(ROOT)}")
        if args.apply:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_file)
            (target_dir / "thong-tin.md").write_text(info_markdown(lesson, source), encoding="utf-8")

    print(f"\nTổng: {len(LESSONS)} bài." + ("" if args.apply else " (chạy thử — thêm --apply để tạo thật)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
