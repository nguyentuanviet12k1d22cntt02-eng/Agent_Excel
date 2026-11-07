# schemas — JSON Schema dùng chung

Lược đồ dữ liệu là "hợp đồng" giữa Web, Backend và Desktop.

```
schemas/
└─ tutor-script/              Lược đồ kịch bản hướng dẫn
   └─ v1/
      ├─ tutor-script.schema.json
      └─ examples/            Kịch bản mẫu hợp lệ (được test kiểm tra)
```

- Thay đổi làm hỏng kịch bản cũ thì **tạo phiên bản mới** (`v2/`), không sửa đè.
- Thay đổi lược đồ cần 1 người bên Backend **và** 1 người bên Desktop duyệt Pull Request.
- **Được xây dựng ở:** T3.2.
