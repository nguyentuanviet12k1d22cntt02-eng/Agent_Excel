from pathlib import Path

import pytest

from tutor_backend.services.storage import FileStore, StorageError
from tutor_backend.services.uploads import detect_type


def test_store_saves_relative_paths(tmp_path: Path):
    store = FileStore(tmp_path)
    relative = store.save("exercises/abc/de.xlsx", b"PK...")
    assert relative == "exercises/abc/de.xlsx"
    assert store.path(relative).read_bytes() == b"PK..."
    store.delete_dir("exercises/abc")
    assert not (tmp_path / "exercises" / "abc").exists()


@pytest.mark.parametrize("bad", ["../ngoai-kho.txt", "a/../../ngoai-kho.txt"])
def test_store_blocks_path_traversal(tmp_path: Path, bad: str):
    with pytest.raises(StorageError):
        FileStore(tmp_path / "kho").save(bad, b"x")


def test_detect_type_by_content():
    assert detect_type(b"%PDF-1.7 ...") == "pdf"
    assert detect_type(b"khong phai file") is None
    assert detect_type(b"PK\x03\x04 hong") is None
