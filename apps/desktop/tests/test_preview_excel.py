"""Chạy thử trên Excel thật: đọc file đang mở qua COM, làm bài như học viên, phiên tự chuyển bước (T7.6).

Cần Excel: chạy khi EXCEL_TESTS=1. Mở phiên Excel riêng (DispatchEx, ẩn) với BẢN SAO file đề tự soạn, ghi vào
bản sao đó để mô phỏng học viên; đóng phiên trong `finally`, không động vào Excel của người dùng.
"""

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from excel_core.checks import CheckStatus, reference_requests
from excel_core.readers import read_workbook
from excel_core.snapshot import snapshot_to_dict

pytestmark = [
    pytest.mark.excel,
    pytest.mark.skipif(os.environ.get("EXCEL_TESTS") != "1", reason="cần Excel thật: đặt EXCEL_TESTS=1"),
]

REPO = Path(__file__).resolve().parents[3]
B22 = REPO / "packages" / "excel_core" / "tests" / "fixtures" / "b22"
SCRIPT = json.loads(
    (REPO / "schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json").read_text(encoding="utf-8")
)


@pytest.fixture
def excel() -> Iterator[Any]:
    import pythoncom  # noqa: PLC0415
    import win32com.client  # noqa: PLC0415

    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    try:
        yield app
    finally:
        for index in range(app.Workbooks.Count, 0, -1):
            app.Workbooks(index).Close(SaveChanges=False)
        app.Quit()
        del app
        pythoncom.CoUninitialize()


def test_learner_actions_in_excel_move_the_preview_forward(excel: Any, tmp_path: Path):
    from tutor_desktop.agent.preview_session import PreviewSession  # noqa: PLC0415
    from tutor_desktop.monitor.excel_link import ExcelLink  # noqa: PLC0415

    copy = tmp_path / "b22-ban-1.xlsx"
    shutil.copy(B22 / "de.xlsx", copy)
    checks = [*SCRIPT["global_checks"], *(c for s in SCRIPT["steps"] for c in s["checks"])]
    files = {"starter": B22 / "de.xlsx", "solution": B22 / "dap-an.xlsx"}
    references = {
        source: snapshot_to_dict(read_workbook(files[source], request))
        for source, request in reference_requests(checks, SCRIPT["exercise"]["sheet"]).items()
    }
    session = PreviewSession(SCRIPT, references)
    link = ExcelLink(copy, excel_factory=lambda: excel)
    link.open()
    sheet = link.workbook.Worksheets("Bài 01")

    assert session.evaluate(link.snapshot(session.read_request())).status == CheckStatus.FAILED

    # Học viên gõ =C9+D9+E9: sai cách (không dùng SUM), gia sư phản hồi theo mã lỗi
    sheet.Range("F9").Formula = "=C9+D9+E9"
    session.note_change()
    wrong = session.evaluate(link.snapshot(session.read_request()))
    assert wrong.feedback is not None and wrong.feedback["code"] == "used_operator_instead"

    # Sửa lại bằng SUM: đạt bước 1; sao chép xuống: đạt bước 2; dòng tổng: xong bài
    sheet.Range("F9").Formula = "=SUM(C9:E9)"
    assert session.evaluate(link.snapshot(session.read_request())).advanced
    sheet.Range("F9").Copy(sheet.Range("F10:F19"))
    assert session.evaluate(link.snapshot(session.read_request())).advanced
    sheet.Range("C20").Formula = "=SUM(C9:C19)"
    sheet.Range("C20").Copy(sheet.Range("D20:F20"))
    last = session.evaluate(link.snapshot(session.read_request()))
    assert last.advanced and last.finished
    assert session.done == {s["id"] for s in SCRIPT["steps"]}

    # Gõ đè số liệu gốc: điều kiện toàn bài báo ngay
    sheet.Range("C9").Value = 1
    assert [
        v.check["type"] for v in session.evaluate(link.snapshot(session.read_request())).global_violations
    ] == ["data_unchanged"]
