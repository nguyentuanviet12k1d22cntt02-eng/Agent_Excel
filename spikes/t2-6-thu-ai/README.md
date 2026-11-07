# T2.6 — Thử AI sinh kịch bản từ diff, có tự kiểm

**Mục tiêu:** xem LLM (`mercury-3`, Inception Labs) sinh kịch bản từ **diff file đề ↔ đáp án** tốt tới đâu so với kịch bản viết tay; thử sớm cơ chế tự kiểm của T4.5.

**Chạy:** `.venv\Scripts\python spikes\t2-6-thu-ai\generate_script.py b09` (hoặc `b22`, thêm `--model mercury-2` để đổi mô hình)
Cần `samples/_local/` (T1.2) và key trong `apps/backend/.env`. Kịch bản sinh ra lưu ở `samples/_local/<bài>/kich-ban-ai.json` (không lên git).

**Quy trình:** diff (openpyxl, gom ô liền nhau thành vùng) → đề bài trong ô + text box + sheet hướng dẫn → LLM với structured output → **tự kiểm**: mỗi điều kiện phải đạt trên đáp án và **không** đạt trên đề → **độ phủ**: mọi vùng thay đổi có điều kiện kiểm tới.

## Kết quả (07/11/2026, `mercury-3`)

| | b09 (định dạng số) | b22 (hàm SUM) |
|---|---|---|
| Vùng thay đổi trong diff | 11 | 19 |
| Thời gian · token vào/ra | 5,4 s · 2.114 / 2.479 | 11,2 s · 1.530 / 6.612 |
| Số bước (kịch bản tay) | 4 (tay: 6) | 4 (tay: 3) |
| **Độ phủ diff** | **11/11** | **19/19** |
| **Điều kiện hợp lệ khi tự kiểm** | **7/12**: 5 điều kiện "đạt sẵn trên đề" (vô nghĩa) | **7/7** |
| Bịa số liệu trong gợi ý | ❌ **Có** | Không |

### Lỗi của AI ở b09 (phát hiện quan trọng nhất)

1. **Bịa giá trị cụ thể trong gợi ý cấp 4**: "F10 = 120, F11 = 80…" (thật: 10, 5, 25, 8, 15); "G11 = 650.25" (thật: 605.25); "I14 = 0.03" (thật: 0).
2. **Bảo học viên gõ số vào cột Thành tiền**, trong khi cột này đã có công thức `=F*G`. Làm theo là phá hỏng bài. Nguyên nhân: diff chỉ cho AI thấy H10:H14 *đổi định dạng*, không cho biết H10:H14 *đã có công thức cần giữ*.
3. **Trỏ sai cột nguồn**: "bảng số liệu thô ở vùng D18:D22" (đúng: F18:F22).

Bước tự kiểm điều kiện **không** bắt được các lỗi này, vì chúng nằm trong chữ của gợi ý.

### Điểm AI làm tốt

- Hiểu Comma Style để lại 2 số lẻ, phải bấm Decrease Decimal 2 lần (b09); dùng chốt điền để sao chép công thức (b22). Khớp kịch bản viết tay.
- Thẻ yêu cầu đúng tinh thần "phải đạt gì".
- Tuân thủ lược đồ JSON 100% (structured output).

### Lỗi do đầu vào, không phải do AI

- **b22, bước "định dạng dòng 20"**: ban đầu nghĩ do file đáp án nhóm tạo có định dạng thừa. Bỏ phần định dạng đó trong `build_solutions.py` và tạo lại, bước này **vẫn xuất hiện**, vì **Excel tự áp định dạng kế toán cho ô công thức `=SUM(...)`** theo định dạng của ô nguồn. → Diff (T4.3) phải **bỏ qua thay đổi định dạng số mà Excel tự sinh khi nhập công thức** (ô mới có công thức, định dạng trùng định dạng ô nguồn). Đồng thời file đáp án vẫn phải sạch.
- **b09, điều kiện "đạt sẵn trên đề"**: căn phải với ô số luôn đạt (Excel tự căn phải số); định dạng cột F trong đề đã có sẵn dấu nghìn. Tự kiểm phát hiện đúng.

## Kết luận cho thiết kế (T3.2, T4.5, T5.5)

1. **Đưa diff vào prompt là đúng hướng**: độ phủ 100% ở cả hai bài; khác hẳn lần thử T0.4 (chỉ đọc đề, bỏ sót bước chép số liệu).
2. **Diff phải có ngữ cảnh "giữ nguyên"**: các ô trong vùng làm bài đã có công thức/dữ liệu ở file đề → đưa vào prompt dạng "đã có sẵn, KHÔNG được sửa", và sinh tự động điều kiện `data_unchanged` / `formula_matches_r1c1`.
3. **Không để AI viết giá trị cụ thể vào gợi ý.** Hai lớp chặn:
   - Prompt cấm số liệu cụ thể; gợi ý chỉ trỏ tới vùng nguồn.
   - **Kiểm tra sau sinh (tất định):** mọi số và mọi địa chỉ ô xuất hiện trong gợi ý phải có thật trong workbook và đúng vai trò (nguồn/đích). Sai thì gửi lại cho AI sửa, hoặc đánh dấu cho giảng viên.
4. **Điều kiện bắt buộc thêm theo luật, không trông vào AI:** vùng có công thức trong đáp án → luôn có `value_equals` + `formula_consistent` (AI b22 chỉ dùng `formula_uses_function`, không bắt được lỗi `$`).
5. **Tự kiểm (T4.5) loại được điều kiện vô nghĩa và điều kiện sai**: giữ lại làm bước bắt buộc trước khi giảng viên xem.
6. **Giảng viên duyệt vẫn cần thiết**: lỗi trong *chữ* của gợi ý (bảo gõ đè công thức) chỉ con người hoặc luật riêng mới bắt được.
7. Thời gian 3–13 s/bài, chấp nhận được cho thao tác "Sinh" trên Web quản trị (hiện trạng thái "đang sinh").
8. **Kết quả thay đổi giữa các lần chạy** với cùng đầu vào: b22 chạy 3 lần ra 4, 3, 4 bước; 1.000 – 7.900 token ra. Đánh giá chất lượng (T5.8) phải chạy **nhiều lần mỗi bài** và báo trung bình, không lấy một lần.
9. AI đặt nhầm tên cột ("cột Thành tiền" thay vì "Tổng tiền" ở b22). Prompt nên đưa **tiêu đề cột thật** cho từng vùng trong diff.
