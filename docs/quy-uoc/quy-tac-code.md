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
2. **Excel đang bận thì thử lại có giới hạn.** Khi gặp lỗi Excel từ chối lệnh (người học đang gõ trong ô hoặc đang mở hộp thoại), thử lại sau một khoảng ngắn, tối đa vài lần, rồi bỏ qua lượt đọc đó. **Không** vòng lặp vô hạn.
3. **Không bao giờ thay đổi workbook của người học.** Desktop chỉ đọc. Việc duy nhất được ghi là mã bài khi phát hành, và việc đó do Backend làm trên file đề, trước khi học viên nhận file.
4. **Không để sót tiến trình Excel.** Phiên Excel do code tự mở (`DispatchEx`) thì phải `Quit()` trong khối `finally`. Excel của người học thì không được đóng.
5. `ui/` nhận dữ liệu qua **signal/slot** của Qt, không gọi COM, không gọi API trực tiếp.

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

Thiết lập công cụ ở T6.1. Quy tắc áp dụng từ đầu:

1. **TypeScript chế độ `strict`**, không dùng `any`. Chưa biết kiểu thì dùng `unknown` rồi kiểm tra.
2. **Chỉ dùng function component và hook.** Không dùng class component.
3. **Tổ chức theo tính năng**: `src/features/<tinh-nang>/` chứa component, hook, gọi API của tính năng đó. Thành phần dùng chung đặt trong `src/components/`.
4. **Kiểu dữ liệu API sinh tự động từ đặc tả OpenAPI** của Backend, không tự gõ lại.
5. Định dạng bằng **Prettier**, kiểm tra bằng **ESLint**.

## 4. JSON Schema (`schemas/`)

1. Lược đồ kịch bản là "hợp đồng" giữa 3 ứng dụng. **Thay đổi làm hỏng kịch bản cũ thì phải tăng phiên bản** (`v1/` → `v2/`), không sửa đè.
2. Mọi trường có `description` bằng tiếng Việt.
3. Mỗi phiên bản có thư mục `examples/` chứa kịch bản mẫu hợp lệ. Test của `excel_core` kiểm tra các ví dụ này luôn hợp lệ.

## 5. Bảo mật

1. Không commit API key, mật khẩu, token. Đặt trong `.env` theo mẫu `.env.example`.
2. **Repo đang public:** trước khi `git add`, xem lại danh sách file (`git status`). Không đưa lên dữ liệu cá nhân của học viên, giảng viên, hay tài liệu trung tâm chưa đồng ý công khai.
3. Lỡ commit key thì báo ngay trưởng nhóm và đổi key trên trang nhà cung cấp. Xóa commit là chưa đủ.
