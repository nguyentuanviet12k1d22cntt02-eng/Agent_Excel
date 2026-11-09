# Quy tắc code

Các quy tắc có thể kiểm tra tự động đều do **ruff** (Python) và **CI trên GitHub** kiểm tra. Pull Request nào CI báo đỏ thì không merge.

## 1. Chung cho mọi ngôn ngữ

1. **Một hàm làm một việc.** Hàm dài quá khoảng 50 dòng thì tách ra.
2. **Không lặp code.** Code giống nhau ở 2 nơi thì gom thành hàm; dùng ở cả Backend và Desktop thì đưa vào `packages/excel_core`.
3. **Không viết cứng** đường dẫn, địa chỉ máy chủ, API key, số "ma thuật". Đưa vào cấu hình (`.env`) hoặc hằng số có tên.
4. **Comment giải thích *vì sao*, không giải thích *cái gì*.** Code đã nói nó làm gì rồi.
5. **Không để lại code chết**: code bị comment, `print` gỡ lỗi, import thừa.
6. **Mã nguồn UTF-8, xuống dòng LF** (đã cấu hình trong `.editorconfig` và `.vscode/`).
7. Tên gọi theo [quy tắc đặt tên](dat-ten.md), thuật ngữ theo bảng ở mục 3 của file đó.

## 2. Python

### 2.1. Định dạng và kiểm tra

- Định dạng bằng `ruff format`, kiểm tra bằng `ruff check`. Cấu hình ở `ruff.toml`, dòng tối đa 110 ký tự.
- VS Code tự định dạng khi lưu file nếu đã cài extension **Ruff** (được gợi ý trong `.vscode/extensions.json`).
- Chạy trước khi commit:

  ```powershell
  ruff format .
  ruff check . --fix
  pytest
  ```

### 2.2. Viết code

| Quy tắc | Đúng | Sai |
|---|---|---|
| Có type hint cho tham số và giá trị trả về của hàm public | `def read_range(sheet: str, address: str) -> list[list[object]]:` | `def read_range(sheet, address):` |
| Docstring tiếng Việt cho module, lớp, hàm public | `"""Đọc giá trị một vùng ô, trả về mảng 2 chiều."""` | (không có) |
| Dùng `logging`, không dùng `print` (ruff chặn `print`) | `logger.info("Đã kết nối Excel %s", version)` | `print("connected")` |
| Bắt lỗi cụ thể, không bắt `Exception` chung (ruff chặn) | `except pywintypes.com_error as exc:` | `except Exception:` / `except:` |
| Dùng `pathlib`, không dùng `os.path` (ruff chặn) | `Path(base) / "cache" / name` | `os.path.join(base, "cache", name)` |
| Dữ liệu có cấu trúc dùng `dataclass` hoặc Pydantic, không dùng `dict` tùy tiện | `@dataclass class Step: ...` | `step = {"id": ..., "chk": ...}` |
| Import tuyệt đối từ tên package | `from excel_core.diff import diff_workbooks` | `from ..diff import *` |
| Đọc/ghi file luôn chỉ rõ mã hóa | `path.read_text(encoding="utf-8")` | `open(path).read()` |
| Điểm khởi động (`__main__.py`, script) có in ra console thì chuyển stdout sang UTF-8. Console Windows mặc định là cp1252, in tiếng Việt sẽ **crash** | `sys.stdout.reconfigure(encoding="utf-8")` ở đầu `main()` | in tiếng Việt khi chưa cấu hình |

Ghi log: mỗi module tạo logger riêng ở đầu file.

```python
import logging

logger = logging.getLogger(__name__)
```

### 2.3. Quy tắc riêng cho Desktop

1. **Mọi lệnh COM tới Excel chạy trên một luồng riêng** (luồng của `monitor/`), không chạy trên luồng giao diện. Luồng giao diện Qt mà bị chặn thì cửa sổ gia sư sẽ treo.
2. **Excel đang bận thì thử lại có giới hạn.** Khi gặp lỗi Excel từ chối lệnh (người học đang gõ trong ô hoặc đang mở hộp thoại), thử lại sau một khoảng ngắn, tối đa vài lần, rồi bỏ qua lượt đọc đó. **Không** vòng lặp vô hạn. Lỗi "bận" có hai dạng (đã kiểm chứng ở T2.2):
   - `pywintypes.com_error` với mã `0x80010001` hoặc `0x8001010A`;
   - **`AttributeError`** khi gọi trễ (late binding) một thuộc tính có thật, ví dụ `excel.ActiveSheet.Name`: Excel từ chối bước tra tên `GetIDsOfNames` và pywin32 đổi lỗi đó thành `AttributeError`. Hàm thử lại phải bắt cả loại này.

   Đọc giá trị vùng ô (`Range.Value`) vẫn chạy khi Excel bận và trả về giá trị **trước** khi người học gõ. Biết Excel có đang bận hay không: **không dùng `Excel.Ready`** (vẫn `True` khi đang sửa ô); dùng `is_excel_busy()` trong `spikes/t2-2-com-su-kien/events_busy.py`.
3. **Không bao giờ thay đổi workbook của người học.** Desktop chỉ đọc. Việc duy nhất được ghi là mã bài khi phát hành, và việc đó do Backend làm trên file đề, trước khi học viên nhận file.
4. **Không để sót tiến trình Excel.** Phiên Excel do code tự mở (`DispatchEx`) thì phải `Quit()` trong khối `finally`. Excel của người học thì không được đóng.
5. `ui/` nhận dữ liệu qua **signal/slot** của Qt, không gọi COM, không gọi API trực tiếp.
6. **Đọc/ghi `NumberFormat` qua COM luôn dùng LCID 1033 (en-US).** pywin32 mặc định gọi COM theo cài đặt vùng của người dùng; trên máy định dạng Việt Nam (dấu thập phân `,`), Excel dịch mã định dạng: ghi `"#,##0"` bị lưu thành `"#.##0"`, đọc ra cũng bị dịch. Gọi `Invoke(dispid, 1033, ...)` thì đọc/ghi đúng mã chuẩn, còn hiển thị trên Excel vẫn theo kiểu Việt Nam. Đã kiểm chứng ở T1.2 (`scripts/build_solutions.py`). `Formula` không bị ảnh hưởng (luôn dùng cú pháp tiếng Anh).
7. **Không dùng địa chỉ ghép nhiều vùng** kiểu `Range("A1:A5,C1:C5")`: Excel báo lỗi trên máy định dạng Việt Nam. Thao tác từng vùng riêng, hoặc dùng `Application.Union`.
8. **Gọi `Range.Sort` luôn truyền `Orientation=1`** (trên xuống dưới). Không truyền thì Excel có thể sắp theo chiều ngang và xáo trộn các cột. Đã kiểm chứng ở T2.3.
9. **Không suy ra "đã sắp xếp" từ `Sheet.Sort.SortFields`**; kiểm bằng thứ tự dữ liệu thật. Không giả định vị trí cột, tìm cột theo tiêu đề.
10. **Tọa độ ô trên màn hình:** dùng COM `PointsToScreenPixelsX/Y` **chỉ khi** `GetDpiForWindow(Excel) == GetDpiForSystem()`. Khác nhau (Excel nằm ở màn hình phụ khác tỉ lệ) thì COM lệch hàng trăm pixel, phải dùng UIA `DataItem.BoundingRectangle`. Đã kiểm chứng ở T2.5.
11. **Tìm nút Ribbon theo AutomationId (`idMso`), không theo tên hiển thị.** Tên đổi theo ngôn ngữ Office và có thể khác tên quen gọi (nút AutoSum có tên "Sum"). Danh mục mã: `spikes/t2-4-uia-ribbon/danh-muc-idmso.md`.
12. **Overlay: mỗi màn hình một cửa sổ**, quy đổi pixel vật lý → logic theo `devicePixelRatio` của chính màn hình chứa điểm cần vẽ.
13. **Không đọc `Range.MergeCells`.** Chỉ cần đọc thuộc tính này, Excel tự nới vùng chọn đang có của người học cho trọn ô gộp (bài 06: đang chọn cột H thì thành B:J vì tiêu đề gộp B9:J9), dù code không gọi `Select`. Muốn biết ô gộp thì dùng `Range.MergeArea` (từng ô) hoặc `Range.Value(11)` (XML), như `_merged_areas` trong `excel_core/readers/com_reader.py`. Đã kiểm chứng ở T7.2. Bấm chuột vào tiêu đề cột thì Excel **không** nới theo ô gộp, còn `Range.Select` qua COM thì có.

### 2.4. Quy tắc riêng cho Backend

1. Router trong `api/` chỉ làm 3 việc: nhận dữ liệu, gọi `services`, trả kết quả. Không viết nghiệp vụ trong router.
2. Dữ liệu vào/ra API luôn khai báo bằng Pydantic schema trong `schemas/`. Không trả thẳng model ORM ra ngoài.
3. Cấu hình đọc qua `pydantic-settings` (`core/config.py`), không gọi `os.environ` rải rác.
4. **Prompt cho LLM đặt trong `ai/prompts/` thành file riêng**, không viết chuỗi dài lẫn trong code. Nhờ vậy sửa prompt không phải sửa logic, và lịch sử thay đổi prompt có trong git (cần cho báo cáo).
5. Kết quả AI sinh ra **luôn được kiểm tra theo lược đồ** trước khi lưu (T4.5). Không tin tưởng output của LLM.

### 2.5. Test

- Dùng **pytest**. Test đặt trong `tests/` của từng project, cấu trúc thư mục giống `src/`.
- **Mỗi module có logic phải có test.** Bắt buộc với `packages/excel_core` vì cả Backend và Desktop phụ thuộc vào nó.
- Tên hàm test mô tả tình huống: `test_diff_detects_new_formula_in_cell()`.
- Viết theo 3 phần: chuẩn bị → thực hiện → kiểm tra.
- Test cần Excel thật (COM) thì đánh dấu `@pytest.mark.excel`, để CI có thể bỏ qua khi máy chạy CI không có Excel.
- File Excel nhỏ dùng riêng cho test đặt trong `tests/fixtures/` của project đó. Bài tập đầy đủ thì lấy từ `samples/`.

## 3. TypeScript / React (`apps/web`)

Công cụ thiết lập ở T6.1 (xem [apps/web/README.md](../../apps/web/README.md)). Quy tắc:

1. **TypeScript chế độ `strict`**, không dùng `any`. Chưa biết kiểu thì dùng `unknown` rồi kiểm tra.
2. **Chỉ dùng function component và hook.** Không dùng class component.
3. **Tổ chức theo tính năng**: `src/features/<tinh-nang>/` chứa component, hook, gọi API của tính năng đó. Thành phần dùng chung đặt trong `src/components/`.
4. **Kiểu dữ liệu API sinh tự động từ đặc tả OpenAPI** của Backend, không tự gõ lại.
5. Định dạng bằng **Prettier**, kiểm tra bằng **ESLint** (`typescript-eslint` mức `strictTypeChecked`). Trước khi commit: `npm run format`, `npm run lint`, `npm test`.
6. **Gọi API qua `src/api/client.ts`** (`api.GET(...)` rồi `unwrap`), không gọi `fetch` trực tiếp: client lo token, làm mới token và đổi lỗi `problem+json` thành `ApiError` có thông báo tiếng Việt.
7. Dữ liệu từ máy chủ đọc bằng **TanStack Query** (`useQuery`, `useMutation`); không tự giữ bản sao trong `useState`.
8. Chữ trên giao diện tiếng Việt có dấu; tên biến, hàm, component tiếng Anh.

## 4. JSON Schema (`schemas/`)

1. Lược đồ kịch bản là "hợp đồng" giữa 3 ứng dụng. **Thay đổi làm hỏng kịch bản cũ thì phải tăng phiên bản** (`v1/` → `v2/`), không sửa đè.
2. Mọi trường có `description` bằng tiếng Việt.
3. Mỗi phiên bản có thư mục `examples/` chứa kịch bản mẫu hợp lệ. Test của `excel_core` kiểm tra các ví dụ này luôn hợp lệ.

## 5. Bảo mật

1. Không commit API key, mật khẩu, token. Đặt trong `.env` theo mẫu `.env.example`.
2. **Repo đang public:** trước khi `git add`, xem lại danh sách file (`git status`). Không đưa lên dữ liệu cá nhân của học viên, giảng viên, hay tài liệu trung tâm chưa đồng ý công khai.
3. Lỡ commit key thì báo ngay trưởng nhóm và đổi key trên trang nhà cung cấp. Xóa commit là chưa đủ.
