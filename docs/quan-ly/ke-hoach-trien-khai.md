# Kế hoạch triển khai dự án

**Đề tài:** Xây dựng gia sư AI hướng dẫn thực hành Excel dựa trên thao tác của người học
**Thời gian:** 06/11/2026 – 31/03/2027 · **Cập nhật lần cuối:** 07/11/2026 (GĐ2)
**Nhóm:** Nguyễn Tuấn Việt (trưởng nhóm), Diệp Đại Lê Hoài, Nguyễn Văn Linh, Nguyễn Ngọc Hòa · **GVHD:** ThS. Ngô Thị Ngọc Dịu

---

## 1. Cách dùng kế hoạch

- Mỗi task nhỏ, làm xong trong **1–3 ngày**. Task nào ước lượng lâu hơn thì tách tiếp.
- Mỗi task có **mã** (ví dụ `T2.4`) để đặt tên nhánh, issue và commit: `feature/T2.4-uia-ribbon`.
- Một task được tính là **xong** khi đạt cột "Hoàn thành khi" **và** đã merge vào nhánh `main` (code) hoặc đã nộp vào `docs/` (tài liệu).
- Cột **Cần trước** ghi các task phải xong trước. Task không có ràng buộc thì làm song song được.
- Trạng thái: ⬜ chưa làm · 🔄 đang làm · ✅ xong.

---

## 2. Tổng quan các giai đoạn

| GĐ | Tên giai đoạn | Thời gian | Phụ trách chính | Mốc bàn giao |
|---|---|---|---|---|
| 0 | Khởi động | 06/11 – 15/11 | Việt | Repo, môi trường chung, chọn LLM |
| 1 | Bộ bài tập mẫu & kịch bản viết tay | 09/11 – 22/11 | Hoài, Hòa | `samples/`, 2 kịch bản viết tay |
| 2 | Làm thử kỹ thuật (spike) | 09/11 – 22/11 | Việt, Linh | Báo cáo khả thi, bản thử bộ giám sát |
| 3 | Thiết kế hệ thống | 23/11 – 06/12 | Cả nhóm | Đặc tả, lược đồ JSON, ERD, đặc tả API |
| 4 | Lõi Excel dùng chung (`excel_core`) | 30/11 – 13/12 | Việt, Linh | Thư viện snapshot, diff, kiểm chứng |
| 5 | Backend & sinh kịch bản AI | 07/12 – 03/01 | Việt, Hoài | API, RAG, tác tử sinh kịch bản |
| 6 | Web quản trị (React) | 14/12 – 10/01 | Hoài | Web bản thử nghiệm |
| 7 | Desktop gia sư (PyQt6) | 14/12 – 24/01 | Linh, Hòa | Desktop bản thử nghiệm |
| 8 | Tích hợp, kiểm thử, thử nghiệm nhỏ | 18/01 – 31/01 | Cả nhóm | Hệ thống tích hợp, gói `.exe`, kết quả pilot |
| — | *Nghỉ Tết Đinh Mùi (mùng 1 = 06/02/2027)* | *~01/02 – 14/02* | — | *Dự phòng* |
| 9 | Thực nghiệm sư phạm | 15/02 – 28/02 | Cả nhóm | Dữ liệu thực nghiệm |
| 10 | Phân tích & nghiệm thu | 01/03 – 31/03 | Cả nhóm | Báo cáo tổng kết, mã nguồn, slide |

**Đường găng** (chậm ở đây là chậm cả dự án):
`T1.1 bài tập mẫu → T1.4/T1.5 kịch bản viết tay → T3.2 lược đồ JSON → T4.4/T4.5 kiểm chứng → T5.5 tác tử sinh kịch bản → T7.5 Teaching Agent → T8.1 tích hợp`

### Đối chiếu với tiến độ trong đề cương

| Đề cương | Kế hoạch này | Ghi chú |
|---|---|---|
| GĐ1 (T10/2026): tổng quan, khảo sát, bộ tiêu chí | T0.5 | Rà soát và bổ sung phần còn thiếu |
| GĐ2 (T11/2026): đặc tả, thiết kế, lược đồ JSON, API, bản thử bộ giám sát | GĐ1, GĐ2, GĐ3 | |
| GĐ3 (T12/2026): Backend, sinh kịch bản, Web | GĐ4, GĐ5, GĐ6 | |
| GĐ4 (T01/2027): Desktop | GĐ7 | Bắt đầu sớm từ 14/12 để bù thời gian nghỉ Tết |
| GĐ5 (T02/2027): tích hợp, đóng gói, thực nghiệm | GĐ8, GĐ9 | Thử nghiệm nhỏ đưa lên trước Tết |
| GĐ6 (T03/2027): phân tích, báo cáo, nghiệm thu | GĐ10 | |

---

## 3. Các quyết định kỹ thuật định hình kế hoạch

1. **AI không phải đoán từ đầu.** Backend tự so sánh *file đề* (dữ liệu thô) với *file kết quả mẫu* để ra danh sách thay đổi chính xác: ô nào có công thức mới, vùng nào đổi định dạng, có thêm biểu đồ không, trang in có đổi không… AI chỉ làm phần cần đến ngôn ngữ: gom thay đổi thành các bước, sắp thứ tự, tra giáo trình (RAG) và viết gợi ý 4 cấp. Cách này giảm khả năng AI bịa nội dung.
2. **Một bộ kiểm chứng dùng chung (`excel_core`).** Backend và Desktop dùng chung một mô hình "ảnh chụp workbook" (snapshot) và một bộ hàm kiểm tra điều kiện. Backend đọc file `.xlsx` bằng openpyxl, Desktop đọc Excel đang chạy bằng COM. Hai bên chỉ khác phần đọc dữ liệu.
3. **Kịch bản AI tự được kiểm tra trước khi đến tay giảng viên.** Mọi điều kiện kiểm chứng phải **đúng trên file mẫu** và **sai trên file đề**. Nếu không đạt, tác tử AI tự sửa lại.
4. **Lược đồ JSON là "hợp đồng" giữa 3 phần** (Web, Backend, Desktop). Lược đồ đặt ở `schemas/tutor-script/` và có đánh số phiên bản.
5. **Desktop nhận ra bài tập qua mã bài nhúng trong file đề** (Custom Document Property). Mã này được nhúng khi giảng viên phát hành kịch bản.

### Cấu trúc repo

Chi tiết và quy tắc phụ thuộc: [docs/quy-uoc/cau-truc-thu-muc.md](../quy-uoc/cau-truc-thu-muc.md).

```
Agent_Excel/
├─ apps/backend/            FastAPI: người dùng, học liệu, RAG, sinh kịch bản, tiến độ
├─ apps/web/                React (Vite + TypeScript): Web quản trị
├─ apps/desktop/            PyQt6: bộ giám sát, Teaching Agent, cửa sổ gia sư, overlay
├─ packages/excel_core/     Dùng chung: mô hình snapshot, so sánh file, kiểm tra điều kiện
├─ schemas/                 JSON Schema của kịch bản hướng dẫn
├─ samples/         Bộ bài tập mẫu (đề, file đề, file mẫu, giáo trình)
├─ spikes/          Script làm thử kỹ thuật (không dùng cho sản phẩm)
├─ scripts/         Công cụ quản lý repo (tạo issue từ kế hoạch…)
├─ docs/            Kế hoạch, đặc tả, thiết kế, tài liệu báo cáo
└─ nckh/            Đề cương
```

---

## 4. Chi tiết từng giai đoạn

### GĐ0 — Khởi động (06/11 – 15/11)

**Mục tiêu:** cả nhóm có chung repo, chung môi trường, chung cách làm việc.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T0.1 | Khởi tạo git, tạo cấu trúc thư mục như mục 3, viết README, `.gitignore` (bỏ `.env`, `venv/`, `node_modules/`, file tạm `~$*.xlsx`) | Repo đã lên GitHub, 4 thành viên có quyền ghi | — | Việt | 🔄 |
| T0.2 | Viết quy ước làm việc: đặt tên nhánh, commit, mở Pull Request và review chéo | Có bộ quy ước trong `docs/quy-uoc/` | T0.1 | Việt | ✅ |
| T0.3 | Chốt một phiên bản Python chung cho cả nhóm; tạo môi trường ảo và `requirements`; build thử một file `.exe` "hello" có PyQt6 + pywin32 bằng PyInstaller | Cả 4 máy build và chạy được file `.exe` thử | T0.1 | Việt | 🔄 |
| T0.4 | Chọn nhà cung cấp LLM và mô hình embedding: thử 2–3 lựa chọn với một đoạn giáo trình tiếng Việt; ước tính chi phí cả đề tài so với kinh phí 4.950.000đ | Có bảng so sánh và quyết định; API key để trong `.env`, không commit | — | Việt | 🔄 |
| T0.5 | Rà soát đầu ra GĐ1 của đề cương: báo cáo tổng quan, kết quả khảo sát, bộ tiêu chí kiểm tra và quy tắc phản hồi | Có danh sách "đã có / còn thiếu" và lịch bổ sung | — | Cả nhóm | 🔄 |
| T0.6 | Tạo bảng công việc (GitHub Projects); mỗi task trong file này thành một issue có người phụ trách | Mọi task GĐ0–GĐ3 đã có issue | T0.1 | Việt | 🔄 |

### GĐ1 — Bộ bài tập mẫu & kịch bản viết tay (09/11 – 22/11)

**Mục tiêu:** có dữ liệu thật làm nền cho thiết kế, cho thử AI và cho thực nghiệm.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T1.1 | Xin trung tâm tin học 4–6 bài thực hành, mỗi bài gồm: đề bài, file đề (dữ liệu thô), file kết quả mẫu, chương giáo trình tương ứng. **Hỏi luôn** phiên bản Office và ngôn ngữ giao diện (Việt/Anh) trên máy phòng thực hành | Đủ 4 thành phần cho mỗi bài; biết cấu hình máy ở trung tâm | — | Hoài, Hòa | 🔄 |
| T1.2 | Chuẩn hóa vào `samples/b<số>-<mô-tả>/` (`de.xlsx`, `dap-an.xlsx`, `de-bai.pdf`, `giao-trinh.pdf`, `thong-tin.md`); xóa dữ liệu cá nhân nếu có | Các bài cùng một cấu trúc thư mục | T1.1 | Hòa | ✅ |
| T1.3 | Lập ma trận "bài tập × nhóm kỹ năng" (nhập liệu, định dạng, trang in, 5 nhóm hàm, sắp xếp, lọc, biểu đồ) | Mỗi nhóm kỹ năng trong phạm vi có ít nhất 1 bài | T1.2 | Hoài | ✅ |
| T1.4 | Viết tay kịch bản cho bài 1 (dạng markdown): các bước, mỗi bước kiểm tra gì, tín hiệu nào kích hoạt, gợi ý 4 cấp, trích dẫn giáo trình | Có `docs/kich-ban-tay/b09-du-lieu-dang-so.md`, đã nhờ GVHD góp ý | T1.2 | Hoài | 🔄 |
| T1.5 | Viết tay kịch bản cho bài 2 (chọn bài khác nhóm kỹ năng với bài 1) | Có `docs/kich-ban-tay/b22-ham-tinh-tong.md` | T1.2 | Hòa | 🔄 |
| T1.6 | Tổng hợp danh mục **loại điều kiện kiểm chứng** và **loại tín hiệu** từ 2 kịch bản tay và bộ tiêu chí GĐ1 | Có `docs/thiet-ke/danh-muc-dieu-kien.md` | T1.4, T1.5, T0.5 | Hoài, Hòa | 🔄 |

### GĐ2 — Làm thử kỹ thuật (09/11 – 22/11)

**Mục tiêu:** biết chắc phần nào làm được trước khi thiết kế. Code để trong `spikes/`.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T2.1 | **COM – đọc dữ liệu:** kết nối vào Excel đang mở; đọc giá trị, công thức, định dạng (font, nền, viền, định dạng số, gộp ô) của một vùng; đo thời gian đọc 1.000 ô | Script chạy được, có số đo thời gian | T0.3 | Linh | ✅ |
| T2.2 | **COM – sự kiện và lúc Excel bận:** bắt `SheetChange`, `SelectionChange`, `WorkbookActivate`; thử khi học viên đang gõ trong ô hoặc đang mở hộp thoại; xử lý lỗi "Excel bận" bằng thử lại | Script chạy 10 phút thao tác tự do không bị crash | T2.1 | Linh | ✅ |
| T2.3 | **COM – đối tượng khó:** biểu đồ (loại, vùng dữ liệu, tiêu đề), thiết lập trang in (đo độ trễ), AutoFilter, trạng thái sắp xếp; đọc/ghi Custom Document Property (mã bài) | Có bảng "đọc được gì, mất bao lâu" | T2.1 | Việt | ✅ |
| T2.4 | **UIA/MSAA – Ribbon và hộp thoại:** biết tab Ribbon đang chọn; tìm nút theo AutomationId và lấy tọa độ; phát hiện hộp thoại đang mở (Format Cells, Sort, Insert Chart, Page Setup) và tab bên trong; thử với giao diện Office tiếng Việt và tiếng Anh | Có script và danh sách nút/hộp thoại nhận diện được (Office tiếng Việt: xác nhận ở T9.3) | T0.3 | Việt | ✅ |
| T2.5 | **Overlay PyQt6:** cửa sổ trong suốt, luôn nằm trên cùng, chuột bấm xuyên qua được; vẽ khung đúng quanh một ô và bám theo khi cuộn, zoom, di chuyển cửa sổ, ở mức DPI 100% / 125% / 150% | Có ảnh hoặc video minh họa (125%: mô phỏng; 100% và nhiều màn hình: chạy thật) | T2.1 | Linh | ✅ |
| T2.6 | **Thử AI bằng tay:** dùng openpyxl trích nội dung file đề và file mẫu, gửi kèm đề bài và đoạn giáo trình cho LLM để sinh các bước; so với kịch bản viết tay | Có ghi chép prompt và nhận xét chất lượng | T0.4, T1.4 | Việt | ✅ |
| T2.7 | **Báo cáo khả thi:** bảng "làm được / không làm được / cách thay thế"; điều chỉnh phạm vi nếu cần | Có `docs/task/t2-7-bao-cao-spike.md` (đây là "bản thử nghiệm bộ giám sát" trong đề cương) | T2.1 – T2.6 | Việt, Linh | ✅ |

### GĐ3 — Thiết kế hệ thống (23/11 – 06/12)

**Mục tiêu:** có bộ tài liệu đặc tả và thiết kế (Chương 3 báo cáo) đủ để bắt đầu code.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T3.1 | Yêu cầu chức năng và phi chức năng; tác nhân; ca sử dụng cho Web quản trị và Desktop | Có `docs/thiet-ke/dac-ta-yeu-cau.md` | T0.5 | Hoài, Hòa | ✅ |
| T3.2 | **Lược đồ kịch bản JSON v1** (JSON Schema): thông tin chung (mã bài, phiên bản), các bước, điều kiện kiểm chứng, vùng mục tiêu (ô/vùng trên trang tính và thành phần giao diện), tín hiệu kích hoạt, gợi ý 4 cấp, trích dẫn giáo trình | Có `schemas/tutor-script/v1/tutor-script.schema.json`; 2 kịch bản viết tay chuyển sang JSON và hợp lệ | T1.6, T2.7 | Việt | ✅ |
| T3.3 | Mô hình **snapshot workbook**: những thuộc tính nào được đọc và kiểu dữ liệu chung cho Backend và Desktop | Có `docs/thiet-ke/snapshot.md` | T2.7 | Linh | ✅ |
| T3.4 | **Luật điều tiết gợi ý:** khi nào tăng hoặc giảm cấp (số lần sai, thời gian dừng, xin trợ giúp, hoàn thành bước), theo mục 3.6 đề cương | Có `docs/thiet-ke/luat-goi-y.md` | T1.6 | Hòa | ✅ |
| T3.5 | Kiến trúc tổng thể: sơ đồ thành phần; sơ đồ tuần tự cho luồng "sinh – duyệt – phát hành" và luồng "học viên thực hành" | Có `docs/thiet-ke/kien-truc.md` | T3.2 | Việt | ✅ |
| T3.6 | Thiết kế CSDL (ERD): người dùng, giáo trình, bài tập, phiên bản kịch bản (nháp / chờ duyệt / đã duyệt / phát hành), phiên học, tiến độ, nhật ký | Có ERD và mô tả các bảng | T3.5 | Hoài | ✅ |
| T3.7 | Đặc tả REST API (OpenAPI) cho Web và Desktop | Có `docs/thiet-ke/openapi.yaml` | T3.6 | Việt | ✅ |
| T3.8 | Trình GVHD rà soát thiết kế, chốt bản v1 | Có biên bản góp ý; gắn tag `design-v1` trên git | T3.1 – T3.7 | Cả nhóm | 🔄 |

### GĐ4 — Lõi Excel dùng chung `excel_core` (30/11 – 13/12)

**Mục tiêu:** một thư viện Python dùng chung cho Backend (đọc file) và Desktop (đọc Excel đang chạy).

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T4.1 | Khung package `excel_core`: kiểu dữ liệu snapshot (theo T3.3), cài đặt pytest | Import được từ `apps/backend` và `apps/desktop` | T3.3 | Linh | ✅ |
| T4.2 | Bộ đọc bằng openpyxl: đọc file `.xlsx` thành snapshot (giá trị, công thức, định dạng, trang in, bộ lọc, biểu đồ) | Test đọc đúng trên mọi bài trong `samples/` | T4.1 | Linh | 🔄 |
| T4.3 | **Bộ so sánh (diff)** file đề với file mẫu, cho ra danh sách thay đổi có cấu trúc | Diff đúng trên mọi bài trong `samples/` | T4.2 | Việt | 🔄 |
| T4.4 | **Bộ kiểm tra điều kiện:** mỗi loại điều kiện (theo T1.6) là một hàm kiểm tra, kèm thông báo khi sai. Phân biệt "chỉ cần đúng giá trị" với "phải dùng đúng hàm" | Mỗi loại điều kiện có test riêng | T4.1, T3.2 | Linh | ✅ |
| T4.5 | **Trình kiểm tra kịch bản:** kịch bản hợp lệ theo lược đồ; mọi điều kiện đúng trên file mẫu và sai trên file đề | 2 kịch bản viết tay chạy qua được | T4.3, T4.4 | Việt | ✅ |

### GĐ5 — Backend & sinh kịch bản AI (07/12 – 03/01)

**Mục tiêu:** giảng viên tải bài lên thì nhận lại kịch bản hợp lệ, sẵn sàng để duyệt.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T5.1 | Khung FastAPI: cấu hình, kết nối CSDL, migration, xử lý lỗi chung | `/health` chạy; migration tạo đủ bảng theo ERD | T3.6 | Việt | ✅ |
| T5.2 | Xác thực và phân quyền (quản trị, giảng viên, học viên) | Đăng nhập trả về token; API chặn đúng khi sai quyền | T5.1 | Hoài | ✅ |
| T5.3 | API học liệu: tải lên giáo trình, đề bài, file đề, file mẫu; lưu trữ file | Tải lên và tải về được qua Swagger | T5.1 | Hoài | ✅ |
| T5.4 | **Lập chỉ mục giáo trình (RAG):** tách PDF/DOCX theo mục, tạo embedding, lưu vector; API tìm đoạn liên quan | Truy vấn "hàm VLOOKUP" trả về đúng mục trong giáo trình | T5.3, T0.4 | Việt | ⬜ |
| T5.5 | **Tác tử sinh kịch bản:** đầu vào là diff + đề bài + đoạn giáo trình, đầu ra là kịch bản JSON; chạy T4.5, nếu sai thì tự sửa (có giới hạn số lần) | Sinh được kịch bản hợp lệ cho ít nhất 4 bài mẫu | T4.5, T5.4 | Việt | ⬜ |
| T5.6 | Vòng đời kịch bản: nháp → chờ duyệt → đã duyệt → phát hành; lưu lịch sử phiên bản; khi phát hành thì nhúng mã bài và phiên bản vào file đề | API chuyển trạng thái chạy được; file đề tải về có mã bài | T5.5 | Việt | ⬜ |
| T5.7 | API cho Desktop: danh sách bài, tải kịch bản theo mã bài + phiên bản, tải file đề, nhận tiến độ và nhật ký | Kiểm tra được bằng một client giả | T5.6 | Hoài | ⬜ |
| T5.8 | **Đánh giá chất lượng sinh kịch bản:** so kịch bản AI với kịch bản viết tay (tỷ lệ bước đúng, tỷ lệ bước phải sửa) | Có bảng số liệu cho mục 5.2 của báo cáo | T5.5 | Việt | ⬜ |

### GĐ6 — Web quản trị React (14/12 – 10/01)

**Mục tiêu:** giảng viên làm được toàn bộ luồng sinh – sửa – duyệt – phát hành trên giao diện web.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T6.1 | Khung React (Vite + TypeScript): định tuyến trang, lớp gọi API, trang đăng nhập | Đăng nhập được bằng tài khoản từ backend | T5.2 | Hoài | ⬜ |
| T6.2 | Quản lý giáo trình và bài tập: tải lên, xem danh sách, xóa | Làm đủ các thao tác trên giao diện | T6.1, T5.3 | Hoài | ⬜ |
| T6.3 | Sinh kịch bản: nút "Sinh", hiển thị trạng thái đang chạy / lỗi / xong | Sinh được kịch bản từ giao diện | T6.2, T5.5 | Hoài | ⬜ |
| T6.4 | **Trình xem và sửa kịch bản:** danh sách bước, sửa nội dung gợi ý từng cấp, xem điều kiện kiểm chứng và vùng mục tiêu trên lưới mô phỏng trang tính | Sửa và lưu được; dữ liệu vẫn hợp lệ theo lược đồ | T6.3 | Hoài, Việt | ⬜ |
| T6.5 | Duyệt, phát hành, xem lịch sử phiên bản | Giảng viên phát hành được; học viên chỉ thấy bản đã phát hành | T6.4, T5.6 | Hoài | ⬜ |
| T6.6 | Theo dõi tiến độ: tiến độ từng học viên, bước hay sai, cấp gợi ý dùng nhiều *(làm khi đã có dữ liệu từ Desktop, trong GĐ8)* | Hiển thị đúng dữ liệu từ nhật ký | T5.7, T7.9 | Hoài | ⬜ |

### GĐ7 — Desktop gia sư PyQt6 (14/12 – 24/01)

**Mục tiêu:** học viên mở file đề, gia sư tự nhận bài, quan sát ngầm và hướng dẫn khi bắt được tín hiệu.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T7.1 | Khung PyQt6: cấu hình, đăng nhập, gọi API, lưu kịch bản trên máy để dùng khi mất mạng | Đăng nhập, tải và lưu được kịch bản (dùng API giả nếu backend chưa xong) | T3.7 | Hòa | ⬜ |
| T7.2 | Bộ đọc COM cho `excel_core`: tạo snapshot từ Excel đang chạy; tự kết nối lại khi Excel đóng hoặc mở lại | Cùng một file, kết quả giống bộ đọc openpyxl | T4.1, T2.2 | Linh | ⬜ |
| T7.3 | **Bộ giám sát:** gộp sự kiện COM, bộ đếm thời gian và UIA thành một luồng "sự kiện quan sát" chuẩn hóa | Log sự kiện ghi đúng khi thao tác | T7.2, T2.4 | Linh | ⬜ |
| T7.4 | Nhận diện bài tập: đọc mã bài trong file đang mở rồi chọn đúng kịch bản | Mở file đề là app tự nhận ra bài | T7.1, T7.2 | Hòa | ⬜ |
| T7.5 | **Teaching Agent:** quản lý bước hiện tại; kiểm chứng bằng `excel_core`; phát hiện tín hiệu; điều tiết cấp gợi ý theo T3.4; chuyển bước | Chạy hết bài 1 từ đầu đến cuối, log đúng | T7.3, T7.4, T3.4 | Linh | ⬜ |
| T7.6 | Cửa sổ gia sư: thẻ yêu cầu của bước hiện tại, khu vực gợi ý, nút xin trợ giúp, thanh tiến độ | Giao diện phản ánh đúng trạng thái của agent | T7.5 | Hòa | ⬜ |
| T7.7 | **Overlay hướng dẫn:** khung quanh vùng mục tiêu, chỉ tới nút Ribbon hoặc hộp thoại (dựa trên T2.5) | Hiện đúng vị trí khi gợi ý ở cấp "chỉ vị trí thao tác" | T7.5, T2.5 | Linh | ⬜ |
| T7.8 | Mascot: các trạng thái chờ, gợi ý, khen, nhắc nhở | Mascot đổi trạng thái theo sự kiện của agent | T7.6 | Hòa | ⬜ |
| T7.9 | Nhật ký và đồng bộ: ghi log thực hành, gửi tiến độ về backend, giữ hàng đợi khi mất mạng | Tắt mạng rồi bật lại không mất dữ liệu | T7.5, T5.7 | Hòa | ⬜ |
| T7.10 | Đóng gói `.exe` bằng PyInstaller, chạy thử trên máy chưa cài Python | Bộ cài chạy được trên ít nhất 2 máy khác máy phát triển | T7.1 – T7.9 | Linh | ⬜ |

### GĐ8 — Tích hợp, kiểm thử, thử nghiệm nhỏ (18/01 – 31/01)

**Mục tiêu:** hệ thống chạy trọn luồng và đã được học viên thật dùng thử **trước Tết**.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T8.1 | **Kiểm thử đầu – cuối:** giảng viên tải lên → sinh → duyệt → phát hành → học viên làm bài trên Desktop → tiến độ hiện trên Web | Chạy trọn luồng cho ít nhất 4 bài mẫu | GĐ5, GĐ6, GĐ7 | Cả nhóm | ⬜ |
| T8.2 | Triển khai Backend và Web lên máy chủ (Docker) để dùng khi thực nghiệm | Truy cập được qua mạng từ trung tâm | T8.1 | Việt | ⬜ |
| T8.3 | **Đánh giá kỹ thuật:** tỷ lệ nhận diện đúng trạng thái bước, tỷ lệ báo sai, độ trễ phản hồi, chạy liên tục ít nhất 1 giờ | Có bảng số liệu cho mục 5.2 của báo cáo | T8.1 | Linh | ⬜ |
| T8.4 | **Thử nghiệm nhỏ (pilot)** với 3–5 học viên; ghi lỗi và sửa (một vòng thiết kế – thử – chỉnh) | Có danh sách lỗi và đã sửa các lỗi nghiêm trọng | T8.1 | Cả nhóm | ⬜ |
| T8.5 | Tài liệu cài đặt Desktop; hướng dẫn sử dụng cho giảng viên và học viên | Có `docs/huong-dan/cai-dat.md`, `docs/huong-dan/su-dung.md` | T7.10 | Hòa | ⬜ |

### GĐ9 — Thực nghiệm sư phạm (chuẩn bị trong tháng 01, tiến hành 15/02 – 28/02)

**Mục tiêu:** có dữ liệu so sánh nhóm dùng gia sư với nhóm đối chứng.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T9.1 | Chuẩn bị bộ công cụ: bộ bài thực nghiệm, bài kiểm tra sau thực hành, phiếu tải nhận thức Paas 9 mức, thang SUS, phiếu hài lòng, phiếu đồng ý tham gia | GVHD đã duyệt bộ công cụ | T1.3 | Hoài, Hòa | ⬜ |
| T9.2 | Chia nhóm thực nghiệm và nhóm đối chứng có trình độ tương đương; chốt lịch với trung tâm | Có danh sách nhóm và lịch | T9.1 | Hòa | ⬜ |
| T9.3 | Cài đặt tại phòng máy trung tâm; kiểm tra phiên bản Excel và ngôn ngữ giao diện từng máy; chạy `spikes/t2-4-uia-ribbon/uia_ribbon.py` (xác nhận `idMso` trên Office tiếng Việt) và `spikes/t2-5-overlay/overlay.py` nếu máy đặt 125% | Mọi máy dùng cho thực nghiệm đều chạy được | T8.2, T7.10 | Linh | ⬜ |
| T9.4 | Tiến hành thực nghiệm; thu dữ liệu (kết quả, thời gian, số lỗi, các phiếu, nhật ký hệ thống) | Dữ liệu đầy đủ và đã sao lưu | T9.2, T9.3 | Cả nhóm | ⬜ |

### GĐ10 — Phân tích & nghiệm thu (01/03 – 31/03)

**Mục tiêu:** hoàn thành và bàn giao đủ các sản phẩm đã cam kết trong đề cương.

| ID | Việc cần làm | Hoàn thành khi | Cần trước | Phụ trách | TT |
|---|---|---|---|---|---|
| T10.1 | Xử lý số liệu: thống kê mô tả; t-test hoặc Mann–Whitney U; phân tích nhật ký (bước khó, cấp gợi ý hay dùng) | Có bảng và biểu đồ cho mục 5.3 của báo cáo | T9.4 | Việt, Hoài | ⬜ |
| T10.2 | Sửa và hoàn thiện hệ thống theo kết quả thực nghiệm | Phát hành bản v1.0 | T9.4 | Linh, Hòa | ⬜ |
| T10.3 | Viết báo cáo tổng kết 6 chương, dùng lại tài liệu của các giai đoạn trước | Bản thảo đã gửi GVHD | T10.1 | Cả nhóm | ⬜ |
| T10.4 | Bàn giao: mã nguồn, gói cài đặt Desktop, bộ triển khai Web và Backend, tài liệu | Gói bàn giao đủ theo mục "Sản phẩm" trong đề cương | T10.2 | Việt | ⬜ |
| T10.5 | Slide, kịch bản demo nghiệm thu, tập dượt | Demo chạy trơn tru trước hội đồng thử | T10.3 | Cả nhóm | ⬜ |

---

## 5. Rủi ro và cách giảm thiểu

| Rủi ro | Ảnh hưởng | Cách giảm thiểu |
|---|---|---|
| Tết Đinh Mùi (~01/02 – 14/02/2027) rơi vào tháng thực nghiệm | Trung tâm nghỉ, thiếu học viên | Pilot xong trước Tết (T8.4); chuẩn bị công cụ từ tháng 01 (T9.1); thực nghiệm chính thức 15/02 – 28/02 |
| Lịch thi học kỳ của nhóm | Chậm tiến độ | Xác định lịch thi sớm; xếp task nhẹ vào tuần thi |
| Thiếu bài tập mẫu thật | Không có dữ liệu để thiết kế và thực nghiệm | Làm T1.1 ngay tuần đầu |
| Máy ở trung tâm dùng Office tiếng Việt hoặc phiên bản khác | Overlay chỉ sai nút | Tìm nút theo AutomationId thay vì tên (T2.4); hỏi cấu hình máy sớm (T1.1) |
| Excel đang sửa ô hoặc mở hộp thoại làm lệnh COM bị từ chối | Bộ giám sát treo hoặc báo sai | Thử lại có giới hạn, ưu tiên dùng sự kiện (T2.2) |
| AI sinh sai bước hoặc sai điều kiện | Giảng viên mất công sửa | Có diff tất định, tự kiểm tra kịch bản (T4.5) và giảng viên duyệt |
| Chi phí API vượt kinh phí | Thiếu kinh phí | Ước tính ở T0.4; AI chỉ chạy khi sinh kịch bản, Desktop không gọi AI |

---

## 6. Bắt đầu ngay trong tuần này (06/11 – 15/11)

1. **T0.1** Khởi tạo repo · **T0.3** Chốt môi trường Python (Việt)
2. **T1.1** Liên hệ trung tâm xin bài tập mẫu (Hoài, Hòa)
3. **T2.1** Làm thử đọc dữ liệu qua Excel COM (Linh)
4. **T0.5** Họp nhóm rà soát đầu ra GĐ1 (cả nhóm)
