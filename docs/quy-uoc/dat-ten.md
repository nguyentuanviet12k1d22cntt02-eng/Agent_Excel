# Quy tắc đặt tên

## 1. Nguyên tắc chung

1. **Tên file và thư mục chỉ dùng ký tự ASCII**: không dấu tiếng Việt, không khoảng trắng. Tên có dấu hay khoảng trắng dễ lỗi khi đóng gói `.exe`, khi chạy trên CI và khi gõ lệnh.
2. **Code đặt tên tiếng Anh**, theo chuẩn của từng ngôn ngữ.
3. **Tài liệu và dữ liệu tiếng Việt đặt tên tiếng Việt không dấu**, viết thường, nối bằng dấu `-` (kebab-case). Ví dụ: `ke-hoach-trien-khai.md`.
4. Tên phải nói được **nội dung**, không dùng `test2.py`, `new_file.py`, `final_final.md`.
5. Không dùng ngày tháng trong tên file. Lịch sử đã có git lo.

## 2. Bảng tra nhanh

| Loại | Kiểu | Ví dụ đúng | Ví dụ sai |
|---|---|---|---|
| Thư mục ứng dụng, thư mục tài liệu | kebab-case | `apps/word-desktop/`, `docs/quy-uoc/` | `apps/WordDesktop/`, `docs/Quy ước/` |
| Package Python (tên import) | snake_case | `tutor_desktop`, `excel_core` | `tutorDesktop`, `excel-core` |
| Tên phân phối trong `pyproject.toml` | kebab-case | `tutor-desktop`, `excel-core` | `tutor_desktop` |
| Module Python | snake_case | `com_reader.py`, `hint_policy.py` | `ComReader.py`, `comreader.py` |
| File test Python | `test_<module>.py` | `test_com_reader.py` | `com_reader_test.py`, `test1.py` |
| Component React | PascalCase `.tsx` | `ScriptEditor.tsx` | `scriptEditor.tsx` |
| File TypeScript khác (hook, tiện ích, API) | camelCase `.ts` | `useScripts.ts`, `apiClient.ts` | `use_scripts.ts` |
| Thư mục trong `apps/web/src/` | kebab-case | `features/script-editor/` | `features/ScriptEditor/` |
| JSON Schema | `<ten>.schema.json` | `tutor-script.schema.json` | `schema.json` |
| Tài liệu trong `docs/` | kebab-case tiếng Việt không dấu | `luat-goi-y.md` | `LUAT_GOI_Y.md`, `luật gợi ý.md` |
| Tài liệu kết quả của một task | `t<gđ>-<số>-<mô-tả>.md` | `t2-7-bao-cao-spike.md` | `T2.7_bao_cao.md` |
| Thư mục spike | `t<gđ>-<số>-<mô-tả>/` | `spikes/t2-4-uia-ribbon/` | `spikes/T2.4 UIA/` |
| Thư mục bài tập mẫu | `b<2 chữ số>-<mô-tả>/` | `samples/b09-du-lieu-dang-so/` | `samples/Bài 09/` |
| Script PowerShell | kebab-case `.ps1` | `build-exe.ps1` | `BuildExe.ps1` |
| Biến môi trường | UPPER_SNAKE_CASE | `LLM_API_KEY` | `llmApiKey` |
| Nhánh git | `feature/<mã-task>-<mô-tả>` | `feature/T2.4-uia-ribbon` | `viet-dev`, `fix` |

**Riêng mã task trong nhánh git và commit vẫn viết `T2.4`** (có chữ hoa, có dấu chấm), giống hệt mã trong kế hoạch để dễ tìm. Còn trong **tên file, tên thư mục** thì viết `t2-4`, vì dấu chấm trong tên dễ bị hiểu nhầm là phần mở rộng.

## 3. Đặt tên trong code Python

| Thành phần | Kiểu | Ví dụ |
|---|---|---|
| Biến, hàm, phương thức | snake_case | `read_range_values()`, `hint_level` |
| Lớp | PascalCase | `TeachingAgent`, `WorkbookSnapshot` |
| Hằng số | UPPER_SNAKE_CASE | `MAX_RETRY`, `DEFAULT_IDLE_SECONDS` |
| Thành phần nội bộ (không dùng ngoài module) | thêm `_` ở đầu | `_parse_address()` |
| Kiểu lỗi tự định nghĩa | kết thúc bằng `Error` | `ExcelBusyError`, `ScriptValidationError` |
| Hàm trả về `bool` | bắt đầu bằng `is_`, `has_`, `can_` | `is_step_done()`, `has_autofilter()` |

Thuật ngữ trong code dùng **một từ tiếng Anh cố định** cho mỗi khái niệm của đề tài, để cả nhóm không mỗi người gọi một kiểu:

| Khái niệm | Từ dùng trong code |
|---|---|
| Kịch bản hướng dẫn | `script` |
| Bước | `step` |
| Điều kiện kiểm chứng | `check` |
| Gợi ý, cấp gợi ý | `hint`, `hint_level` |
| Tín hiệu kích hoạt hướng dẫn | `signal` |
| Vùng mục tiêu | `target` |
| Bài tập | `exercise` |
| File đề / file kết quả mẫu | `starter_file` / `solution_file` |
| Giáo trình | `textbook` |
| Học liệu (giáo trình + bài tập) | `material` |
| Phiên học, tiến độ, nhật ký | `session`, `progress`, `log` |
| Ảnh chụp workbook | `snapshot` |
| Sự kiện quan sát | `observation` |

Thêm khái niệm mới thì bổ sung vào bảng này trước khi dùng.

## 4. Bài tập mẫu (`samples/`)

```
samples/b09-du-lieu-dang-so/
├─ de.xlsx            file đề học viên nhận được
├─ dap-an.xlsx        file kết quả mẫu
├─ de-bai.pdf         đề bài (hoặc .docx)
├─ giao-trinh.pdf     chương giáo trình tương ứng (hoặc .docx)
└─ thong-tin.md       nguồn, nhóm kỹ năng, sheet nào là đề / đáp án, ghi chú
```

Repo là public, nên **chỉ đưa vào `samples/` những bài trung tâm đồng ý công khai** hoặc bài nhóm tự soạn. Bài chưa được phép thì đặt trong `samples/_local/` cùng cấu trúc trên. Thư mục này nằm trong `.gitignore` và chia sẻ trong nhóm qua kênh riêng.
