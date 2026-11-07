import tutor_backend


def test_package_imports() -> None:
    assert tutor_backend.__version__


def test_backend_can_use_excel_core_snapshot() -> None:
    # T4.1: Backend dùng chung kiểu snapshot của excel_core
    from excel_core.snapshot import PropertyGroup, RangeRequest

    assert RangeRequest("Bài 01", "C9:E19", frozenset({PropertyGroup.VALUES})).range == "C9:E19"
