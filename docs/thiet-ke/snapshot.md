# Mô hình snapshot workbook và trạng thái quan sát

**Task:** T3.3 · **Báo cáo:** mục 3.4, 4.4 · **Trạng thái:** v1, chờ GVHD rà soát (T3.8)
**Code sẽ đặt ở:** `packages/excel_core/src/excel_core/snapshot/` (kiểu dữ liệu), `readers/openpyxl_reader.py`, `readers/com_reader.py` (GĐ4)
**Dựa trên số đo:** [T2.1](../../spikes/t2-1-com-doc-du-lieu/README.md), [T2.3](../../spikes/t2-3-com-doi-tuong-kho/README.md), [T2.2](../../spikes/t2-2-com-su-kien/README.md)

## 1. Vì sao cần một mô hình chung

Cùng một điều kiện kiểm chứng (ví dụ `number_format`) phải chạy ở hai nơi:

| Nơi | Đọc từ | Để làm gì |
|---|---|---|
| Backend | File `.xlsx` bằng **openpyxl** | So sánh file đề với đáp án (diff); tự kiểm kịch bản AI: điều kiện đạt trên đáp án, không đạt trên đề (T4.5) |
| Desktop | Excel **đang chạy** bằng **COM** | Kiểm bài làm của học viên theo thời gian thực |

Nếu mỗi bên tự viết điều kiện thì sẽ có lúc Backend nói "đạt" mà Desktop nói "không đạt". Vì vậy: **hai bộ đọc khác nhau → cùng một snapshot → cùng một bộ `checks/`**. Mọi khác biệt giữa openpyxl và COM được xử lý **trong bộ đọc** (chuẩn hóa), không lọt vào `checks/`.

## 2. Nguyên tắc

1. **Snapshot theo phạm vi, không chụp cả workbook.** Bộ đọc nhận một *yêu cầu đọc* (vùng nào, nhóm thuộc tính nào) suy ra từ các điều kiện của bước hiện tại. Lý do: đọc định dạng từng ô qua COM mất ~2 ms/ô (T2.1); cả trang tính thì quá chậm.
2. **Đọc theo vùng, không theo từng ô**: giá trị và công thức cả vùng một lần (nhanh hơn ~1.000 lần, T2.1).
3. **Chuẩn hóa theo ý nghĩa**: màu → `#RRGGBB`; mã định dạng số → mã en-US **và** thông tin đã phân tích (loại, số chữ số thập phân, dấu nghìn); ngày dựng sẵn về một loại "ngày ngắn".
4. **Bất biến (immutable)**: snapshot là ảnh chụp tại một thời điểm, `dataclass(frozen=True)`. So sánh hai snapshot không bao giờ bị thay đổi giữa chừng.
5. **Không phụ thuộc Windows**: `excel_core/snapshot/` không import `win32com` (quy tắc cấu trúc 3.4). Chỉ `com_reader.py` import, và import trong hàm.

## 3. Yêu cầu đọc (`ReadRequest`)

```python
class PropertyGroup(StrEnum):
    VALUES = "values"  # giá trị, kiểu dữ liệu
    FORMULAS = "formulas"  # công thức A1 + R1C1
    NUMBER_FORMAT = "number_format"
    STYLE = "style"  # font, nền, viền, căn lề  (chậm qua COM: chỉ vùng nhỏ)
    STRUCTURE = "structure"  # ô gộp, dòng/cột ẩn, kích thước
    FILTER = "filter"  # AutoFilter, dòng đang hiện
    PAGE_SETUP = "page_setup"  # hướng, khổ, lề, đầu/cuối trang (COM: chỉ khi cần)
    CHARTS = "charts"


@dataclass(frozen=True)
class RangeRequest:
    sheet: str
    range: str  # "F10:F14" — một vùng liền kề
    groups: frozenset[PropertyGroup]


@dataclass(frozen=True)
class ReadRequest:
    ranges: tuple[RangeRequest, ...]
    sheet_groups: frozenset[PropertyGroup] = frozenset()  # filter, page_setup, charts theo sheet
    include_sheet_list: bool = False  # cho sheet_exists
```

Mỗi loại điều kiện khai báo nó cần nhóm nào (`checks/<ten>.py` có hằng `REQUIRES`). Ví dụ `number_format` → `{NUMBER_FORMAT}`; `formula_consistent` → `{FORMULAS}`; `sorted_by` → `{VALUES}` trên cả bảng. Teaching Agent gộp yêu cầu của mọi điều kiện trong bước hiện tại và `global_checks` thành **một** `ReadRequest`.

## 4. Kiểu dữ liệu

```python
@dataclass(frozen=True)
class WorkbookSnapshot:
    source: Literal["openpyxl", "com"]
    taken_at: datetime
    exercise_id: str | None  # thuộc tính tùy chỉnh tutor_exercise_id
    sheet_names: tuple[str, ...]
    active_sheet: str | None  # COM: ActiveSheet; openpyxl: sheet đang chọn khi lưu
    sheets: Mapping[str, SheetSnapshot]  # chỉ các sheet có trong ReadRequest


@dataclass(frozen=True)
class SheetSnapshot:
    name: str
    cells: Mapping[str, CellSnapshot]  # khóa: "F10" (A1, không $)
    merged: tuple[str, ...]  # ("A1:D1", ...)
    hidden_rows: frozenset[int]
    hidden_cols: frozenset[str]
    row_heights: Mapping[int, float]  # điểm (pt)
    col_widths: Mapping[str, float]  # đơn vị ký tự như Excel
    autofilter: AutoFilterInfo | None
    page_setup: PageSetupInfo | None
    charts: tuple[ChartInfo, ...]


@dataclass(frozen=True)
class CellSnapshot:
    value: CellValue  # None | float | str | bool | datetime | ErrorValue
    value_kind: Literal["empty", "number", "text", "logical", "date", "error"]
    formula: str | None  # "=SUM(C9:E9)", cú pháp tiếng Anh
    formula_r1c1: str | None  # "=SUM(RC[-3]:RC[-1])"
    number_format: NumberFormatInfo | None
    font: FontInfo | None
    fill: FillInfo | None
    border: BorderInfo | None
    alignment: AlignmentInfo | None


@dataclass(frozen=True)
class NumberFormatInfo:
    code: str  # mã en-US, ví dụ "#,##0.00" (COM: LCID 1033)
    category: Literal[
        "general",
        "number",
        "currency",
        "accounting",
        "percent",
        "date",
        "time",
        "text",
        "scientific",
        "fraction",
        "custom",
    ]
    decimals: int | None
    thousands_separator: bool
    date_pattern: str | None  # đã chuẩn hóa, "short_date" cho định dạng ngày dựng sẵn


@dataclass(frozen=True)
class FontInfo:
    name: str
    size: float
    bold: bool
    italic: bool
    underline: bool
    color: str | None  # "#RRGGBB"


@dataclass(frozen=True)
class FillInfo:
    color: str | None  # None = không tô


@dataclass(frozen=True)
class BorderInfo:
    top: str | None
    bottom: str | None
    left: str | None
    right: str | None  # kiểu: "thin", "medium"…


@dataclass(frozen=True)
class AlignmentInfo:
    horizontal: str
    vertical: str
    wrap_text: bool


@dataclass(frozen=True)
class AutoFilterInfo:
    range: str
    columns: Mapping[str, tuple[str, ...]]  # tiêu đề cột → tiêu chí (đã bỏ dấu "=" đầu của COM)
    visible_rows: frozenset[int] | None


@dataclass(frozen=True)
class PageSetupInfo:
    orientation: Literal["portrait", "landscape"]
    paper_size: str  # "A4", "A5", "letter"…
    margins_cm: tuple[float, float, float, float]
    fit_to_pages: tuple[int | None, int | None]
    center_horizontally: bool
    print_area: str | None
    header_footer: Mapping[str, str]  # "header_center" → "&P"…


@dataclass(frozen=True)
class ChartInfo:
    chart_type: str  # "column", "bar", "line", "pie"…
    title: str | None
    data_ranges: tuple[str, ...]  # tách từ =SERIES(...) hoặc từ XML biểu đồ
```

Trường nào không có trong `ReadRequest` thì là `None` / rỗng. Điều kiện gặp trường cần mà là `None` → **lỗi lập trình** (yêu cầu đọc thiếu), không phải "không đạt".

## 5. Mỗi trường đọc từ đâu, chuẩn hóa thế nào

| Trường | openpyxl | COM (pywin32) | Chuẩn hóa |
|---|---|---|---|
| `value` | Mở file **2 lần**: `data_only=True` lấy giá trị đã tính, `data_only=False` lấy công thức | `Range.Value` cả vùng (tuple 2 chiều) | `pywintypes.datetime` → `datetime` thường; số nguyên dạng `float` giữ `float`; lỗi `#DIV/0!` → `ErrorValue`; chuỗi rỗng → `None` |
| `value_kind` | Theo kiểu Python + định dạng ngày | Như trên | Số có định dạng ngày → `date`. Số lưu dạng chữ (`"1250"`) → `text` (để `value_type` bắt lỗi `stored_as_text`) |
| `formula` | `cell.value` khi `data_only=False` | `Range.Formula` cả vùng | Luôn cú pháp tiếng Anh (COM `Formula` không bị dịch theo vùng, T1.2) |
| `formula_r1c1` | **Tự chuyển A1 → R1C1** (viết ở `excel_core`, T4.4) | `Range.FormulaR1C1` | Bỏ khoảng trắng thừa; chữ hoa tên hàm |
| `number_format.code` | `cell.number_format` | `NumberFormat` gọi **Invoke LCID 1033** (quy tắc code 2.3 mục 6) | Mã dựng sẵn id 14 (`mm-dd-yy` ở openpyxl, `m/d/yyyy` ở COM) → `date_pattern="short_date"` (T2.1) |
| `number_format.category…` | Phân tích `code` bằng cùng một hàm `parse_number_format()` | Như openpyxl | Phần định dạng số dương (trước `;` đầu tiên) quyết định số chữ số thập phân và dấu nghìn. `_(* #,##0_)` → `accounting`. Có `%` → `percent` |
| `font`, `fill`, `border`, `alignment` | `cell.font`, `cell.fill`… | `Range.Font.Bold`… **từng ô** (~2 ms/ô) | Màu: theme + tint (openpyxl) và BGR long (COM) → `#RRGGBB`. Căn lề `xlHAlignRight=-4152` → `"right"` |
| `merged` | `ws.merged_cells.ranges` | `Range.MergeArea` của các ô trong vùng | Địa chỉ A1 không `$` |
| `hidden_rows/cols`, kích thước | `row_dimensions`, `column_dimensions` | `Rows(i).Hidden`, `RowHeight`, `ColumnWidth` | Ngưỡng sai số khi so kích thước (đơn vị cột khác nhau giữa hai nguồn ~0,1) |
| `autofilter` | `ws.auto_filter` (`colId` đếm từ 0) | `AutoFilter.Filters(i).Criteria1` | Cột theo **tiêu đề**; bỏ `=` đầu tiêu chí (T2.3) |
| `page_setup` | `ws.page_setup`, `ws.oddHeader` | `PageSetup.*` — chỉ đọc khi bước cần; đọc lần đầu 15–19 ms (T2.3) | Lề inch → cm |
| `charts` | `ws._charts` (loại, tiêu đề, vùng tham chiếu) | `ChartObjects(i).Chart` (`ChartType`, `SeriesCollection().Formula`) | `ChartType` 51/57/4/5… → tên loại; vùng tách từ `=SERIES(...)` |
| `exercise_id` | `wb.custom_doc_props["tutor_exercise_id"]` | `CustomDocumentProperties("tutor_exercise_id")` | — |

**Lưu ý openpyxl:** giá trị ô công thức chỉ có khi file **đã được Excel lưu** (giá trị cache). File đáp án do giảng viên tải lên đều thỏa. File tạo bằng code (không qua Excel) thì phải mở bằng Excel và lưu lại trước (đã gặp ở T1.2).

## 6. Đọc lại khi có thay đổi (Desktop)

```
SheetChange(sheet, vùng_đổi)
   └─ vùng_đổi ∩ (vùng mục tiêu của bước hiện tại ∪ vùng của global_checks) ≠ ∅ ?
        ├─ không → chỉ ghi nhật ký (có thể là tín hiệu off_target)
        └─ có    → ReadRequest của bước → snapshot mới → chạy checks
```

- **Ngân sách thời gian:** từ `SheetChange` tới khi có kết quả kiểm chứng ≤ **300 ms** (đo ở T8.x). Ước lượng: đọc giá trị/công thức vùng < 5 ms, định dạng vùng 5–20 ô 10–40 ms, chạy checks < 10 ms.
- **Excel bận** (đang sửa ô, mở hộp thoại): đọc vùng ô vẫn chạy (T2.2), nhưng giá trị là trước khi học viên gõ. Không cần chụp lại; `SheetChange` sẽ báo khi học viên Enter.
- Thay đổi định dạng **không** sinh `SheetChange`. Vì vậy với bước có điều kiện định dạng, Desktop chụp lại **khi học viên bấm nút trên Ribbon / đóng hộp thoại** (theo dõi bằng UIA) và **định kỳ 1 giây khi bước hiện tại có điều kiện định dạng**, chỉ trên vùng mục tiêu (vài ô, ~10 ms).

## 7. Trạng thái quan sát (`Observation`)

`monitor/` của Desktop biến mọi thứ quan sát được thành **sự kiện quan sát** đã chuẩn hóa, gửi cho Teaching Agent qua hàng đợi (Agent không biết COM, UIA là gì):

| Sự kiện | Dữ liệu | Nguồn (T2.x) |
|---|---|---|
| `workbook_opened` | `exercise_id`, tên file | COM `WorkbookOpen` + thuộc tính tùy chỉnh (T2.3) |
| `cells_changed` | `sheet`, `range` | COM `SheetChange` (T2.2) |
| `selection_changed` | `sheet`, `range` | COM `SheetSelectionChange` |
| `sheet_activated` | `sheet` | COM `SheetActivate` |
| `format_may_have_changed` | `sheet`, `range` (vùng đang chọn) | UIA: bấm nút Ribbon nhóm định dạng; đóng hộp thoại Format Cells |
| `dialog_opened` / `dialog_closed` | `title`, `tab`, `selected_item` | Win32 `bosa_sdm_XL9` + UIA (T2.4) |
| `excel_busy_changed` | `busy: bool` | `is_excel_busy()` (T2.2) |
| `print_requested` | — | COM `WorkbookBeforePrint` (T2.4) |
| `excel_foreground_changed` | `foreground: bool` | Win32 `GetForegroundWindow` (T2.5) |
| `tick` | thời điểm | Đồng hồ 1 giây, để Agent tính tín hiệu `idle` |

```python
@dataclass(frozen=True)
class Observation:
    kind: ObservationKind
    at: datetime
    data: Mapping[str, object]
```

Snapshot và Observation đều ghi được vào **nhật ký thực hành** (dạng JSON gọn) để phân tích sau (đề cương: các bước học viên hay vướng).

## 8. Kiểm thử

- **Cùng một file, hai bộ đọc, cùng snapshot:** mở `dap-an.xlsx` bằng openpyxl và bằng COM (trên máy Windows có Excel), so sánh từng trường đã chuẩn hóa. Test COM đánh dấu `@pytest.mark.excel`, CI (không có Excel) bỏ qua.
- Test `parse_number_format()` với bảng mã định dạng thật lấy từ 25 bài.
- Test chuyển A1 → R1C1 với các mẫu ở b18, b22 (tương đối, tuyệt đối, hỗn hợp, vùng, khác sheet).
