"""T2.5 — Overlay PyQt6: khung chỉ vị trí ô và nút Ribbon, bám theo khi cuộn, phóng to, di chuyển cửa sổ,
đổi màn hình (nhiều màn hình khác tỉ lệ DPI).

Chạy:
  .venv\\Scripts\\python spikes\\t2-5-overlay\\overlay.py
  .venv\\Scripts\\python spikes\\t2-5-overlay\\overlay.py --qt-scale 0.8333   # mô phỏng tỉ lệ khác (150% x 0,8333 = 125%)

Một cửa sổ Excel riêng (dữ liệu tự tạo) hiện lên ~20 giây, có lúc chuyển sang màn hình phụ (nếu có).
Script tự chụp vùng cửa sổ Excel ở mỗi trường hợp vào spikes/t2-5-overlay/anh/. Không giả lập bàn phím/chuột.

Cách tính tọa độ:
  - Ô: COM Pane.PointsToScreenPixelsX/Y (pixel vật lý, đã tính zoom + cuộn) — khớp UIA ≤ 1 px (T2.4)
    NHƯNG CHỈ khi Excel nằm trên màn hình có DPI bằng DPI hệ thống. Ở màn hình khác DPI, COM sai (lệch cả
    trăm pixel, không theo một tỉ lệ) → dùng UIA cho ô đầu và ô cuối của phần vùng đang hiện.
  - Nút Ribbon: UIA, tìm theo AutomationId (idMso).
  - Qt vẽ theo pixel logic, MỖI MÀN HÌNH MỘT TỈ LỆ: tìm màn hình chứa điểm (MonitorFromPoint), rồi
    logic = (vật lý - gốc vật lý của màn hình) / devicePixelRatio của màn hình đó.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pythoncom
import uiautomation as auto
import win32api
import win32com.client
import win32con
import win32gui
import win32process
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QScreen
from PyQt6.QtWidgets import QApplication, QWidget

OUT = Path(__file__).resolve().parent / "anh"
TARGET_RANGE = "C4:D8"
RIBBON_BUTTON = "CommaStyle"
SWP_KEEP = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE


@dataclass
class Box:
    rect: QRect  # pixel logic của Qt, tính trong màn hình chứa nó
    label: str
    color: QColor


@dataclass
class Monitor:
    screen: QScreen
    device: str  # tên Windows, ví dụ DISPLAY1
    origin: tuple[int, int]  # góc trên trái, pixel vật lý
    dpr: float
    overlay: Overlay


class Overlay(QWidget):
    """Lớp phủ phủ kín MỘT màn hình: trong suốt, luôn trên cùng, chuột bấm xuyên qua."""

    def __init__(self, screen: QScreen) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # không hiện trên taskbar
            | Qt.WindowType.WindowTransparentForInput  # chuột/bàn phím đi xuyên qua
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # không cướp focus của Excel
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.boxes: list[Box] = []

    def paintEvent(self, _event: object) -> None:  # noqa: N802 — tên do Qt quy định
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for box in self.boxes:
            p.setPen(QPen(box.color, 3))
            p.drawRect(box.rect.adjusted(-2, -2, 2, 2))
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.fillRect(box.rect.left() - 2, box.rect.top() - 24, len(box.label) * 8 + 12, 20, box.color)
            p.setPen(QColor("white"))
            p.drawText(box.rect.left() + 4, box.rect.top() - 9, box.label)


def monitor_dpi(handle: object) -> int:
    dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
    ctypes.windll.shcore.GetDpiForMonitor(int(handle), 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
    return dpi_x.value


def build_monitors(app: QApplication, qt_scale: float) -> list[Monitor]:
    """Ghép QScreen của Qt với màn hình của Windows.

    Không ghép theo tên được: Qt có lúc đặt tên theo model màn hình ('HP P19v G4') thay vì DISPLAY3.
    Ghép theo kích thước vật lý và tỉ lệ: geometry logic x devicePixelRatio = kích thước vật lý,
    devicePixelRatio = DPI màn hình / 96 x QT_SCALE_FACTOR.
    """
    monitors: list[Monitor] = []
    screens = list(app.screens())
    for handle, _, _ in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(handle)
        x1, y1, x2, y2 = info["Monitor"]
        dpr = monitor_dpi(handle) / 96 * qt_scale

        def fits(s: QScreen, w: int = x2 - x1, h: int = y2 - y1, dpr: float = dpr) -> bool:
            g = s.geometry()
            return (
                abs(s.devicePixelRatio() - dpr) < 0.01
                and abs(g.width() * s.devicePixelRatio() - w) <= 2
                and abs(g.height() * s.devicePixelRatio() - h) <= 2
            )

        match = next((sc for sc in screens if sc.name() == info["Device"] and fits(sc)), None)
        match = match or next((sc for sc in screens if fits(sc)), None)
        if match is None:
            print(f"   (không ghép được màn hình {info['Device']} với QScreen nào)")
            continue
        screens.remove(match)
        monitors.append(Monitor(match, info["Device"], (x1, y1), match.devicePixelRatio(), Overlay(match)))
    return monitors


def monitor_at(monitors: list[Monitor], x: int, y: int) -> Monitor:
    handle = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST)
    device = win32api.GetMonitorInfo(handle)["Device"]
    return next(m for m in monitors if m.device == device)


def physical_to_local(mon: Monitor, x1: int, y1: int, x2: int, y2: int) -> QRect:
    ox, oy = mon.origin
    d = mon.dpr
    return QRect(round((x1 - ox) / d), round((y1 - oy) / d), round((x2 - x1) / d), round((y2 - y1) / d))


def com_rect(excel: object, address: str) -> tuple[int, int, int, int]:
    rng = excel.ActiveSheet.Range(address)
    pane = excel.ActiveWindow.ActivePane
    return (
        pane.PointsToScreenPixelsX(rng.Left),
        pane.PointsToScreenPixelsY(rng.Top),
        pane.PointsToScreenPixelsX(rng.Left + rng.Width),
        pane.PointsToScreenPixelsY(rng.Top + rng.Height),
    )


def uia_cell_rect(window: auto.Control, address: str) -> tuple[int, int, int, int] | None:
    item = window.DataItemControl(searchDepth=30, Name=address)
    if not item.Exists(0, 0):
        return None
    r = item.BoundingRectangle
    return r.left, r.top, r.right, r.bottom


def cell_rect_physical(
    excel: object, window: auto.Control, address: str
) -> tuple[tuple[int, int, int, int], str]:
    """Tọa độ vật lý của vùng ô. Trả về (tọa độ, cách tính)."""
    com = com_rect(excel, address)
    win_dpi = ctypes.windll.user32.GetDpiForWindow(excel.Hwnd)
    sys_dpi = ctypes.windll.user32.GetDpiForSystem()
    if win_dpi == sys_dpi:
        return com, "COM"
    # Màn hình khác DPI hệ thống: COM sai và sai KHÔNG theo một tỉ lệ (ngang x1,5 nhưng chiều cao dòng lệch
    # kiểu khác), nên không quy đổi được. Dùng UIA: ô đầu và ô cuối của phần vùng đang hiện trên màn hình.
    visible = excel.Intersect(excel.ActiveSheet.Range(address), excel.ActiveWindow.VisibleRange)
    if visible is None:
        return com, "vùng không hiện trên màn hình"
    first = visible.Cells(1, 1).Address.replace("$", "")
    last = visible.Cells(visible.Rows.Count, visible.Columns.Count).Address.replace("$", "")
    r1, r2 = uia_cell_rect(window, first), uia_cell_rect(window, last)
    if r1 is None or r2 is None:
        return com, "COM (UIA không thấy ô, có thể lệch)"
    return (r1[0], r1[1], r2[2], r2[3]), f"UIA {first}..{last} (COM sai ở màn hình khác DPI hệ thống)"


def ribbon_rect_physical(window: auto.Control, automation_id: str) -> tuple[int, int, int, int] | None:
    ctrl = window.Control(searchDepth=30, AutomationId=automation_id)
    if not ctrl.Exists(0, 0):
        return None
    r = ctrl.BoundingRectangle
    return r.left, r.top, r.right, r.bottom


def click_through(x: int, y: int, excel_pid: int) -> str:
    """Cửa sổ nhận chuột tại điểm (x, y) — phải là Excel, không phải overlay."""
    hwnd = win32gui.WindowFromPoint((x, y))
    if not hwnd:
        return "không có cửa sổ"
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    owner = "Excel" if pid == excel_pid else ("overlay (SAI)" if pid == os.getpid() else f"PID {pid}")
    return f"{win32gui.GetClassName(hwnd)} của {owner}"


def pump(app: QApplication, seconds: float) -> None:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()


def snapshot(app: QApplication, mon: Monitor, excel: object, name: str) -> None:
    pump(app, 0.4)
    left, top, right, bottom = win32gui.GetWindowRect(excel.Hwnd)
    r = physical_to_local(mon, left, top, right, bottom)
    pix = mon.screen.grabWindow(0, r.x(), r.y(), r.width(), r.height())
    pix = pix.scaledToWidth(1100, Qt.TransformationMode.SmoothTransformation)
    pix.save(str(OUT / f"{name}.png"))
    print(f"   đã chụp anh/{name}.png")


def move_excel(excel: object, x: int, y: int, w: int, h: int) -> None:
    """Đặt cửa sổ Excel theo pixel vật lý (tiến trình đã DPI-aware nhờ Qt).

    Gọi hai lần: khi sang màn hình khác DPI, Windows tự co giãn kích thước cửa sổ theo tỉ lệ mới.
    """
    for _ in range(2):
        win32gui.SetWindowPos(excel.Hwnd, win32con.HWND_TOPMOST, x, y, w, h, win32con.SWP_NOACTIVATE)
        time.sleep(1.0)  # Excel vẽ lại theo DPI của màn hình mới


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--qt-scale", type=float, help="QT_SCALE_FACTOR, để mô phỏng tỉ lệ màn hình khác")
    args = parser.parse_args()
    prefix = ""
    if args.qt_scale:
        os.environ["QT_SCALE_FACTOR"] = str(args.qt_scale)
        prefix = f"qt{args.qt_scale:g}-"
    app = QApplication(sys.argv)
    monitors = build_monitors(app, args.qt_scale or 1.0)
    primary = next(m for m in monitors if m.origin == (0, 0))
    print("Màn hình:")
    for m in monitors:
        geo = m.screen.geometry()
        print(
            f"   {m.device} (Qt: {m.screen.name()!r}): gốc vật lý {m.origin}, devicePixelRatio={m.dpr}, "
            f"Qt geometry=({geo.x()},{geo.y()},{geo.width()}x{geo.height()})"
        )

    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    try:
        excel.Visible = True
        excel.DisplayAlerts = False
        excel_pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
        wb = excel.Workbooks.Add()
        ws = wb.Worksheets(1)
        ws.Range("B3:D3").Value = [["Mặt hàng", "Số lượng", "Đơn giá"]]
        ws.Range("B4:D8").Value = [[f"Hàng {i}", i * 125, i * 10.5] for i in range(1, 6)]
        excel.WindowState = -4143  # xlNormal
        ox, oy = primary.origin
        move_excel(excel, ox + 60, oy + 60, 1500, 900)
        window = auto.ControlFromHandle(excel.Hwnd)
        home = window.TabItemControl(searchDepth=12, AutomationId="TabHome")
        if home.Exists(0, 0):
            home.GetSelectionItemPattern().Select()
            time.sleep(0.6)
        for m in monitors:
            m.overlay.show()
            m.overlay.raise_()
        exstyle = win32gui.GetWindowLong(int(primary.overlay.winId()), win32con.GWL_EXSTYLE)
        print(
            f"Overlay: WS_EX_TRANSPARENT={bool(exstyle & win32con.WS_EX_TRANSPARENT)}, "
            f"WS_EX_LAYERED={bool(exstyle & win32con.WS_EX_LAYERED)}, WS_EX_TOPMOST={bool(exstyle & win32con.WS_EX_TOPMOST)}, "
            f"WS_EX_TOOLWINDOW={bool(exstyle & win32con.WS_EX_TOOLWINDOW)}"
        )

        def draw(case: str) -> None:
            cell, method = cell_rect_physical(excel, window, TARGET_RANGE)
            rib = ribbon_rect_physical(window, RIBBON_BUTTON)
            mon = monitor_at(monitors, (cell[0] + cell[2]) // 2, (cell[1] + cell[3]) // 2)
            for m in monitors:
                m.overlay.boxes = []
            boxes = [Box(physical_to_local(mon, *cell), f"Vùng {TARGET_RANGE}", QColor("#d62828"))]
            if rib:
                boxes.append(Box(physical_to_local(mon, *rib), "Comma Style", QColor("#1d4ed8")))
            mon.overlay.boxes = boxes
            for m in monitors:
                m.overlay.update()
                m.overlay.raise_()
            pump(app, 0.3)
            cx, cy = (cell[0] + cell[2]) // 2, (cell[1] + cell[3]) // 2
            dpi_win = ctypes.windll.user32.GetDpiForWindow(excel.Hwnd)
            print(
                f"{case}: màn hình {mon.device} (dpr {mon.dpr}), GetDpiForWindow(Excel)={dpi_win} "
                f"(= {dpi_win / 96:.2f}x); ô {TARGET_RANGE} vật lý={cell} [{method}]; nút={rib}"
            )
            first, last = TARGET_RANGE.split(":")
            uia_first, uia_last = uia_cell_rect(window, first), uia_cell_rect(window, last)
            if uia_first and uia_last:
                truth = (*uia_first[:2], *uia_last[2:])
                err = max(abs(a - b) for a, b in zip(cell, truth, strict=True))
                raw = com_rect(excel, TARGET_RANGE)
                raw_err = max(abs(a - b) for a, b in zip(raw, truth, strict=True))
                print(
                    f"   đối chiếu UIA {TARGET_RANGE}={truth} → lệch {err} px (nếu dùng COM thô: lệch {raw_err} px)"
                )
            print(f"   chuột tại giữa khung ô rơi vào: {click_through(cx, cy, excel_pid)}")
            if rib:
                rx, ry = (rib[0] + rib[2]) // 2, (rib[1] + rib[3]) // 2
                print(f"   chuột tại giữa khung nút rơi vào: {click_through(rx, ry, excel_pid)}")
            snapshot(app, mon, excel, prefix + case)

        draw("1-ban-dau")
        excel.ActiveWindow.Zoom = 150
        draw("2-zoom-150")
        excel.ActiveWindow.Zoom = 100
        excel.ActiveWindow.ScrollRow = 3
        excel.ActiveWindow.ScrollColumn = 2
        draw("3-cuon-trang")
        excel.ActiveWindow.ScrollRow = 1
        excel.ActiveWindow.ScrollColumn = 1
        move_excel(excel, ox + 200, oy + 120, 1500, 900)
        draw("4-di-chuyen-cua-so")
        others = [m for m in monitors if m is not primary and m.dpr != primary.dpr]
        if others:
            other = others[0]
            mx, my = other.origin
            move_excel(excel, mx + 60, my + 60, 1500, 900)
            draw("5-man-hinh-phu")
            excel.ActiveWindow.Zoom = 130
            excel.ActiveWindow.ScrollRow = 2
            draw("6-man-hinh-phu-zoom-cuon")
        else:
            print("Không có màn hình phụ khác tỉ lệ — bỏ qua trường hợp 5")

        for m in monitors:
            m.overlay.hide()
        win32gui.SetWindowPos(excel.Hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, SWP_KEEP)
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
