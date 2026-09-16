# Caesar Cipher — Backend (Week 1 MVP)

Web app Caesar Cipher chạy bằng **FastAPI** — một tiến trình duy nhất phục vụ
toàn bộ giao diện, tài nguyên tĩnh, tài liệu API và các endpoint API trên cùng
một origin. Ứng dụng stateless: không database, không session, không lưu input,
file hay kết quả sau mỗi request.

## Yêu cầu trước khi clone (prerequisites)

| Thành phần | Phiên bản (đã kiểm chứng) | Ghi chú |
|---|---|---|
| Python | **3.12.x** (3.12.3) | `requires-python = ">=3.12,<3.13"`; `uv` sẽ dùng Python này |
| uv | **0.12.15** | Gom đúng phiên bản đã pin trong `Dockerfile` (`ghcr.io/astral-sh/uv:0.12.15`) |
| Docker | 29.x (hoặc mới hơn) | Chỉ bắt buộc cho luồng chạy container |

### Cài `uv` 0.12.15 (chưa có `uv` trên máy)

```bash
curl -LsSf https://astral.sh/uv/0.12.15/install.sh | sh
```

Kiểm tra:

```bash
uv --version   # uv 0.12.15
```

## Chuẩn bị môi trường local

```bash
git clone <url-ssp-bai-tap> && cd caesar_cipher-be
uv sync --frozen        # tạo .venv + cài dependency đúng theo uv.lock (gồm dev deps)
```

> `uv sync` mặc định cài luôn nhóm dev (pytest, ruff, …). Dùng `uv sync --frozen --no-dev`
> nếu bạn chỉ muốn dependency chạy app mà không có dev tooling.

## Chạy local (cổng 8000)

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Sau khi server lên:

- Giao diện web: http://localhost:8000/
- Tài liệu API tương tác (Swagger): http://localhost:8000/docs
- OpenAPI schema JSON: http://localhost:8000/openapi.json

Mọi endpoint API đều nằm dưới `http://localhost:8000/api/caesar/…`:
`POST /api/caesar/encrypt`, `POST /api/caesar/decrypt`, `POST /api/caesar/file`.

## Chạy test và lint

```bash
uv run pytest                 # toàn bộ tính năng + deadline: coverage backend ≥ 90%
uv run pytest --no-cov tests/integration/test_app_runtime.py   # runtime (không cần Docker)
uv run ruff check .           # lint
uv run ruff format --check .  # định dạng
```

Coverage chỉ đo mã Python trong `app/` (không tính JS/CSS/HTML); ngưỡng chặn là
`--cov-fail-under=90`.

## Chạy bằng Docker

Build image từ `Dockerfile` multi-stage (uv 0.12.15, `uv sync --frozen --no-dev`):

```bash
docker build -t caesar-cipher-be .
```

Chạy container, map cổng 8000:

```bash
docker run --rm -p 8000:8000 caesar-cipher-be
```

Kiểm tra (mở terminal khác):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/      # 200
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/docs  # 200
```

Container chạy với user không phải root (`appuser`, uid **10001**), image cuối
**không** chứa `uv`:

```bash
docker run --rm caesar-cipher-be id -u            # 10001
docker run --rm caesar-cipher-be sh -c 'command -v uv || echo UV-ABSENT'   # UV-ABSENT
```

Ví dụ gọi API trên container:

```bash
curl -sS -X POST http://localhost:8000/api/caesar/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello World", "key": 3}'
# {"success":true,"result":"Khoor Zruog"}
```

Kết quả quan sát được (HTTP status, cấu trúc response, thông báo lỗi) giống hệt
chạy local với cùng đầu vào.

## Giới hạn triển khai

Ứng dụng Tuần 1 **không có rate limit** và được thiết kế cho mục đích học tập,
không nên phơi trực tiếp ra Internet. Nếu triển khai công khai, đặt reverse proxy
phía trước để giới hạn kích thước request và bổ sung rate limit phù hợp.

## Dọn dữ liệu thử nghiệm

Dừng container: nhấn `Ctrl+C`; với `--rm` container tự xóa. Không có database
hay file trạng thái nào để dọn — một request kết thúc là xong.
