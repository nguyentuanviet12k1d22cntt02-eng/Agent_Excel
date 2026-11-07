import tutor_desktop


def test_package_imports() -> None:
    assert tutor_desktop.__version__


def test_desktop_can_use_excel_core_snapshot() -> None:
    # T4.1: Desktop dùng chung kiểu snapshot của excel_core (không kéo theo win32com)
    import sys

    from excel_core.snapshot import CellSnapshot

    assert CellSnapshot().is_empty
    assert "win32com" not in sys.modules or "excel_core.readers.com_reader" in sys.modules
