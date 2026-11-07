# T5.8 — Đánh giá chất lượng sinh kịch bản bằng AI

**Task:** T5.8 · **Báo cáo:** mục 5.2 (đánh giá kỹ thuật) · **Ngày chạy:** 07/11/2026 · **Mô hình:** Inception `mercury-3`
**Code:** `apps/backend/src/tutor_backend/ai/evaluation.py` · **Chạy lại:** `.venv\Scripts\python -m tutor_backend evaluate --runs 3`

## 1. Cách đánh giá

- **Bài:** 4 bài do nhóm tự soạn, số liệu giả (`packages/excel_core/tests/fixtures/`). b09 và b22 có **cùng bố cục** với bài gốc của trung tâm, nên so được với 2 kịch bản viết tay (`schemas/tutor-script/v1/examples/`). b14 (tạo bảng: gộp ô, phông, nền, viền) và b16 (sắp xếp) chưa có kịch bản tay, chỉ đo độ hợp lệ.
- **Mỗi bài sinh 3 lần**: LLM cho kết quả khác nhau giữa các lần với cùng đầu vào (T2.6), nên báo trung bình.
- **Quy trình sinh** đúng như khi giảng viên bấm "Sinh" trên Web (T5.5): phân tích bài tất định → LLM chia bước và viết lời → dựng kịch bản v1 → kiểm 3 tầng → còn lỗi thì gửi lỗi cho LLM sửa, tối đa 3 lần. Lần chạy này không gắn giáo trình (RAG không tham gia).

| Chỉ số | Ý nghĩa |
|---|---|
| Hợp lệ | Kịch bản cuối qua cả 3 tầng: lược đồ, tham chiếu chéo, tự kiểm trên file đề/đáp án |
| Số lần gọi | Số lần gọi LLM (1 = đạt ngay; > 1 = có vòng tự sửa) |
| Độ phủ diff | Phần thay đổi đề → đáp án có điều kiện cùng loại kiểm tới |
| Lỗi chữ gợi ý | Địa chỉ ô hoặc số liệu không có thật trong chữ (lỗi chính của T2.6) |
| Bước đúng | Phần bước của kịch bản tay có một bước AI làm đúng việc đó (vùng mục tiêu trùng, Jaccard ≥ 0,5) |
| Điều kiện trùng | Phần điều kiện của kịch bản tay mà kịch bản AI cũng kiểm (cùng loại, phủ vùng) |

## 2. Kết quả

| Bài | Hợp lệ (3 tầng) | Số lần gọi | Thời gian AI (s) | Token vào / ra | Số bước AI (tay) | Độ phủ diff | Lỗi chữ gợi ý | Bước đúng | Điều kiện trùng |
|---|---|---|---|---|---|---|---|---|---|
| b09 định dạng dữ liệu số | 3/3 | 1,3 | 13,8 | 7.471 / 8.840 | 5,3 (6) | 100% | 0 | 100% | 87% |
| b22 hàm SUM | 3/3 | 1,0 | 7,3 | 4.321 / 4.312 | 2,0 (3) | 100% | 0 | 67% | 100% |
| b14 tạo bảng tính | 3/3 | 1,0 | 8,0 | 4.435 / 4.716 | 3,0 | 100% | 0 | — | — |
| b16 sắp xếp dữ liệu | 3/3 | 1,0 | 5,2 | 4.044 / 2.756 | 1,0 | 100% | 0 | — | — |
| **Chung (12 lần)** | **12/12** | **1,08** | **8,6** (tối đa 15,7) | 5.068 / 5.156 | | **100%** | **0** | | |

**So với lần thử đầu (T2.6, cùng mô hình, AI tự viết cả điều kiện):**

| | T2.6 | T5.5 |
|---|---|---|
| Điều kiện hợp lệ khi tự kiểm (b09) | 7/12 | 100% |
| Bịa số liệu, ghi địa chỉ ô trong gợi ý | Có (b09) | 0/12 lần |
| Bảo học viên gõ vào cột đã có công thức | Có (b09) | Không: cột được bảo vệ bằng điều kiện toàn bài |
| Vùng nguồn chép số liệu | Sai cột (D18:D22) | Đúng (F18:F22…): do code tìm, không do AI |

## 3. Nhận xét

1. **Tách việc "tất định" khỏi việc "viết lời" là thay đổi quyết định chất lượng.** AI không còn viết tham số điều kiện (số lẻ, vùng, hàm…) mà chỉ chia bước và viết lời; điều kiện suy ra từ chính file đáp án nên luôn đúng trên đáp án. Mã thay đổi, nút Ribbon, mã lỗi là danh sách đóng trong lược đồ structured output nên AI không bịa được.
2. **b22 "bước đúng" 67%** do khác cách chia bước, không phải sai: kịch bản tay tách "tính ô đầu tiên" và "sao chép xuống" thành 2 bước; AI gộp thành một bước "Tổng tiền cho từng ngày" (cùng điều kiện: có SUM, sao chép nhất quán, đúng giá trị). Điều kiện trùng vẫn 100%.
3. **b09 "điều kiện trùng" 87%**: 2/15 điều kiện của kịch bản tay không có trong bản AI, đều ở cột Thành tiền (công thức có sẵn trong đề): `formula_matches_r1c1` và `value_equals`. Bước phân tích bảo vệ cột này bằng điều kiện toàn bài `is_formula` (gõ đè thì phản hồi ngay), không coi là việc của một bước. Đây là chỗ giảng viên duyệt có thể thêm nếu muốn.
4. **Thời gian** 4–16 s mỗi bài, đạt NFR-03 (≤ 60 s). Một lần b09 cần vòng tự sửa (lần gọi thứ 2).
5. **Lỗi hiểu ngữ cảnh** gặp khi phát triển: AI gọi mỗi dòng của b22 là "món hàng" (thật ra là ngày). Đã sửa bằng cách đưa thêm cho AI cột nhận dạng dòng ("mỗi dòng ứng với một Ngày"); 3 lần chạy chính thức đều gọi đúng.

## 4. Giới hạn và việc tiếp theo

- **Bài tự soạn, không phải bài trung tâm.** Bố cục giống b09/b22 gốc nhưng số liệu và chữ là của nhóm. Chạy lại trên bài thật (máy có `samples/_local/`):
  `.venv\Scripts\python -m tutor_backend evaluate --runs 3 --samples-dir samples\_local --out ket-qua.md`
- **"Tỷ lệ bước phải sửa"** (so bản AI với bản giảng viên sửa, `origin = ai_edited`) cần dữ liệu thật từ giảng viên dùng Web (GĐ6, GĐ8). Hàm `edit_rate()` đã có; khi có dữ liệu thì lấy từ bảng `script_versions` (bản `ai` và bản con `ai_edited`).
- **Chất lượng lời gợi ý** (đúng sư phạm, dễ hiểu) chưa đo tự động: cần giảng viên chấm theo thang (gợi ý cho GVHD: 1–5 điểm cho từng cấp gợi ý của 10 bước ngẫu nhiên).
- **RAG** chưa tham gia lần đánh giá này (chưa có giáo trình công khai). Khi có giáo trình trung tâm: so có/không có đoạn giáo trình trong prompt.
