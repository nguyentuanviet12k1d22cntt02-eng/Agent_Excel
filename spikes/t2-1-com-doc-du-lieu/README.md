# T2.1 — Đọc dữ liệu qua Excel COM

**Mục tiêu:** đo tốc độ đọc giá trị, công thức, định dạng qua COM; kiểm tra COM và openpyxl đọc cùng một file có ra cùng kết quả không.

**Chạy:**

```powershell
.venv\Scripts\python spikes\t2-1-com-doc-du-lieu\read_benchmark.py samples\_local\b09-du-lieu-dang-so\dap-an.xlsx
```

Script tự mở một phiên Excel riêng (không đụng Excel đang mở), đóng khi xong. Đối số file là tùy chọn.

## Kết quả (máy của Việt, Excel 16.0 build 20326, Windows vi-VN, 07/11/2026)

**Tốc độ đọc 1.000 ô (100 dòng × 10 cột):**

| Cách đọc | Thời gian | Mỗi ô |
|---|---|---|
| Từng ô: `.Value` | 502 ms | 0,50 ms |
| Từng ô: `.Formula` | 545 ms | 0,54 ms |
| Từng ô: `NumberFormat` (LCID 1033) | 153 ms | 0,15 ms |
| Từng ô: `Font.Bold` | **1.854 ms** | **1,85 ms** |
| Cả vùng 1 lần: `.Value` | **0,6 ms** | 0,0006 ms |
| Cả vùng 1 lần: `.Formula` | 1,7 ms | 0,0017 ms |
| Cả vùng 1 lần: `NumberFormat` | 0,3 ms | trả về `None` nếu các ô khác định dạng |

**Đối chiếu COM ↔ openpyxl** trên `b09/dap-an.xlsx` (222 ô có dữ liệu):

- Giá trị, công thức: **khớp 100%** (sau khi đổi `pywintypes.datetime` về `datetime` thường).
- Mã định dạng số: khớp 217/222 ô. 5 ô lệch đều là **định dạng ngày dựng sẵn số 14 (Short Date)**: openpyxl đọc ra `mm-dd-yy`, COM đọc ra `m/d/yyyy`. Excel hiển thị định dạng này theo cài đặt vùng của máy.

## Kết luận

1. **Không bao giờ đọc từng ô trên cả trang tính.** Đọc giá trị và công thức cả vùng một lần: nhanh hơn khoảng **1.000 lần**.
2. **Thuộc tính định dạng (font, nền, viền) chỉ đọc cho vùng mục tiêu của bước hiện tại.** Đọc `Font.Bold` từng ô mất gần 2 ms/ô; một vùng 5 ô mất 10 ms là chấp nhận được, cả trang thì không.
3. `NumberFormat` cả vùng: đọc một lần trước; nếu ra `None` (vùng lẫn định dạng) thì mới đọc từng ô.
4. **Snapshot (T3.3) phải chuẩn hóa định dạng ngày dựng sẵn** (`mm-dd-yy`, `m/d/yyyy`, id 14…) về cùng một loại "ngày ngắn", không so nguyên chuỗi. Bộ đọc openpyxl và bộ đọc COM khác nhau đúng ở chỗ này.
5. Đọc `NumberFormat` qua LCID 1033 cho kết quả **trùng với openpyxl** (trừ định dạng ngày ở trên), xác nhận quy tắc ở `quy-tac-code.md` mục 2.3.
