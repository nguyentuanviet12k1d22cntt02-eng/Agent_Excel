"""So màu "#RRGGBB" có ngưỡng: màu theme do openpyxl quy đổi lệch ±1 mỗi kênh so với Excel."""

COLOR_TOLERANCE = 3  # mỗi kênh 0–255


def colors_close(actual: str | None, expected: str | None, tolerance: int = COLOR_TOLERANCE) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    a, e = actual.lstrip("#"), expected.lstrip("#")
    return all(abs(int(a[i : i + 2], 16) - int(e[i : i + 2], 16)) <= tolerance for i in (0, 2, 4))
