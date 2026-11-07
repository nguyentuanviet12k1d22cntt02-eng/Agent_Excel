"""T2.5 — Overlay PyQt6: khung chỉ vị trí ô và nút Ribbon, bám theo khi cuộn, phóng to, di chuyển cửa sổ.

Chạy:  .venv\\Scripts\\python spikes\\t2-5-overlay\\overlay.py
Một cửa sổ Excel riêng (dữ liệu tự tạo) hiện lên ~15 giây. Script tự chụp vùng cửa sổ Excel ở mỗi trường hợp
vào spikes/t2-5-overlay/anh/ để kiểm chứng bằng mắt. Không giả lập bàn phím/chuột.

Cách tính tọa độ:
  - Ô: COM Pane.PointsToScreenPixelsX/Y (pixel vật lý, đã tính zoom + cuộn) — khớp UIA ≤ 1 px (T2.4).
  - Nút Ribbon: UIA, tìm theo AutomationId (idMso).
  - Qt vẽ theo pixel logic → chia cho devicePixelRatio của màn hình (150% → 1,5).
"""

from __future__ import annotations

import ctypes
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pythoncom
import uiautomation as auto
import win32com.client
import win32con
import win32gui
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

OUT = Path(__file__).resolve().parent / "anh"
TARGET_RANGE = "C4:D8"
RIBBON_BUTTON = "CommaStyle"


@dataclass
class Box:
    rect: QRect  # pixel logic của Qt
    label: str
    color: QColor


class Overlay(QWidget):
    """Lớp phủ toàn màn hình: trong suốt, luôn trên cùng, chuột bấm xuyên qua."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # không hiện trên taskbar
            | Qt.WindowType.WindowTransparentForInput  # chuột/bàn phím đi xuyên qua
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # không cướp focus của Excel
        self.setGeometry(QApplication.primaryScreen().geometry())
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


def physical_to_logical(x1: int, y1: int, x2: int, y2: int, dpr: float) -> QRect:
    return QRect(round(x1 / dpr), round(y1 / dpr), round((x2 - x1) / dpr), round((y2 - y1) / dpr))


def cell_rect_physical(excel: object, address: str) -> tuple[int, int, int, int]:
    rng = excel.ActiveSheet.Range(address)
    pane = excel.ActiveWindow.ActivePane
    return (
        pane.PointsToScreenPixelsX(rng.Left),
        pane.PointsToScreenPixelsY(rng.Top),
        pane.PointsToScreenPixelsX(rng.Left + rng.Width),
        pane.PointsToScreenPixelsY(rng.Top + rng.Height),
    )


def ribbon_rect_physical(window: auto.Control, automation_id: str) -> tuple[int, int, int, int] | None:
    ctrl = window.Control(searchDepth=30, AutomationId=automation_id)
    if not ctrl.Exists(0, 0):
        return None
    r = ctrl.BoundingRectangle
    return r.left, r.top, r.right, r.bottom


def snapshot(app: QApplication, overlay: Overlay, excel: object, name: str, dpr: float) -> None:
    overlay.update()
    end = time.perf_counter() + 0.4
    while time.perf_counter() < end:
        app.processEvents()
    left, top, right, bottom = win32gui.GetWindowRect(excel.Hwnd)
    screen = QApplication.primaryScreen()
    pix = screen.grabWindow(
        0, round(left / dpr), round(top / dpr), round((right - left) / dpr), round((bottom - top) / dpr)
    )
    pix = pix.scaledToWidth(1100, Qt.TransformationMode.SmoothTransformation)
    pix.save(str(OUT / f"{name}.png"))
    print(f"   đã chụp anh/{name}.png")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    app = QApplication(sys.argv)
    dpr = QApplication.primaryScreen().devicePixelRatio()
    overlay = Overlay()

    pythoncom.CoInitialize()
    excel = win32com.client.DispatchEx("Excel.Application")
    try:
        excel.Visible = True
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Add()
        ws = wb.Worksheets(1)
        ws.Range("B3:D3").Value = [["Mặt hàng", "Số lượng", "Đơn giá"]]
        ws.Range("B4:D8").Value = [[f"Hàng {i}", i * 125, i * 10.5] for i in range(1, 6)]
        excel.WindowState = -4143  # xlNormal
        excel.Left, excel.Top, excel.Width, excel.Height = 40, 40, 700, 460
        time.sleep(1.0)
        window = auto.ControlFromHandle(excel.Hwnd)
        home = window.TabItemControl(searchDepth=12, AutomationId="TabHome")
        if home.Exists(0, 0):
            home.GetSelectionItemPattern().Select()
            time.sleep(0.6)

        # Đưa Excel lên trên cùng TẠM THỜI (không cần quyền giành focus), để ảnh chụp chỉ có Excel
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        win32gui.SetWindowPos(excel.Hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flags)
        overlay.show()
        overlay.raise_()
        exstyle = win32gui.GetWindowLong(int(overlay.winId()), win32con.GWL_EXSTYLE)
        print(f"Màn hình: devicePixelRatio={dpr}, DPI hệ thống={ctypes.windll.user32.GetDpiForSystem()}")
        print(
            f"Overlay: WS_EX_TRANSPARENT (chuột xuyên qua)={bool(exstyle & win32con.WS_EX_TRANSPARENT)}, "
            f"WS_EX_LAYERED={bool(exstyle & win32con.WS_EX_LAYERED)}, WS_EX_TOPMOST={bool(exstyle & win32con.WS_EX_TOPMOST)}, "
            f"WS_EX_NOACTIVATE/TOOLWINDOW={bool(exstyle & win32con.WS_EX_TOOLWINDOW)}"
        )
        print(f"Cửa sổ đang có focus: {win32gui.GetWindowText(win32gui.GetForegroundWindow())!r}")

        def draw(case: str) -> None:
            boxes = [
                Box(
                    physical_to_logical(*cell_rect_physical(excel, TARGET_RANGE), dpr),
                    f"Vùng {TARGET_RANGE}",
                    QColor("#d62828"),
                )
            ]
            rib = ribbon_rect_physical(window, RIBBON_BUTTON)
            if rib:
                boxes.append(Box(physical_to_logical(*rib, dpr), "Comma Style", QColor("#1d4ed8")))
            overlay.boxes = boxes
            overlay.raise_()
            print(
                f"{case}: ô {TARGET_RANGE} (pixel vật lý) = {cell_rect_physical(excel, TARGET_RANGE)}; nút Ribbon = {rib}"
            )
            snapshot(app, overlay, excel, case, dpr)

        draw("1-ban-dau")
        excel.ActiveWindow.Zoom = 150
        draw("2-zoom-150")
        excel.ActiveWindow.Zoom = 100
        excel.ActiveWindow.ScrollRow = 3
        excel.ActiveWindow.ScrollColumn = 2
        draw("3-cuon-trang")
        excel.ActiveWindow.ScrollRow = 1
        excel.ActiveWindow.ScrollColumn = 1
        excel.Left, excel.Top = 160, 90
        time.sleep(0.5)
        draw("4-di-chuyen-cua-so")

        overlay.hide()
        win32gui.SetWindowPos(excel.Hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
