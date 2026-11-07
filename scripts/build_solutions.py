"""T1.2 — Tạo file đáp án dap-an.xlsx CÙNG BỐ CỤC với de.xlsx bằng Excel thật (COM).

Đáp án sẵn có của trung tâm (sheet `Dap_An_Mau`) nằm ở vị trí khác với sheet đề, nên không so sánh
từng ô được. Script này mở de.xlsx, làm bài đúng như học viên phải làm, rồi lưu thành dap-an.xlsx.
Dùng Excel thật để công thức được tính và định dạng giữ nguyên.

Công thức giải (recipe) chỉ tham chiếu ô trong chính file đề, không chép nội dung bài vào repo.

Chạy:  python scripts/build_solutions.py              (mọi bài có recipe)
       python scripts/build_solutions.py b09          (một bài)
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples" / "_local"
XL_RIGHT = -4152  # Excel: HorizontalAlignment = xlRight
XL_OPENXML_WORKBOOK = 51  # Excel: định dạng .xlsx
LCID_EN_US = 1033

Recipe = Callable[[object], None]  # nhận đối tượng Workbook của Excel


def set_number_format(rng: object, fmt: str) -> None:
    """Gán NumberFormat theo mã chuẩn (en-US), không để Excel dịch theo cài đặt vùng của Windows.

    pywin32 mặc định gọi COM với ngôn ngữ người dùng: trên máy vi-VN, gán "#,##0" sẽ bị lưu thành
    "#.##0" (sai). Gọi Invoke với LCID 1033 thì Excel nhận đúng mã chuẩn. Xem quy-tac-code.md mục 2.3.
    """
    import pythoncom

    dispid = rng._oleobj_.GetIDsOfNames("NumberFormat")
    rng._oleobj_.Invoke(dispid, LCID_EN_US, pythoncom.DISPATCH_PROPERTYPUT, 0, fmt)


def get_number_format(rng: object) -> str:
    """Đọc NumberFormat theo mã chuẩn (en-US). Lý do: xem set_number_format."""
    import pythoncom

    dispid = rng._oleobj_.GetIDsOfNames("NumberFormat")
    return rng._oleobj_.Invoke(dispid, LCID_EN_US, pythoncom.DISPATCH_PROPERTYGET, 1)


def solve_b09(wb: object) -> None:
    """Bài 09 — định dạng dữ liệu số."""
    # Sheet luyện tập: nhập số thô ở cột D vào cột E rồi định dạng theo yêu cầu
    ws = wb.Worksheets("1. Thuc_Hanh_Tung_Buoc")
    for row in range(7, 11):  # Bài tập 1: dấu phân cách hàng nghìn
        ws.Range(f"E{row}").Value = ws.Range(f"D{row}").Value
        set_number_format(ws.Range(f"E{row}"), "#,##0")
    for row, fmt in zip(range(15, 19), ["0.00", "0.000", "0.0000", "0.00"], strict=True):  # Bài tập 2
        ws.Range(f"E{row}").Value = float(ws.Range(f"D{row}").Value)
        set_number_format(ws.Range(f"E{row}"), fmt)
    # Không dùng địa chỉ ghép "E7:E10,E15:E18": Excel báo lỗi trên máy vi-VN (đã thử, kể cả với LCID 1033)
    for address in ("E7:E10", "E15:E18"):
        ws.Range(address).HorizontalAlignment = XL_RIGHT

    # Sheet đề: nhập số liệu thô (dòng 18–22) vào bảng (dòng 10–14), định dạng theo hướng dẫn B5:B7
    ws = wb.Worksheets("2. Bang_Ke_Ban_Hang")
    for row in range(10, 15):
        for col in ("F", "G", "I"):
            ws.Range(f"{col}{row}").Value = ws.Range(f"{col}{row + 8}").Value
    set_number_format(ws.Range("F10:F14"), "#,##0")
    set_number_format(ws.Range("G10:H14"), "#,##0.00")
    set_number_format(ws.Range("I10:I14"), "0.000")
    ws.Range("F10:I14").HorizontalAlignment = XL_RIGHT


def solve_b22(wb: object) -> None:
    """Bài 22 — hàm SUM, sheet `Bài 01` (sheet `Bài 02` chờ giảng viên xác nhận cách tính)."""
    ws = wb.Worksheets("Bài 01")
    ws.Range("F9:F19").Formula = "=SUM(C9:E9)"  # Excel tự đổi địa chỉ tương đối cho từng dòng
    ws.Range("C20:F20").Formula = "=SUM(C9:C19)"
    # Không định dạng thêm: đề không yêu cầu. Đáp án phải "sạch", nếu không diff sẽ sinh bước thừa (T2.6).


RECIPES: dict[str, Recipe] = {
    "b09-du-lieu-dang-so": solve_b09,
    "b22-ham-tinh-tong": solve_b22,
}


def build(code: str, recipe: Recipe) -> Path:
    import pythoncom
    import win32com.client

    starter = SAMPLES / code / "de.xlsx"
    solution = SAMPLES / code / "dap-an.xlsx"
    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")  # phiên Excel riêng
    try:
        excel.Visible = False
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Open(str(starter))
        try:
            recipe(wb)
            wb.Application.Calculate()
            wb.SaveAs(str(solution), FileFormat=XL_OPENXML_WORKBOOK)
        finally:
            wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
    return solution


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    wanted = sys.argv[1:]
    for code, recipe in RECIPES.items():
        if wanted and not any(code.startswith(w) for w in wanted):
            continue
        path = build(code, recipe)
        print(f"Đã tạo {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
