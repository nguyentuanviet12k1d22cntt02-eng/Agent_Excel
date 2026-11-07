"""T2.2 — Sự kiện COM và xử lý khi Excel đang bận.

Chạy:
  .venv\\Scripts\\python spikes\\t2-2-com-su-kien\\events_busy.py              # tự kiểm tra (phiên Excel riêng)
  .venv\\Scripts\\python spikes\\t2-2-com-su-kien\\events_busy.py --soak 600   # chạy bền 10 phút (phiên riêng)
  .venv\\Scripts\\python spikes\\t2-2-com-su-kien\\events_busy.py --attach 120
      # gắn vào Excel ĐANG MỞ của bạn trong 120 giây: ghi lại sự kiện và lần đọc bị từ chối.

Phần 1: bắt SheetChange / SheetSelectionChange / SheetActivate, đo độ trễ.
Phần 2: đưa phiên Excel riêng vào 2 trạng thái bận THẬT rồi thử từng loại lệnh COM:
  - đang sửa ô: F2 + gõ, chưa Enter;
  - đang mở hộp thoại Format Cells bằng nút trên Ribbon (UIA Invoke), giống người dùng bấm.
Không giả lập bàn phím/chuột toàn hệ thống: phím được gửi bằng PostMessage vào ĐÚNG cửa sổ lưới (EXCEL7)
của phiên Excel riêng, sau khi gắn luồng nhập (AttachThreadInput) và đặt focus trong luồng đó.
"""

from __future__ import annotations

import argparse
import random
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable

import pythoncom
import pywintypes
import uiautomation as auto
import win32api
import win32com.client
import win32con
import win32gui
import win32process

RPC_E_CALL_REJECTED = -2147418111  # 0x80010001: Excel từ chối lệnh (đang bận)
RPC_E_SERVERCALL_RETRYLATER = -2147417846  # 0x8001010A
BUSY_CODES = {RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER}
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


def busy_code(exc: Exception) -> str | None:
    """Mã "Excel bận" nếu lỗi là do Excel bận, None nếu là lỗi khác.

    Khi Excel bận, nó từ chối cả bước tra tên (IDispatch.GetIDsOfNames) bằng 0x80010001; pywin32 (gọi trễ)
    nuốt lỗi này rồi ném AttributeError. Vì vậy AttributeError trên thuộc tính có thật cũng là "bận".
    """
    if isinstance(exc, pywintypes.com_error) and exc.hresult in BUSY_CODES:
        return hex(exc.hresult & 0xFFFFFFFF)
    if isinstance(exc, AttributeError):
        return "AttributeError (GetIDsOfNames bị từ chối)"
    return None


def read_with_retry(
    fn: Callable[[], object], attempts: int = 10, delay: float = 0.1
) -> tuple[object, list[str]]:
    """Gọi COM, nếu Excel bận thì thử lại tối đa `attempts` lần. Trả về (kết quả, danh sách mã bận gặp)."""
    errors: list[str] = []
    for _ in range(attempts):
        try:
            return fn(), errors
        except (pywintypes.com_error, AttributeError) as exc:
            code = busy_code(exc)
            if code is None:
                raise
            errors.append(code)
            time.sleep(delay)
    return None, errors


def is_excel_busy(excel: object) -> bool:
    """Excel đang sửa ô hoặc đang mở hộp thoại? Gọi GetIDsOfNames thô lên CommandBars — bị từ chối ở cả 2 trạng thái."""
    try:
        excel.CommandBars._oleobj_.GetIDsOfNames("GetPressedMso")
    except pywintypes.com_error as exc:
        return exc.hresult in BUSY_CODES
    except AttributeError:
        return True
    return False


def pump(seconds: float) -> None:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pythoncom.PumpWaitingMessages()
        time.sleep(0.01)


# ---------- Điều khiển phiên Excel riêng như người dùng (không dùng bàn phím toàn hệ thống) ----------


def find_grid_window(excel_hwnd: int) -> int:
    """Cửa sổ lưới ô của workbook (class EXCEL7) — nơi nhận phím khi người dùng gõ."""
    found: list[int] = []

    def visit(hwnd: int, _: object) -> bool:
        if win32gui.GetClassName(hwnd) == "EXCEL7":
            found.append(hwnd)
        return True

    win32gui.EnumChildWindows(excel_hwnd, visit, None)
    return found[0]


def post_keys(excel_hwnd: int, keys: list[tuple[int, str | None]]) -> None:
    """Gửi phím vào lưới ô của phiên Excel riêng: gắn luồng nhập, đặt focus vào lưới, PostMessage.

    Chỉ PostMessage (F2, WM_CHAR) thì Excel bỏ qua; phải đặt focus trong luồng của Excel trước.
    """
    grid = find_grid_window(excel_hwnd)
    excel_tid, _ = win32process.GetWindowThreadProcessId(grid)
    me = win32api.GetCurrentThreadId()
    win32process.AttachThreadInput(me, excel_tid, True)
    try:
        win32gui.SetFocus(grid)
        for vk, char in keys:
            scan = win32api.MapVirtualKey(vk, 0)
            win32gui.PostMessage(grid, win32con.WM_KEYDOWN, vk, 1 | (scan << 16))
            if char:
                win32gui.PostMessage(grid, win32con.WM_CHAR, ord(char), 1 | (scan << 16))
            win32gui.PostMessage(grid, win32con.WM_KEYUP, vk, 1 | (scan << 16) | (0xC0 << 24))
        time.sleep(0.3)
    finally:
        win32process.AttachThreadInput(me, excel_tid, False)


def start_editing(excel_hwnd: int, text: str) -> None:
    post_keys(excel_hwnd, [(win32con.VK_F2, None)] + [(ord(c.upper()), c) for c in text])


def stop_editing(excel_hwnd: int, commit: bool) -> None:
    key = (win32con.VK_RETURN, "\r") if commit else (win32con.VK_ESCAPE, None)
    post_keys(excel_hwnd, [key])


def find_dialogs(pid: int) -> list[int]:
    found: list[int] = []

    def visit(hwnd: int, _: object) -> bool:
        if (
            win32gui.GetClassName(hwnd) == EXCEL_DIALOG_CLASS
            and win32process.GetWindowThreadProcessId(hwnd)[1] == pid
        ):
            found.append(hwnd)
        return True

    win32gui.EnumWindows(visit, None)
    return found


def select_home_tab(excel_hwnd: int) -> None:
    tab = auto.ControlFromHandle(excel_hwnd).TabItemControl(AutomationId="TabHome", searchDepth=12)
    if tab.Exists(2):
        tab.GetSelectionItemPattern().Select()
        time.sleep(0.6)


def open_format_cells(excel_hwnd: int, pid: int) -> int | None:
    """Bấm nút mở rộng nhóm Number trên Ribbon bằng UIA Invoke (giống người dùng). Trả về hwnd hộp thoại.

    Mở bằng COM (Dialogs(...).Show) thì Excel KHÔNG bận với các lệnh COM khác — không giống thực tế.
    """

    def invoke() -> None:
        with auto.UIAutomationInitializerInThread():
            button = auto.ControlFromHandle(excel_hwnd).ButtonControl(
                AutomationId="FormatCellsNumberDialog", searchDepth=20
            )
            if button.Exists(2):
                button.GetInvokePattern().Invoke()

    threading.Thread(target=invoke, daemon=True).start()
    for _ in range(50):
        if dialogs := find_dialogs(pid):
            return dialogs[0]
        time.sleep(0.1)
    return None


def close_dialogs(pid: int) -> None:
    for _ in range(10):
        dialogs = find_dialogs(pid)
        if not dialogs:
            return
        for hwnd in dialogs:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.3)


# ---------- Phần 1: sự kiện ----------


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


# ---------- Phần 2: lệnh COM nào chạy được khi Excel bận ----------


def probe(fn: Callable[[], object]) -> str:
    try:
        value = fn()
    except (pywintypes.com_error, AttributeError) as exc:
        code = busy_code(exc)
        if code:
            return f"❌ bận: {code}"
        hresult = getattr(exc, "hresult", None)
        return f"❌ lỗi {hex(hresult & 0xFFFFFFFF) if hresult else type(exc).__name__}"
    return f"✅ {value!r}"[:60]


def part_states(excel: object) -> None:
    print("\nPhần 2 — lệnh COM khi Excel bận thật:")
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    ws.Range("A1").Value = 123
    ws.Range("A1").Select()
    hwnd = excel.Hwnd
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    select_home_tab(hwnd)
    probes: list[tuple[str, Callable[[], object]]] = [
        ("Excel.Ready", lambda: excel.Ready),
        ("is_excel_busy()", lambda: is_excel_busy(excel)),
        ("Đọc vùng A1:B2 (.Value)", lambda: ws.Range("A1:B2").Value),
        ("Đọc ActiveCell.Address", lambda: excel.ActiveCell.Address),
        ("Đọc ActiveSheet.Name", lambda: excel.ActiveSheet.Name),
        ("Ghi B1 = 5", lambda: setattr(ws.Range("B1"), "Value", 5) or "đã ghi"),
        ("CommandBars.GetPressedMso('Bold')", lambda: excel.CommandBars.GetPressedMso("Bold")),
    ]
    results: dict[str, list[str]] = {name: [] for name, _ in probes}

    def run_probes() -> None:
        for name, fn in probes:
            results[name].append(probe(fn))

    run_probes()  # bình thường

    start_editing(hwnd, "99")
    time.sleep(0.5)
    run_probes()  # đang sửa ô
    stop_editing(hwnd, commit=False)
    time.sleep(0.5)
    after_esc = ws.Range("A1").Value

    dialog = open_format_cells(hwnd, pid)
    time.sleep(0.5)
    if dialog:
        run_probes()  # đang mở hộp thoại
    else:
        for name in results:
            results[name].append("(không mở được hộp thoại)")
    close_dialogs(pid)
    time.sleep(0.5)

    print(f"  {'Lệnh':<36} | {'Bình thường':<22} | {'Đang sửa ô (F2)':<34} | Đang mở Format Cells")
    for name, row in results.items():
        print(f"  {name:<36} | {row[0]:<22} | {row[1]:<34} | {row[2]}")
    print(f"  Hộp thoại (class {EXCEL_DIALOG_CLASS}): {'tìm thấy' if dialog else 'KHÔNG thấy'}")
    print(f"  Sau Esc: A1 = {after_esc!r} (Esc bỏ phần đang gõ dở)")

    values, errors = read_with_retry(lambda: excel.ActiveSheet.Name, attempts=3)
    print(f"  read_with_retry(ActiveSheet.Name) sau khi hết bận: {values!r}, số lần bận {len(errors)}")
    wb.Close(SaveChanges=False)


# ---------- Chạy bền: monitor chạy luồng riêng, "người học giả lập" thao tác liên tục ----------


def soak(seconds: int) -> int:
    excel = win32com.client.DispatchEx("Excel.Application")  # luôn là phiên riêng
    hwnd = excel.Hwnd
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    stats: Counter[str] = Counter()
    busy_codes: Counter[str] = Counter()
    crashes: list[str] = []
    stop = threading.Event()
    try:
        excel.Visible = True
        excel.DisplayAlerts = False
        excel.WindowState = -4143
        place_on_secondary_monitor(hwnd)
        wb = excel.Workbooks.Add()
        wb.Worksheets(1).Range("A1:C3").Value = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        select_home_tab(hwnd)
        stream = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, excel._oleobj_)

        def monitor() -> None:
            """Giống luồng monitor/ của Desktop: nhận sự kiện + đọc lại vùng thay đổi + kiểm tra trạng thái bận."""
            pythoncom.CoInitialize()
            try:
                app = win32com.client.Dispatch(
                    pythoncom.CoGetInterfaceAndReleaseStream(stream, pythoncom.IID_IDispatch)
                )
                win32com.client.WithEvents(app, AppEvents)
                seen = 0
                while not stop.is_set():
                    pump(0.2)
                    try:
                        for _, kind, detail in EVENTS[seen:]:
                            stats[f"sự kiện {kind}"] += 1
                            if kind == "SheetChange":
                                sheet, address = detail.split("!")
                                _, errors = read_with_retry(
                                    lambda s=sheet, a=address: app.Worksheets(s).Range(a).Value, attempts=20
                                )
                                busy_codes.update(errors)
                                stats["đọc lại vùng thay đổi"] += 1
                        seen = len(EVENTS)
                        busy = is_excel_busy(app)
                        stats["lần kiểm tra bận"] += 1
                        stats["phát hiện bận"] += busy
                        _, errors = read_with_retry(lambda: app.ActiveSheet.Name, attempts=1)
                        busy_codes.update(errors)
                    except Exception as exc:  # noqa: BLE001 — chạy bền: ghi lại mọi lỗi, không được chết
                        crashes.append(f"{type(exc).__name__}: {exc}")
            finally:
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        ws = wb.Worksheets(1)
        rng = random.Random(7)
        end = time.perf_counter() + seconds
        next_report = time.perf_counter() + 60
        while time.perf_counter() < end:
            action = rng.choice(["ghi", "ghi", "chọn", "sửa ô", "sửa ô", "hộp thoại", "sheet"])
            stats[f"thao tác {action}"] += 1
            try:
                if action == "ghi":
                    ws.Range(f"{rng.choice('ABCDE')}{rng.randint(1, 20)}").Value = rng.randint(1, 999)
                elif action == "chọn":
                    ws.Range(f"B{rng.randint(1, 10)}:C{rng.randint(11, 20)}").Select()
                elif action == "sửa ô":
                    ws.Range(f"D{rng.randint(1, 20)}").Select()
                    start_editing(hwnd, str(rng.randint(10, 99)))
                    time.sleep(rng.uniform(1.0, 4.0))  # người học gõ dở, nghĩ…
                    stop_editing(hwnd, commit=rng.random() < 0.7)
                elif action == "hộp thoại":
                    if open_format_cells(hwnd, pid):
                        time.sleep(rng.uniform(1.0, 4.0))
                    close_dialogs(pid)
                elif action == "sheet":
                    if wb.Worksheets.Count < 4:
                        wb.Worksheets.Add()
                    else:
                        wb.Worksheets(rng.randint(1, wb.Worksheets.Count)).Activate()
                    ws = wb.Worksheets(1)
            except (pywintypes.com_error, AttributeError) as exc:
                stats["thao tác giả lập bị Excel từ chối"] += 1
                close_dialogs(pid)
                if busy_code(exc) is None:
                    stats[f"lỗi thao tác {type(exc).__name__}"] += 1
            time.sleep(rng.uniform(0.2, 1.0))
            if time.perf_counter() > next_report:
                next_report += 60
                print(f"  … còn {end - time.perf_counter():.0f} s; monitor crash: {len(crashes)}", flush=True)
        stop.set()
        thread.join(timeout=10)
        print(
            f"Chạy bền {seconds} s xong. Luồng monitor còn sống tới cuối: {'có' if not crashes else 'CÓ LỖI'}"
        )
        for key, count in sorted(stats.items()):
            print(f"  {key}: {count}")
        print(f"  mã bận gặp ở monitor (đã thử lại): {dict(busy_codes)}")
        print(f"  lỗi làm monitor phải bắt (crash nếu không bắt): {len(crashes)}")
        for line in crashes[:10]:
            print(f"    {line}")
        wb.Close(SaveChanges=False)
    finally:
        stop.set()
        close_dialogs(pid)
        excel.Quit()
    return 0 if not crashes else 1


def place_on_secondary_monitor(hwnd: int) -> None:
    """Đặt Excel lên màn hình phụ (nếu có) để ít làm phiền người đang dùng máy; không đặt luôn-trên-cùng."""
    monitors = [win32api.GetMonitorInfo(h) for h, _, _ in win32api.EnumDisplayMonitors()]
    others = [m for m in monitors if not m["Flags"] & win32con.MONITORINFOF_PRIMARY]
    left, top, right, bottom = (others or monitors)[0]["Work"]
    width, height = min(1500, right - left - 40), min(900, bottom - top - 40)
    win32gui.SetWindowPos(hwnd, 0, left + 20, top + 20, width, height, win32con.SWP_NOACTIVATE)
    time.sleep(1.0)


def attach(seconds: int) -> None:
    excel = win32com.client.GetActiveObject("Excel.Application")
    win32com.client.WithEvents(excel, AppEvents)
    print(f"Đã gắn vào Excel đang mở. Theo dõi {seconds} giây, hãy thao tác tự do…")
    reads = rejected = busy = 0
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pump(0.5)
        reads += 1
        busy += is_excel_busy(excel)
        _, errors = read_with_retry(lambda: excel.ActiveSheet.Name, attempts=1)
        rejected += bool(errors)
    print(
        f"Sự kiện nhận được: {len(EVENTS)}; lần đọc thử: {reads}; bị từ chối: {rejected}; lần thấy bận: {busy}"
    )
    for _, kind, detail in EVENTS[-15:]:
        print(f"  {kind}: {detail}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--attach", type=int, metavar="GIAY", help="Gắn vào Excel đang mở trong số giây này")
    parser.add_argument(
        "--soak", type=int, metavar="GIAY", help="Chạy bền trên phiên Excel riêng trong số giây này"
    )
    args = parser.parse_args()
    pythoncom.CoInitialize()
    try:
        if args.attach:
            attach(args.attach)
            return 0
        if args.soak:
            return soak(args.soak)
        excel = win32com.client.DispatchEx("Excel.Application")  # luôn là phiên riêng
        win32com.client.WithEvents(excel, AppEvents)
        pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
        try:
            excel.Visible = True  # hộp thoại cần cửa sổ hiển thị
            excel.DisplayAlerts = False
            excel.WindowState = -4143
            place_on_secondary_monitor(excel.Hwnd)
            part_events(excel)
            part_states(excel)
        finally:
            close_dialogs(pid)
            excel.Quit()
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
