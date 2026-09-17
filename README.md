# Caesar Cipher — Week 1 MVP

Ứng dụng web minh họa Caesar Cipher bằng **FastAPI**. Người dùng có thể mã hóa
hoặc giải mã văn bản nhập trực tiếp và file `.txt`, xem kết quả trên giao diện,
sao chép hoặc tải kết quả xuống.

README này ưu tiên giúp người đọc **hiểu thuật toán và luồng bài toán trước**, sau
đó mới hướng dẫn cài đặt và chạy dự án. Đây là ứng dụng học tập, không phải công
cụ bảo vệ dữ liệu nhạy cảm.

Đội Frontend xem [handoff tích hợp và hành vi](repo_docs/frontend-integration.md).

## 1. Hệ thống làm gì?

Mỗi yêu cầu có ba dữ liệu chính:

```text
văn bản + khóa số nguyên + thao tác encrypt/decrypt
                         │
                         ▼
                chuẩn hóa khóa modulo 26
                         │
                         ▼
          dịch các chữ cái ASCII A–Z và a–z
                         │
                         ▼
              giữ nguyên mọi ký tự còn lại
```

Hai nguồn đầu vào — văn bản và file — dùng chung một Caesar Core phía server.
Giao diện chỉ kiểm tra sơ bộ, gọi API và hiển thị phản hồi; kết quả chính thức
luôn do server tính.

Ứng dụng chạy stateless trong một tiến trình: cùng một FastAPI app phục vụ UI,
tài nguyên tĩnh, tài liệu API và các endpoint trên cùng origin. Không có database,
session hoặc lịch sử thao tác; phía server không lưu input, file hay kết quả sau request.

## 2. Thuật toán Caesar

Đánh số mỗi chữ cái trong một dải từ `0` đến `25`, ví dụ `A/a = 0`, `B/b = 1`,
..., `Z/z = 25`. Với khóa người dùng nhập là `k`, hệ thống chuẩn hóa khóa thành:

```text
k' = ((k mod 26) + 26) mod 26
```

Cách viết này luôn đưa `k'` về khoảng `0–25`, kể cả khi `k` âm.

Với chỉ số chữ cái là `x`:

```text
Mã hóa:  E(x) = (x + k') mod 26
Giải mã: D(x) = (x - k') mod 26
```

Giải mã bằng khóa `k` vì thế tương đương dịch theo `-k`. Khi vượt cuối hoặc đầu
bảng chữ cái, phép tính modulo làm ký tự quay vòng: `Z + 1 → A`, `A - 1 → Z`.

### Ký tự nào thay đổi?

| Nhóm ký tự | Hành vi |
|---|---|
| ASCII `A–Z` | Dịch vòng trong dải chữ hoa |
| ASCII `a–z` | Dịch vòng trong dải chữ thường |
| Số, dấu câu, khoảng trắng, tab, xuống dòng | Giữ nguyên |
| Tiếng Việt có dấu, emoji và Unicode ngoài ASCII | Giữ nguyên |

Chữ hoa sau khi dịch vẫn là chữ hoa, chữ thường vẫn là chữ thường. Vị trí và
thứ tự của mọi ký tự không phải chữ cái ASCII không thay đổi.

### Ví dụ chuẩn

```text
Input:   Hello World
Key:     3
Encrypt: Khoor Zruog
Decrypt: Hello World
```

### Ví dụ có chuẩn hóa khóa và Unicode

```text
Input:   Xin chào! Zz 123
Key:     29 → chuẩn hóa thành 3
Encrypt: Alq fkàr! Cc 123
```

Trong ví dụ này, các chữ ASCII trong `Xin`, `chào` và `Zz` được dịch. Ký tự `à`,
dấu câu, khoảng trắng và số được giữ nguyên. Giải mã kết quả với cùng khóa `29`
trả lại chính xác input ban đầu.

Một số khóa tương đương:

| Khóa nhập | Khóa chuẩn hóa |
|---:|---:|
| `29` | `3` |
| `-3` | `23` |
| `26` | `0` |
| `-29` | `23` |

## 3. Luồng xử lý văn bản

1. Người dùng chọn **Mã hóa** hoặc **Giải mã**, nhập văn bản và khóa.
2. UI chỉ bật nút hành động khi cả văn bản và khóa hợp lệ.
3. UI gửi JSON tới `POST /api/caesar/encrypt` hoặc
   `POST /api/caesar/decrypt`.
4. Server kiểm tra body, `text` và `key`, rồi gọi Caesar Core.
5. Server trả JSON thành công:

   ```json
   {"success": true, "result": "Khoor Zruog"}
   ```

6. UI hiển thị đúng chuỗi `result`, cho phép xem phân tích, sao chép hoặc tải kết
   quả thành file UTF-8.

Với JSON API, `key` phải thực sự là JSON integer. Các giá trị như `true`, `3.0`
hoặc chuỗi `"3"` bị từ chối; khóa âm, `0` và khóa lớn hơn `25` đều hợp lệ.

## 4. Luồng xử lý file

UI cho phép chọn hoặc kéo-thả file. Luồng hoàn chỉnh gồm hai chế độ phản hồi:

```text
Chọn file .txt
    │
    ├─ UI kiểm tra sơ bộ: đuôi, 0 byte, giới hạn 5 MiB
    │
    ▼
POST /api/caesar/file, response_mode=content
    │
    ├─ server kiểm tra metadata, kích thước và UTF-8
    ├─ bỏ BOM đầu file khỏi nội dung logic
    ├─ gọi Caesar Core
    ▼
JSON result để xem trước
    │
    └─ khi người dùng tải xuống:
       POST lại với response_mode=file
       → attachment UTF-8, đúng filename và trạng thái BOM
```

Server chỉ chấp nhận tên kết thúc bằng `.txt`, không phân biệt hoa thường. File
đúng `5 MiB = 5.242.880 byte` được chấp nhận; thêm một byte sẽ bị từ chối. File
phải là UTF-8 thường hoặc UTF-8 có BOM.

Khi trả JSON để xem trước, BOM không nằm trong `result` vì BOM là dấu hiệu
encoding, không phải nội dung. Khi tải file, server gắn lại BOM nếu và chỉ nếu file
gốc có BOM. Ký tự kết thúc dòng `LF` và `CRLF` cũng được bảo toàn nguyên trạng.

Tên file kết quả dùng dấu chấm:

```text
note.txt       → note.encrypted.txt
note.txt       → note.decrypted.txt
bao.cao.v2.txt → bao.cao.v2.encrypted.txt
BaoCao.TXT     → BaoCao.encrypted.txt
```

## 5. Validation và lỗi quan trọng

Mọi lỗi API dùng cùng một cấu trúc, không trả stack trace hay chi tiết kỹ thuật:

```json
{"success": false, "message": "<thông báo tiếng Việt>"}
```

| HTTP status | Nhóm lỗi | Ví dụ |
|---:|---|---|
| `413` | Request hoặc file vượt giới hạn | `File vượt quá dung lượng tối đa 5 MB.` |
| `415` | Sai đuôi file hoặc encoding | `Chỉ chấp nhận file .txt.` |
| `422` | Body/field thiếu, rỗng hoặc sai định dạng | `Khóa phải là số nguyên.` |
| `500` | Lỗi đọc file hoặc lỗi hệ thống | `Đã xảy ra lỗi hệ thống.` |

Các nguyên tắc cần nhớ:

- Chuỗi hoặc file chỉ chứa whitespace vẫn hợp lệ; chỉ chuỗi rỗng/null hoặc file
  đúng `0` byte bị coi là rỗng.
- `.TXT` được chấp nhận, nhưng `a.txt.exe` bị từ chối.
- `action` và `response_mode` là giá trị giao thức phân biệt hoa thường.
- Khi một request có nhiều lỗi, server trả đúng một lỗi theo thứ tự validation đã
  chốt; ma trận đầy đủ nằm trong OpenSpec.
- Giới hạn nghiệp vụ là **5 MiB**. Chuỗi lỗi vẫn cố ý ghi **“5 MB”** để giữ nguyên
  contract tiếng Việt đã được chấp nhận trong scope.
- Ngoài giới hạn file, ứng dụng có trần hạ tầng `64 MiB` theo `Content-Length` để
  từ chối payload rõ ràng quá lớn trước khi phân tích body.

## 6. Trạng thái UI và thẩm quyền của server

Giao diện mặc định ở chế độ **Mã hóa** với nguồn **Văn bản**. Nó quản lý mode,
nguồn input, file đang chọn, kết quả, tab xem và trạng thái loading.

- Nút hành động chỉ bật khi input và khóa cùng hợp lệ.
- Trong lúc chờ server, toàn bộ cụm điều khiển bị khóa để tránh request trùng hoặc
  trạng thái UI lệch với request đang chạy.
- Khi input, khóa, mode hoặc nguồn thay đổi, kết quả cũ được xóa để tránh hiển thị
  stale result.
- Request thất bại cũng xóa kết quả thành công cũ và hiển thị thông báo tiếng Việt.
- **Xóa** chỉ tác động lên panel tương ứng; **Làm mới** đưa toàn bộ trang về trạng
  thái ban đầu.
- Tab **Phân tích**, phần tô màu ký tự và bảng dịch chuyển chỉ giúp quan sát thuật
  toán. Chúng không thay thế kết quả server.

Trình duyệt chỉ giữ một hàm ánh xạ 26 chữ cái để vẽ bảng dịch chuyển. Mọi kết quả
mã hóa/giải mã được hiển thị, sao chép hoặc tải xuống đều bắt nguồn từ phản hồi API.

## 7. Kiến trúc và ranh giới runtime

```text
Browser UI
   │  JSON hoặc multipart, cùng origin
   ▼
FastAPI HTTP Adapter
   ├── Text validation
   ├── File validation / UTF-8 / BOM
   └── Error handlers
             │
             ▼
      Caesar Core dùng chung
             │
             ▼
       JSON hoặc attachment
```

Ứng dụng cung cấp:

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/` | Giao diện web |
| `GET` | `/docs` | Tài liệu API tương tác |
| `GET` | `/openapi.json` | OpenAPI schema |
| `POST` | `/api/caesar/encrypt` | Mã hóa text JSON |
| `POST` | `/api/caesar/decrypt` | Giải mã text JSON |
| `POST` | `/api/caesar/file` | Mã hóa/giải mã file multipart |

UI và API cùng scheme, host và cổng, nên UI dùng đường dẫn tương đối và Week 1
không cấu hình CORS. Local và container đều phục vụ trên cổng `8000`.

## 8. Cài đặt và chạy local

### Yêu cầu trước khi clone

| Thành phần | Phiên bản đã kiểm chứng | Ghi chú |
|---|---|---|
| Python | **3.12.x** (`3.12.3`) | `requires-python = ">=3.12,<3.13"` |
| uv | **0.12.15** | Cùng phiên bản pin trong `Dockerfile` |
| Docker | **29.x** hoặc mới hơn | Chỉ bắt buộc cho luồng container |

### Cài `uv` 0.12.15

```bash
curl -LsSf https://astral.sh/uv/0.12.15/install.sh | sh
uv --version   # uv 0.12.15
```

### Chuẩn bị môi trường

```bash
git clone <url-ssp-bai-tap> && cd caesar_cipher-be
uv sync --frozen        # tạo .venv + cài dependency đúng theo uv.lock, gồm dev deps
```

`uv sync` mặc định cài nhóm dev. Dùng `uv sync --frozen --no-dev` nếu chỉ cần
dependency để chạy ứng dụng.

### Chạy server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Sau khi server khởi động:

- Giao diện: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

Ví dụ gọi API:

```bash
curl -sS -X POST http://localhost:8000/api/caesar/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello World", "key": 3}'
# {"success":true,"result":"Khoor Zruog"}
```

## 9. Chạy test và lint

```bash
uv run pytest
uv run pytest --no-cov tests/integration/test_app_runtime.py
uv run ruff check .
uv run ruff format --check .
```

Coverage chỉ đo Python trong `app/`, không tính JS/CSS/HTML. Ngưỡng chặn trong
`pyproject.toml` là `--cov-fail-under=90`.

## 10. Chạy bằng Docker

Build image multi-stage bằng dependency trong `uv.lock`:

```bash
docker build -t caesar-cipher-be .
```

Chạy container và map cổng `8000`:

```bash
docker run --rm -p 8000:8000 caesar-cipher-be
```

Kiểm tra từ terminal khác:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/      # 200
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/docs  # 200
```

Container chạy bằng user không phải root (`appuser`, uid `10001`) và image runtime
không chứa `uv`:

```bash
docker run --rm caesar-cipher-be id -u
# 10001

docker run --rm caesar-cipher-be sh -c 'command -v uv || echo UV-ABSENT'
# UV-ABSENT
```

Hành vi quan sát được — kết quả, HTTP status, response envelope và thông báo lỗi —
giống nhau giữa local và container.

## 11. Phạm vi Week 1

Week 1 cố ý không gồm:

- database, persistence, session hoặc lịch sử thao tác;
- authentication và authorization;
- thuật toán cipher thứ hai hoặc abstract cipher hierarchy;
- React hay project frontend tách riêng;
- CORS cho frontend khác origin;
- CI/CD và triển khai cloud;
- xử lý streaming cho file lớn hơn giới hạn;
- rate limiting.

Ứng dụng không nên được phơi trực tiếp ra Internet. Nếu cần triển khai công khai,
hãy đặt reverse proxy phía trước để giới hạn request và bổ sung rate limit phù hợp.
Dừng container bằng `Ctrl+C`; với `--rm`, container tự xóa. Không có database hay
file trạng thái nào cần dọn sau đó.

## 12. Nguồn đặc tả và thứ tự áp dụng

Các nguồn dùng để hiểu và kiểm chứng hành vi:

1. [`BE Scope – Week 1 Caesar Cipher MVP.docx`](<BE Scope – Week 1 Caesar Cipher MVP.docx>)
   và [bản Markdown bảo tồn](docs/reference/be-scope-v1.0.md) mô tả phạm vi và
   contract nghiệp vụ đã thống nhất.
2. [OpenSpec change đã hoàn thành](openspec/changes/caesar-cipher-week1-mvp/)
   ghi lại hành vi quan sát được, quyết định đã chấp nhận và các bổ sung kỹ thuật.
3. `app/` là hiện thực của accepted Week 1 behavior tại HEAD hiện tại.
4. [`Caesar_Cipher_Tool_Demo.html`](Caesar_Cipher_Tool_Demo.html) là **UI reference
   cũ**, không phải runtime contract hiện hành.

Demo cũ vẫn chứa backend giả lập, giới hạn `1 MB`, host/cổng ghi cứng và một số
nhãn/hành vi đã được thay thế. Khi demo mâu thuẫn với scope, accepted OpenSpec hoặc
hành vi hiện tại, **accepted OpenSpec và current behavior chi phối cách hiểu Week 1**.
Ma trận validation đầy đủ, thứ tự mọi lỗi cạnh tranh, lịch sử quyết định, benchmark
và các phương án thiết kế đã loại được giữ trong OpenSpec thay vì sao chép vào README.
