# Biên bản nghiệm thu Week 1 MVP

Đối chiếu ngày 2026-09-16 với mục §7 của
`BE Scope – Week 1 Caesar Cipher MVP.docx` (nguồn sự thật).

- [x] **Mã hóa văn bản:** `Hello World`, khóa `3` trả `Khoor Zruog` qua
  `POST /api/caesar/encrypt`.
- [x] **Giải mã văn bản:** `Khoor Zruog`, khóa `3` trả `Hello World` qua
  `POST /api/caesar/decrypt`.
- [x] **Hai nguồn đầu vào:** UI và test tích hợp phủ văn bản, file, mã hóa, giải mã,
  preview JSON và attachment tải xuống.
- [x] **Ca đặc biệt:** test core/API phủ khóa âm, khóa lớn hơn 25, hoa/thường, số,
  Unicode, ký tự đặc biệt, LF và CRLF.
- [x] **Validation:** 13 thông báo canonical, HTTP status và khuôn JSON được kiểm bằng
  test contract; malformed JSON/multipart đều về canonical 422.
- [x] **Ranh giới dung lượng:** gọi endpoint file trong container với đúng `5242880`
  byte trả 200; `5242881` byte trả 413 và thông báo `File vượt quá dung lượng tối đa
  5 MB.`
- [x] **Chất lượng backend:** `uv run --frozen pytest -q` đạt 97.80% coverage;
  `uv run --frozen ruff check .` và `uv run --frozen ruff format --check .` sạch.
- [x] **Local và Docker:** ứng dụng local qua test/runtime contract; image
  `caesar-cipher-week1-mvp:validation` build thành công, chạy UID 10001, không chứa
  `uv`, và trả 200 cho `/`, `/docs`, `/static/app.js` trên cổng 8000.

## Bằng chứng Docker

```text
image: sha256:925b0f28cb266d75461a4758707105c27b6f2cda5a5845a7141b702b79f87716
docker run --rm <image> id -u: 10001
command -v uv: UV_ABSENT
GET /: 200
GET /docs: 200
GET /static/app.js: 200
file 5 MiB: 200
file 5 MiB + 1 byte: 413
```

Lần build đầu bị chậm tại tải wheel. Dockerfile dùng BuildKit cache mount cho cache
của `uv`; lần build hữu hạn kế tiếp hoàn tất và toàn bộ kiểm tra runtime ở trên đã
chạy trên chính image đó.
