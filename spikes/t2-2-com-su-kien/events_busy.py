"""T2.2 — Sự kiện COM và xử lý khi Excel đang bận.

Chạy:
  .venv\\Scripts\\python spikes\\t2-2-com-su-kien\\events_busy.py            # tự kiểm tra (phiên Excel riêng)
  .venv\\Scripts\\python spikes\\t2-2-com-su-kien\\events_busy.py --attach 120
      # gắn vào Excel ĐANG MỞ của bạn trong 120 giây: ghi lại sự kiện và lần đọc bị từ chối.
      # Trong lúc chạy, hãy thao tác tự do: gõ trong ô, mở hộp thoại, đổi sheet.

Phần 1: bắt SheetChange / SheetSelectionChange, đo độ trễ.
Phần 2: mở hộp thoại Format Cells (Excel bận) → thử đọc ô → ghi mã lỗi → thử lại → đóng hộp thoại
        bằng WM_CLOSE (không giả lập bàn phím).
"""

from __future__ import annotations

import argparse
import sys
import threading
import time

import pythoncom
import pywintypes
import win32com.client
import win32con
import win32gui
import win32process

RPC_E_CALL_REJECTED = -2147418111  # 0x80010001: Excel từ chối lệnh (đang bận)
RPC_E_SERVERCALL_RETRYLATER = -2147417846  # 0x8001010A
BUSY_CODES = {RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER}
XL_DIALOG_FORMAT_NUMBER = 42
EXCEL_DIALOG_CLASS = "bosa_sdm_XL9"

EVENTS: list[tuple[float, str, str]] = []


class AppEvents:
    """Nhận sự kiện của Excel.Application."""

    def OnSheetChange(self, sh: object, target: object) -> None:  # noqa: N802 — tên do COM quy định
        EVENTS.append((time.perf_counter(), "SheetChange", f"{sh.Name}!{target.Address}"))

    def OnSheetSelectionChange(self, sh: object, target: object) -> None:  # noqa: N802
        EVENTS.append((time.perf_counter(), "SelectionChange", f"{sh.Name}!{target.Address}"))

    def OnSheetActivate(self, sh: object) -> None:  # noqa: N802
        EVENTS.append((time.perf_counter(), "SheetActivate", sh.Name))


def read_with_retry(fn: object, attempts: int = 10, delay: float = 0.1) -> tuple[object, list[int]]:
    """Gọi COM, nếu Excel bận thì thử lại tối đa `attempts` lần. Trả về (kết quả, danh sách mã lỗi gặp)."""
    errors: list[int] = []
    for _ in range(attempts):
        try:
            return fn(), errors
        except pywintypes.com_error as exc:
            if exc.hresult not in BUSY_CODES:
                raise
            errors.append(exc.hresult)
            time.sleep(delay)
    return None, errors


def pump(seconds: float) -> None:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pythoncom.PumpWaitingMessages()
        time.sleep(0.01)


def part_events(excel: object) -> None:
    print("Phần 1 — sự kiện:")
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    for address, value in [("B2", 10), ("C3", 20), ("D4", "=B2+C3")]:
        EVENTS.clear()
        start = time.perf_counter()
        ws.Range(address).Value = value
        pump(0.3)
        hit = [e for e in EVENTS if e[1] == "SheetChange"]
        lag = f"{(hit[0][0] - start) * 1000:.1f} ms" if hit else "KHÔNG nhận được"
        print(f"  Ghi {address}={value!r}: SheetChange {hit[0][2] if hit else ''} — trễ {lag}")
    EVENTS.clear()
    ws.Range("E5:F6").Select()
    pump(0.3)
    print(f"  Chọn E5:F6: {[e[1:] for e in EVENTS]}")
    EVENTS.clear()
    wb.Worksheets.Add()
    pump(0.3)
    print(f"  Thêm sheet mới: {[e[1:] for e in EVENTS]}")
    wb.Close(SaveChanges=False)


def find_dialog(pid: int) -> int | None:
    found: list[int] = []

    def visit(hwnd: int, _: object) -> bool:
        if (
            win32gui.GetClassName(hwnd) == EXCEL_DIALOG_CLASS
            and win32process.GetWindowThreadProcessId(hwnd)[1] == pid
        ):
            found.append(hwnd)
        return True

    win32gui.EnumWindows(visit, None)
    return found[0] if found else None


def part_busy(excel: object) -> None:
    print("\nPhần 2 — Excel bận (đang mở hộp thoại Format Cells):")
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    ws.Range("A1").Value = 123
    pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
    stream = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, excel._oleobj_)

    def show_dialog() -> None:
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch(
            pythoncom.CoGetInterfaceAndReleaseStream(stream, pythoncom.IID_IDispatch)
        )
        try:
            app.Dialogs(XL_DIALOG_FORMAT_NUMBER).Show()  # chặn tới khi hộp thoại đóng
        finally:
            pythoncom.CoUninitialize()

    t = threading.Thread(target=show_dialog, daemon=True)
    t.start()
    hwnd = None
    for _ in range(50):
        hwnd = find_dialog(pid)
        if hwnd:
            break
        time.sleep(0.1)
    print(
        f"  Hộp thoại xuất hiện: {'có' if hwnd else 'KHÔNG'} (class {EXCEL_DIALOG_CLASS}, tiêu đề {win32gui.GetWindowText(hwnd)!r})"
        if hwnd
        else "  Không thấy hộp thoại"
    )

    value, errors = read_with_retry(lambda: ws.Range("A1").Value, attempts=5, delay=0.1)
    codes = sorted({hex(e & 0xFFFFFFFF) for e in errors})
    print(
        f"  Đọc A1 khi hộp thoại đang mở: {'được, giá trị ' + repr(value) if value is not None else 'bị từ chối'}; số lần bị từ chối {len(errors)}, mã lỗi {codes}"
    )

    if hwnd:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    t.join(timeout=5)
    print(f"  Đóng hộp thoại bằng WM_CLOSE: {'được' if not t.is_alive() else 'KHÔNG'}")
    value, errors = read_with_retry(lambda: ws.Range("A1").Value)
    print(f"  Đọc A1 sau khi đóng: {value!r}, số lần bị từ chối {len(errors)}")
    wb.Close(SaveChanges=False)


def find_grid_window(excel: object) -> int | None:
    """Cửa sổ lưới ô của workbook (class EXCEL7) — nơi nhận phím khi người dùng gõ."""
    found: list[int] = []

    def visit(hwnd: int, _: object) -> bool:
        if win32gui.GetClassName(hwnd) == "EXCEL7":
            found.append(hwnd)
        return True

    win32gui.EnumChildWindows(excel.Hwnd, visit, None)
    return found[0] if found else None


def part_edit_mode(excel: object) -> None:
    print("\nPhần 3 — Excel bận thật: đang sửa ô (giả lập người học bấm F2 rồi gõ):")
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    ws.Range("A1").Value = 123
    ws.Range("A1").Select()
    grid = find_grid_window(excel)
    if not grid:
        print("  Không tìm thấy cửa sổ lưới EXCEL7")
        wb.Close(SaveChanges=False)
        return
    # Gửi phím vào ĐÚNG cửa sổ lưới của phiên Excel riêng (không phải bàn phím toàn hệ thống)
    win32gui.PostMessage(grid, win32con.WM_KEYDOWN, win32con.VK_F2, 0)
    win32gui.PostMessage(grid, win32con.WM_CHAR, ord("9"), 0)
    time.sleep(0.5)
    print(f"  Excel.Interactive/Ready: {read_with_retry(lambda: excel.Ready, attempts=1)}")
    start = time.perf_counter()
    value, errors = read_with_retry(lambda: ws.Range("A1").Value, attempts=10, delay=0.1)
    codes = sorted({hex(e & 0xFFFFFFFF) for e in errors})
    print(
        f"  Đọc A1 khi đang sửa ô: {'được ' + repr(value) if not errors or value is not None else 'bị từ chối hết'}"
        f"; bị từ chối {len(errors)}/10 lần, mã {codes}, mất {(time.perf_counter() - start) * 1000:.0f} ms"
    )
    win32gui.PostMessage(grid, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)  # thoát chế độ sửa, bỏ "9"
    time.sleep(0.5)
    value, errors = read_with_retry(lambda: ws.Range("A1").Value)
    print(f"  Sau khi bấm Esc: đọc A1 = {value!r}, bị từ chối {len(errors)} lần")
    wb.Close(SaveChanges=False)


def attach(seconds: int) -> None:
    excel = win32com.client.GetActiveObject("Excel.Application")
    win32com.client.WithEvents(excel, AppEvents)
    print(f"Đã gắn vào Excel đang mở. Theo dõi {seconds} giây, hãy thao tác tự do…")
    reads = rejected = 0
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pump(0.5)
        reads += 1
        _, errors = read_with_retry(lambda: excel.ActiveSheet.Name, attempts=1)
        rejected += bool(errors)
    print(f"Sự kiện nhận được: {len(EVENTS)}; lần đọc thử: {reads}; bị từ chối: {rejected}")
    for _, kind, detail in EVENTS[-15:]:
        print(f"  {kind}: {detail}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--attach", type=int, metavar="GIAY", help="Gắn vào Excel đang mở trong số giây này")
    args = parser.parse_args()
    pythoncom.CoInitialize()
    try:
        if args.attach:
            attach(args.attach)
            return 0
        excel = win32com.client.DispatchEx("Excel.Application")  # luôn là phiên riêng
        win32com.client.WithEvents(excel, AppEvents)
        try:
            excel.Visible = True  # hộp thoại cần cửa sổ hiển thị
            excel.DisplayAlerts = False
            part_events(excel)
            part_busy(excel)
            part_edit_mode(excel)
        finally:
            excel.Quit()
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
