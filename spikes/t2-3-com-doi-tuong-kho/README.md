# T2.3 — Đối tượng khó: bộ lọc, sắp xếp, trang in, biểu đồ, thuộc tính tùy chỉnh

**Mục tiêu:** biết COM và openpyxl đọc được gì, nhanh không, với các đối tượng ngoài giá trị ô.

**Chạy:** `.venv\Scripts\python spikes\t2-3-com-doi-tuong-kho\hard_objects.py`
Làm trên bản sao bài b15 trong thư mục tạm (cần `samples/_local/b15-loc-du-lieu/`), không sửa file mẫu.

## Kết quả (máy của Việt, 07/11/2026)

| Đối tượng | COM đọc | Thời gian | openpyxl đọc file đã lưu | Ghi chú |
|---|---|---|---|---|
| **Bộ lọc** (lọc Mã SP = MH003) | ✅ vùng, cột đang lọc, tiêu chí `=MH003`, số dòng đang hiện (6) | 6–8 ms | ✅ vùng, cột lọc (`colId` đếm từ 0), giá trị `MH003`, dòng bị ẩn (13) | Hai nguồn khớp nhau. COM ghi tiêu chí có dấu `=` ở đầu |
| **Sắp xếp** (Số lượng giảm dần) | ⚠️ `Sort.SortFields` **không tin được** để biết đã sắp hay chưa | 17 ms | — (file không lưu "đã sắp") | **Kiểm chứng phải đọc thứ tự dữ liệu.** Xem bẫy `Orientation` bên dưới |
| **Trang in** (A5, ngang, số trang giữa đầu trang) | ✅ hướng, khổ, đầu trang `&P` | Ghi 3 thuộc tính: **440–560 ms**. Đọc: lần đầu 15–19 ms, các lần sau < 1 ms | ✅ hướng, khổ, đầu trang | Chậm khi **ghi**, đọc thì chấp nhận được (có bộ nhớ đệm). Tắt `PrintCommunication` khi đọc: ~1 ms |
| **Biểu đồ** (cột, tiêu đề) | ✅ loại (51 = cột nhóm), tiêu đề, công thức chuỗi `=SERIES(...)` | 9–28 ms | ✅ loại `barChart`, hướng `col`, tiêu đề, vùng dữ liệu | Đủ để kiểm "có biểu đồ đúng loại, đúng dữ liệu, có tiêu đề" |
| **Thuộc tính tùy chỉnh** (mã bài `tutor_exercise_id`) | ✅ đọc/ghi | ~2 ms | ✅ đọc/ghi | **Hai chiều đều được**: Backend (openpyxl) ghi lúc phát hành → Desktop (COM) đọc khi học viên mở file. openpyxl lưu lại file **không làm mất biểu đồ** |

## Bẫy phát hiện được

1. **`Range.Sort` không truyền `Orientation` có thể sắp theo chiều NGANG** (đổi chỗ các cột), kể cả khi `Sheet.Sort.Orientation` đang là 1. Đã kiểm chứng: không truyền thì cột Số lượng bị thay bằng cột ngày; truyền `Orientation=1` thì đúng (65 → 62,25 → 40). Đã thêm vào [quy-tac-code.md](../../docs/quy-uoc/quy-tac-code.md) mục 2.3.
2. **Không giả định vị trí cột giữa các sheet hoặc giữa các bài.** Tìm cột theo tiêu đề. Kịch bản (T3.2) nên tham chiếu cột theo tiêu đề hoặc theo vùng đã khai báo.
3. Với Office object (`CustomDocumentProperties.Add`), pywin32 **không nhận tham số theo tên**, phải truyền theo vị trí.

## Kết luận cho thiết kế

- `autofilter`, `page_setup`, `header_footer`, `chart`: đọc được bằng **cả hai nguồn** → làm được điều kiện kiểm chứng (cập nhật cột "Nguồn đọc" trong [danh-muc-dieu-kien.md](../../docs/thiet-ke/danh-muc-dieu-kien.md)).
- `sorted_by`: kiểm bằng **thứ tự dữ liệu** + so từng dòng với dữ liệu gốc (bắt lỗi chỉ sắp một cột làm lệch dòng).
- **Mã bài lưu trong thuộc tính tùy chỉnh `tutor_exercise_id`** là cách khả thi để Desktop nhận ra bài (T7.4).
- `PageSetup`: Desktop chỉ đọc khi bước hiện tại liên quan trang in (đúng như dự kiến ở T1.6); đọc thì không chậm như lo ngại, chậm là ghi.
