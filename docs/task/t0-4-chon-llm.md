# T0.4 — Chọn nhà cung cấp LLM và mô hình embedding

**Trạng thái:** 🔄 **Đã chốt LLM: Inception Labs, mô hình `mercury-3`** (mục 6). Còn mở: giá, embedding cho RAG. Key đã chuyển vào `apps/backend/.env` (07/11/2026).

## 1. Hệ thống dùng LLM vào việc gì

| Việc | Ở đâu | Tần suất |
|---|---|---|
| Sinh kịch bản: đọc diff (file đề ↔ file mẫu) + đề bài + đoạn giáo trình → kịch bản JSON có gợi ý 4 cấp bằng tiếng Việt | Backend, khi giảng viên bấm "Sinh" (T5.5) | Vài lần cho mỗi bài |
| Embedding: lập chỉ mục giáo trình cho RAG | Backend, khi tải giáo trình lên (T5.4) | Một lần cho mỗi giáo trình |

**Desktop không gọi AI.** Vì vậy số lần gọi API rất ít (vài trăm lần cho cả đề tài). Nên ưu tiên **chất lượng** hơn là tiết kiệm từng token.

## 2. Tiêu chí so sánh

| Tiêu chí | Cách đo | Trọng số |
|---|---|---|
| Chất lượng các bước hướng dẫn | So với kịch bản viết tay (T1.4): bước đúng, đủ, đúng thứ tự | 35% |
| Tuân thủ định dạng JSON | Tỷ lệ kết quả hợp lệ theo lược đồ mà không cần sửa; có hỗ trợ structured output thì được cộng điểm | 20% |
| Tiếng Việt | Gợi ý tự nhiên, đúng thuật ngữ giáo trình (2 thành viên chấm độc lập) | 15% |
| Bám giáo trình | Không dùng hàm hoặc cách làm nằm ngoài giáo trình | 15% |
| Chi phí | Ước tính cho cả đề tài (mục 4) | 10% |
| Độ trễ, độ ổn định | Thời gian sinh một bài; tỷ lệ lỗi API | 5% |

## 3. Bài thử

- **Bài 09 — Dữ liệu dạng số** (`Cơ bản/`): có sẵn sheet đề `2. Bang_Ke_Ban_Hang` và sheet đáp án `3. Dap_An_Mau`, cùng sheet hướng dẫn `1. Thuc_Hanh_Tung_Buoc` của giảng viên. Đây là bản đối chiếu sẵn có.
- **Bài 1 trong kịch bản viết tay** (T1.4), khi đã có.
- Mỗi ứng viên chạy **3 lần** cùng một đầu vào để xem độ ổn định.
- Code thử đặt ở `spikes/t0-4-llm-eval/`, viết sau khi chốt danh sách ứng viên.

## 4. Ước tính chi phí

**Công thức:** chi phí = số lần sinh × (token vào × giá vào + token ra × giá ra)

**Giả định ban đầu** (thay bằng số đo thật sau khi chạy thử):

- Một lần sinh khoảng 20.000 token vào (diff, đề bài, đoạn giáo trình, lược đồ, hướng dẫn) và 8.000 token ra. Tính thêm vòng tự sửa ×2 thì thành **40.000 vào, 16.000 ra**.
- Cả đề tài: 30 bài × 5 lần sinh (thử nghiệm, sửa prompt, sinh lại) = **150 lần**, tức **6 triệu token vào, 2,4 triệu token ra**.

Ví dụ với bảng giá API Claude (lưu ngày 06/10/2026, **kiểm tra lại trên trang giá chính thức trước khi chốt**):

| Mô hình | Giá vào / ra (USD cho 1 triệu token) | Ước tính 150 lần sinh |
|---|---|---|
| Claude Opus 5.5 | 4 / 20 | 6 × 4 + 2,4 × 20 = **72 USD** |
| Claude Sonnet 5.5 | 2 / 10 | 6 × 2 + 2,4 × 10 = **36 USD** |
| Claude Haiku 5.5 | 0,10 / 0,50 | 6 × 0,1 + 2,4 × 0,5 = **1,8 USD** |
| *(ứng viên khác)* | *điền từ trang giá chính thức* | |

Với tỷ giá giả định khoảng 26.000 đ/USD, 72 USD tương đương khoảng 1,9 triệu đồng, tức gần 40% kinh phí 4.950.000 đ. Cách giảm chi phí mà không đổi mô hình:

- **Prompt caching:** phần hướng dẫn và lược đồ JSON giống nhau ở mọi lần sinh, nên cache được.
- **Batch API** (rẻ hơn 50%, trả kết quả không tức thì): dùng cho các lượt đánh giá hàng loạt ở T5.8, không dùng khi giảng viên đang chờ trên giao diện.

**Embedding:** Anthropic không cung cấp mô hình embedding. Có hai lựa chọn: dùng API embedding của nhà cung cấp khác, hoặc chạy mô hình embedding đa ngôn ngữ ngay trên máy chủ (ví dụ `bge-m3` qua Ollama, máy hiện đã cài Ollama). Tiêu chí chính là **tìm đúng đoạn giáo trình tiếng Việt**. Khối lượng giáo trình nhỏ nên chi phí embedding không đáng kể với cả hai cách.

## 5. Cần nhóm quyết định

1. ~~Danh sách ứng viên LLM~~ → trưởng nhóm chọn **Inception Labs** (key trong `key.txt`), ngày 07/11/2026.
2. **Hạn mức chi cho API** trong tổng kinh phí 4.950.000 đ. Cần tra **bảng giá Mercury** trên trang/dashboard của Inception Labs rồi điền vào mục 4.
3. **Embedding:** Inception Labs **không có** API embedding (gọi `/v1/embeddings` trả về 404). Chọn ở T5.4: API embedding nhà cung cấp khác, hoặc mô hình chạy trên máy chủ (ví dụ `bge-m3` qua Ollama).

## 6. Kết quả chạy thử (07/11/2026)

Script chạy lại được: [`spikes/t0-4-llm-eval/check_llm.py`](../../spikes/t0-4-llm-eval/check_llm.py) (không in key ra màn hình).

**Kết nối:** API tương thích OpenAI, `https://api.inceptionlabs.ai/v1`, xác thực bằng Bearer key. Key dùng được 4 mô hình:

| Mô hình | Ngữ cảnh (token) |
|---|---|
| `mercury-2` | 128.000 |
| `mercury-2.5` | 260.000 |
| `mercury-3` | 1.000.000 |
| `mercury-decide` | 65.536 |

**Bài thử:** sinh các bước + gợi ý 4 cấp cho đề b09 (định dạng số), chạy mỗi mô hình 1 lần, có và không có structured output.

| Mô hình | Độ trễ | Token vào / ra | JSON hợp lệ | Đủ bước | Chất lượng gợi ý | Nhận xét |
|---|---|---|---|---|---|---|
| `mercury-3` | 2,7 – 3,3 s | ~350 – 520 / ~1.050 – 1.400 | ✅ (cả khi không ép lược đồ) | ✅ 3/3 | **Tốt nhất**: biết Comma Style mặc định có 2 số lẻ nên phải bấm Decrease Decimal 2 lần, khớp với kịch bản viết tay | **Chọn làm mô hình chính** |
| `mercury-2` | 2,3 – 2,4 s | ~280 / ~960 | ✅ | ✅ 3/3 | Được, nhưng thứ tự cấp chưa hợp lý (cấp 3 mới bảo chọn vùng) | Dự phòng, nhanh và rẻ hơn (cần xác nhận giá) |
| `mercury-2.5` | 5,4 s | ~300 / ~1.930 | ✅ | ❌ chỉ 1/3 bước | Gợi ý tốt nhưng bỏ sót bước | Không chọn |

**Structured output** (`response_format: json_schema`, `strict: true`): `mercury-3` và `mercury-2` **tuân thủ đúng lược đồ**.

**Phát hiện cho thiết kế:**

1. Khi không ép lược đồ, cả 3 mô hình đều tự thêm `thousands_separator: false` cho cột Đơn giá, trong khi đề không yêu cầu, còn đáp án của giảng viên lại **có** dấu nghìn. Khi lược đồ cho phép `null` ("không ràng buộc"), lỗi này biến mất.
   - **Lược đồ kịch bản (T3.2) phải cho phép để trống những thuộc tính đề không nói tới.**
   - **Kịch bản AI sinh ra phải được tự kiểm trên file đáp án (T4.5)**: ràng buộc thừa sẽ làm điều kiện sai ngay trên đáp án.
2. Cả 3 mô hình đều **bỏ qua bước "chép số liệu thô lên bảng"** vì đề trong prompt thử chỉ nêu phần định dạng. Prompt thật phải đưa **diff file đề ↔ đáp án** (T4.3) để AI thấy cả thay đổi về giá trị, không chỉ đọc đề bài.
3. Tốc độ 2–3 giây cho một bài nhỏ đủ để giảng viên ngồi chờ trên giao diện Web, không cần chạy nền.

**Quyết định:** LLM = **Inception Labs `mercury-3`**, có structured output; `mercury-2` để dự phòng. Đánh giá chất lượng đầy đủ trên nhiều bài làm ở T2.6 và T5.8.

## 7. Lưu ý bảo mật

`key.txt` ở gốc repo đã được `.gitignore` chặn, nên sẽ không lên GitHub. Tuy vậy, nên chuyển key vào `apps/backend/.env` (theo mẫu `.env.example`) rồi xóa `key.txt`, để toàn nhóm dùng chung một cách quản lý key.

**Repo là public:** không dán key vào issue, Pull Request, nhóm chat công khai. Mỗi thành viên nên có key riêng (hoặc key con có hạn mức) để thu hồi được khi cần.
