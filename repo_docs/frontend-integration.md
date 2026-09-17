# Handoff tích hợp Frontend — Caesar Cipher Week 1

Tài liệu này là hướng dẫn cho đội Frontend tích hợp với backend Caesar Cipher
Week 1 theo cách độc lập framework. Nó mô tả contract đã được chấp nhận và hành vi
người dùng bắt buộc, không quy định React/Vue/Svelte, cấu trúc component, CSS hay
layout cụ thể.

Contract trong tài liệu được pin theo accepted Week 1 backend tại commit
`fa009eb92b953000afd1a8c31273ae73d901a84a`. Commit tài liệu sau đó không thay đổi
product behavior. [OpenSpec change đã hoàn thành](../openspec/changes/caesar-cipher-week1-mvp/)
là nguồn có thẩm quyền; nếu hướng dẫn này lệch OpenSpec, đó là lỗi tài liệu cần sửa,
không phải lý do để FE tự đổi contract.

## 1. Contract bắt buộc và phần FE được tự do

FE phải giữ nguyên:

- thuật toán Caesar và cách chuẩn hóa khóa;
- request/response, endpoint, content type và HTTP status;
- text/file flow, download flow và xử lý lỗi;
- quy tắc xóa kết quả cũ, loading và khả năng truy cập;
- same-origin contract và server-authoritative result;
- giới hạn file, UTF-8, BOM, newline và filename.

FE được tự do thay đổi:

- framework, cách chia component và state store;
- màu sắc, typography, icon, spacing và responsive layout;
- cách tổ chức code gọi API, miễn hành vi quan sát được không đổi.

## 2. Mô hình hệ thống và runtime boundary

```text
Trình duyệt
   │
   │  đường dẫn tương đối /api/caesar/*
   ▼
FastAPI — cùng origin, cùng cổng 8000
   ├── HTTP adapter và validation
   ├── file processing: bytes / UTF-8 / BOM
   ├── error handlers
   └── Caesar Core dùng chung cho text và file
            │
            ▼
      JSON hoặc file attachment
```

Backend phục vụ:

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/` | UI được backend phục vụ |
| `GET` | `/docs` | Swagger UI tương tác |
| `GET` | `/openapi.json` | OpenAPI schema |
| `POST` | `/api/caesar/encrypt` | Mã hóa text JSON |
| `POST` | `/api/caesar/decrypt` | Giải mã text JSON |
| `POST` | `/api/caesar/file` | Mã hóa/giải mã file multipart |

Khi chạy full app, UI và API cùng scheme, host và port. FE phải dùng URL tương đối,
ví dụ `/api/caesar/encrypt`, không ghi cứng `localhost` hoặc một cổng backend.

Nếu FE dùng dev server riêng, cấu hình dev server **proxy `/api` sang backend**.
Không yêu cầu backend bật CORS chỉ để phục vụ workflow phát triển. Swagger/OpenAPI
khi chạy local có tại <http://localhost:8000/docs> và
<http://localhost:8000/openapi.json>.

Ứng dụng stateless: backend không lưu input, file, result, session hoặc lịch sử sau
request. Local và Docker có cùng contract quan sát được trên cổng `8000`.

## 3. Thuật toán Caesar FE cần hiểu

Với khóa người dùng nhập là `k`, khóa dùng cho hiển thị được chuẩn hóa về `0–25`:

```text
k' = ((k mod 26) + 26) mod 26
```

Đánh số chữ cái trong từng dải từ `0` đến `25`:

```text
Mã hóa:  E(x) = (x + k') mod 26
Giải mã: D(x) = (x - k') mod 26
```

| Nhóm ký tự | Hành vi bắt buộc |
|---|---|
| ASCII `A–Z` | Dịch vòng trong dải chữ hoa |
| ASCII `a–z` | Dịch vòng trong dải chữ thường |
| Số, dấu câu, whitespace, LF, CRLF | Giữ nguyên |
| Tiếng Việt có dấu, emoji, Unicode ngoài ASCII | Giữ nguyên |

Ví dụ:

```text
Input:   Xin chào! Zz 123
Key:     29 → chuẩn hóa thành 3
Encrypt: Alq fkàr! Cc 123
```

Chữ ASCII trong `Xin`, `chào` và `Zz` được dịch; `à`, dấu câu, khoảng trắng và số
được giữ nguyên. Giải mã kết quả với cùng khóa `29` trả lại chính xác input.

FE có thể tính bảng dịch chuyển 26 chữ cái để **minh họa** và hiển thị khóa chuẩn
hóa. FE không được dùng phép tính client-side làm result chính thức. Result hiển thị,
sao chép và tải xuống phải bắt nguồn từ phản hồi server.

## 4. Quy ước API chung

### Success JSON

Các response JSON thành công có đúng hai trường:

```json
{
  "success": true,
  "result": "Khoor Zruog"
}
```

### Error JSON

Mọi lỗi API, kể cả lỗi của `response_mode=file`, trả JSON:

```json
{
  "success": false,
  "message": "Khóa phải là số nguyên."
}
```

FE phải kiểm tra cả HTTP status và body. Luôn hiển thị `message` hợp lệ do backend
trả về; không hiển thị raw body, stack trace hoặc thông báo framework. Nếu body lỗi
không đọc được, dùng thông báo chung bằng tiếng Việt.

| Status | Ý nghĩa quan trọng với FE |
|---:|---|
| `200` | Thành công; JSON result hoặc attachment tùy flow |
| `413` | File/request vượt giới hạn |
| `415` | Đuôi file hoặc encoding không được hỗ trợ |
| `422` | Body/field thiếu, rỗng hoặc sai định dạng |
| `500` | Lỗi đọc file hoặc lỗi hệ thống |

Ma trận lỗi và thứ tự mọi lỗi cạnh tranh nằm trong
[error-handling spec](../openspec/changes/caesar-cipher-week1-mvp/specs/error-handling/spec.md),
không lặp lại toàn bộ ở đây.

Một helper vanilla JS dùng chung cho JSON response:

```js
async function readJsonEnvelope(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const error = new Error("Đã xảy ra lỗi hệ thống.");
    error.status = response.status;
    throw error;
  }

  let body;
  try {
    body = await response.json();
  } catch {
    const error = new Error("Đã xảy ra lỗi hệ thống.");
    error.status = response.status;
    throw error;
  }

  if (!response.ok || body.success !== true) {
    const message = typeof body.message === "string"
      ? body.message
      : "Đã xảy ra lỗi hệ thống.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return body;
}
```

## 5. Text flow

### Endpoint contract

| Operation | Method và path |
|---|---|
| Encrypt | `POST /api/caesar/encrypt` |
| Decrypt | `POST /api/caesar/decrypt` |

- Request `Content-Type`: `application/json`.
- `text`: bắt buộc là chuỗi khác rỗng. Whitespace-only vẫn hợp lệ.
- `key`: bắt buộc là JSON integer thật sự.
- Backend từ chối boolean, float, numeric string, array và object làm `key`.
- Khóa âm, `0` và khóa lớn hơn `25` đều hợp lệ.

Request:

```json
{
  "text": "Hello World",
  "key": 3
}
```

Happy path:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "success": true,
  "result": "Khoor Zruog"
}
```

Representative error — gửi numeric string thay vì JSON integer:

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```json
{
  "success": false,
  "message": "Khóa phải là số nguyên."
}
```

### curl

```bash
curl -sS -X POST http://localhost:8000/api/caesar/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello World","key":3}'
# {"success":true,"result":"Khoor Zruog"}
```

Representative error:

```bash
curl -sS -i -X POST http://localhost:8000/api/caesar/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello World","key":"3"}'
# HTTP 422; {"success":false,"message":"Khóa phải là số nguyên."}
```

### Vanilla JS fetch

Không dùng `Number(rawKey)` vì có thể làm mất chính xác với integer dài. Chuyển
input qua `BigInt`, rồi tạo JSON integer token thay vì numeric string:

```js
function jsonIntegerToken(rawKey) {
  const value = rawKey.trim();
  if (!/^[+-]?[0-9]+$/.test(value)) {
    throw new Error(value === "" ? "Thiếu khóa." : "Khóa phải là số nguyên.");
  }
  return BigInt(value).toString();
}

async function transformText(operation, text, rawKey) {
  const keyToken = jsonIntegerToken(rawKey);
  const body = `{"text":${JSON.stringify(text)},"key":${keyToken}}`;
  const response = await fetch(`/api/caesar/${operation}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return readJsonEnvelope(response);
}
```

Trước khi gọi, FE phải xóa result/analysis cũ và bật loading. Khi lỗi, tiếp tục giữ
result rỗng, hiển thị `error.message`, rồi mở khóa control trong `finally`.

Với nguồn text, FE có thể tạo file UTF-8 từ `result` đã nhận bằng `Blob`. Tên mặc
định là `ket-qua.encrypted.txt` hoặc `ket-qua.decrypted.txt`.

## 6. File flow

### Endpoint contract

```text
POST /api/caesar/file
Content-Type: multipart/form-data
```

Không tự đặt header `Content-Type` khi gửi `FormData`; trình duyệt phải thêm
multipart boundary.

| Field | Bắt buộc | Giá trị |
|---|---|---|
| `file` | Có | File có tên kết thúc bằng `.txt` |
| `key` | Có | Chuỗi số nguyên có dấu |
| `action` | Có | Chính xác `encrypt` hoặc `decrypt` |
| `response_mode` | Không | `content` hoặc `file`; mặc định `content` |

Multipart `key` có thể có dấu `+`/`-`, khoảng trắng hai đầu và số `0` đứng đầu;
giá trị sau trim phải khớp `[+-]?[0-9]+` và dài không quá 32 ký tự. `action` và
`response_mode` phân biệt hoa thường.

### Hai request có chủ ý

1. **Preview:** gửi `response_mode=content`; backend trả JSON result.
2. **Download:** khi người dùng bấm tải, gửi lại file gốc bằng request thứ hai với
   `response_mode=file`; backend trả attachment.

Không download file nguồn bằng cách chỉ đóng `result` preview vào Blob: preview
không mang trạng thái BOM và không phải nguồn có thẩm quyền cho filename file gốc.

### Quy tắc file

- Đuôi `.txt` không phân biệt hoa thường: `.txt`, `.TXT`, `.Txt` đều hợp lệ.
- `a.txt.exe` và file không có đuôi bị từ chối.
- Giới hạn chính xác là `5 MiB = 5.242.880 byte`.
- Đúng `5.242.880` byte được chấp nhận; `5.242.881` byte bị từ chối.
- Thông báo lỗi cố ý giữ nguyên câu `File vượt quá dung lượng tối đa 5 MB.` dù
  giới hạn thực thi là 5 MiB.
- Chỉ UTF-8 thường và UTF-8 có BOM được chấp nhận.
- `response_mode=content` loại BOM đầu file khỏi JSON `result`.
- `response_mode=file` giữ BOM nếu file đầu vào có BOM và không tự thêm nếu không có.
- LF/CRLF, Unicode, số, dấu câu và whitespace giữ nguyên.
- File `0` byte bị từ chối; file chỉ chứa whitespace vẫn hợp lệ.

Filename attachment:

```text
note.txt       → note.encrypted.txt
note.txt       → note.decrypted.txt
bao.cao.v2.txt → bao.cao.v2.encrypted.txt
BaoCao.TXT     → BaoCao.encrypted.txt
```

### Happy path và representative error

Preview thành công:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "success": true,
  "result": "Khoor Zruog"
}
```

Download thành công:

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="note.encrypted.txt"
```

Representative error — file sai đuôi, kể cả khi yêu cầu mode `file`:

```http
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json
```

```json
{
  "success": false,
  "message": "Chỉ chấp nhận file .txt."
}
```

### curl

Preview nội dung:

```bash
curl -sS -X POST http://localhost:8000/api/caesar/file \
  -F 'file=@note.txt;type=text/plain' \
  -F 'key=3' \
  -F 'action=encrypt' \
  -F 'response_mode=content'
# {"success":true,"result":"Khoor Zruog"}
```

Tải attachment:

```bash
curl -sS -OJ -X POST http://localhost:8000/api/caesar/file \
  -F 'file=@note.txt;type=text/plain' \
  -F 'key=3' \
  -F 'action=encrypt' \
  -F 'response_mode=file'
```

Representative error:

```bash
curl -sS -i -X POST http://localhost:8000/api/caesar/file \
  -F 'file=@note.md;type=text/plain' \
  -F 'key=3' \
  -F 'action=encrypt' \
  -F 'response_mode=content'
# HTTP 415; {"success":false,"message":"Chỉ chấp nhận file .txt."}
```

### Vanilla JS fetch

```js
function createFileForm(file, rawKey, action, responseMode) {
  const data = new FormData();
  data.append("file", file);
  data.append("key", rawKey.trim());
  data.append("action", action);
  data.append("response_mode", responseMode);
  return data;
}

async function previewFile(file, rawKey, action) {
  const response = await fetch("/api/caesar/file", {
    method: "POST",
    body: createFileForm(file, rawKey, action, "content"),
  });
  return readJsonEnvelope(response);
}
```

Download phải tạo request thứ hai và xử lý error JSON trước khi đọc Blob:

```js
function attachmentFilename(disposition) {
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8) return decodeURIComponent(utf8[1]);

  const quoted = disposition.match(/filename="((?:\\.|[^"])*)"/i);
  return quoted ? quoted[1].replace(/\\([\\"])/g, "$1") : null;
}

async function downloadFile(file, rawKey, action) {
  const response = await fetch("/api/caesar/file", {
    method: "POST",
    body: createFileForm(file, rawKey, action, "file"),
  });
  const contentType = response.headers.get("content-type") || "";

  if (!response.ok || contentType.toLowerCase().includes("application/json")) {
    let body = null;
    try {
      body = await response.json();
    } catch {
      // Dùng fallback tiếng Việt bên dưới.
    }
    throw new Error(
      typeof body?.message === "string"
        ? body.message
        : "Không thể tải kết quả. Vui lòng thử lại.",
    );
  }

  if (!contentType.toLowerCase().startsWith("text/plain")) {
    throw new Error("Đã xảy ra lỗi hệ thống.");
  }

  const filename = attachmentFilename(
    response.headers.get("content-disposition") || "",
  );
  if (!filename) throw new Error("Đã xảy ra lỗi hệ thống.");

  return { blob: await response.blob(), filename };
}
```

FE tự tạo object URL, kích hoạt download và `URL.revokeObjectURL()` sau khi dùng.
Nếu download thất bại, phải xóa result/analysis cũ thay vì tiếp tục hiển thị trạng
thái thành công trước đó.

## 7. FE validation và BE authority

Validation phía FE chỉ nhằm phản hồi nhanh và vô hiệu nút khi dữ liệu rõ ràng sai.
Backend luôn là nguồn quyết định cuối cùng.

| FE chịu trách nhiệm | Backend chịu trách nhiệm |
|---|---|
| Kiểm tra text có ký tự nào hay chưa | Kiểm tra body JSON và kiểu field thực tế |
| Kiểm tra cú pháp khóa để bật/tắt nút | Quyết định key hợp lệ và chuẩn hóa cho transform |
| Kiểm tra sơ bộ tên file, `File.size`, 0 byte | Đếm bytes thật, giới hạn 5 MiB, UTF-8 và BOM |
| Hiển thị loading, status và `message` | Trả HTTP status và error envelope canonical |
| Vẽ shift-map minh họa | Tính result chính thức bằng Caesar Core |
| Tải Blob/attachment theo response | Quyết định nội dung, BOM và filename file nguồn |

FE không được dùng `trim()` để kết luận text whitespace-only là rỗng. FE cũng không
thể dùng preview client-side thay cho validation UTF-8 của backend.

## 8. UI state và transition bắt buộc

State có thể được tổ chức tùy framework, nhưng tối thiểu cần biểu diễn:

```text
mode        = encrypt | decrypt
inputSource = text | file
text/file   = input hiện tại
key         = giá trị người dùng nhập
result      = null | chuỗi server trả về
view        = result | analysis
loading     = true | false
```

| Event | State/result bắt buộc | UI mong đợi |
|---|---|---|
| Mở trang | `encrypt`, `text`, `result=null`, `loading=false` | Nút action bị vô hiệu |
| Đổi mode | Giữ input và key; xóa result/analysis, ẩn notice cũ | Đổi nhãn Bản rõ/Bản mã và action |
| Đổi nguồn text/file | Giữ dữ liệu riêng của từng nguồn; xóa result, ẩn notice cũ | Hiện panel tương ứng |
| Sửa text/file | Xóa result/analysis và notice cũ | Validate lại ngay |
| Sửa key | Xóa result/analysis và notice cũ | Hiện key chuẩn hóa nếu cần |
| Submit | Xóa result cũ; `loading=true` | Khóa toàn bộ control, báo đang xử lý |
| Success | Lưu đúng `result` từ server; `loading=false` | Bật copy/clear/download |
| API/network failure | `result=null`; xóa analysis; `loading=false` | Hiện lỗi tiếng Việt, cho phép thử lại |
| Download failure | Xóa result/analysis thành công cũ | Status và notice chuyển sang lỗi |
| Xóa input | Chỉ xóa input đang chọn và result liên quan | Key có thể giữ nguyên |
| Xóa key | Chỉ xóa key và result liên quan | Đưa focus về ô key |
| Xóa output | Chỉ xóa result/analysis | Giữ input và key |
| Làm mới | Reset toàn bộ về trạng thái mở trang | Ẩn notice, reset ba status bar |

Nút action chỉ bật khi input và key cùng hợp lệ. Trong loading, phải chặn mọi cách
thay đổi state hoặc gửi lặp: click, keyboard shortcut, Enter/Space trên drop zone và
file drop thực tế.

Các hành vi component khác cũng là contract:

- Có ba status độc lập cho input, key và output; mỗi status có mức neutral, valid
  hoặc error thể hiện bằng cả text và dấu hiệu trực quan.
- Nút **Tạo ví dụ** chuyển sang nguồn text, điền `Hello World` và key `3`, rồi cập
  nhật validation để action sẵn sàng.
- Output là read-only và có hai view **Văn bản**/**Phân tích**. Analysis hiển thị
  mode, nguồn, key nhập/key chuẩn hóa, tổng ký tự, số chữ hoa ASCII, chữ thường
  ASCII và ký tự giữ nguyên.
- Copy/Clear output bị vô hiệu khi chưa có result. Download có mặt cho cả nguồn
  text và file, cũng bị vô hiệu khi chưa có result.
- Clear output đưa view về Văn bản, xóa analysis và reset output status nhưng giữ
  input/key.
- Shift-map gồm hai hàng 26 chữ cái, cập nhật theo mode và key chuẩn hóa; key không
  hợp lệ dùng mapping `0`. Các chữ ASCII xuất hiện trong input được highlight không
  phân biệt hoa thường.
- File panel hỗ trợ picker và drag/drop, hiển thị tên, kích thước nhị phân
  byte/KiB/MiB, preview, **Đổi file** và **Gỡ file**.

## 9. Accessibility và loading

- Toàn bộ chức năng phải dùng được bằng bàn phím, có thứ tự focus hợp lý và không
  có focus trap.
- Mọi control tương tác phải có focus indicator nhìn thấy rõ.
- Mode tabs, input-source selector và result tabs phải thể hiện trạng thái chọn qua
  semantics/ARIA phù hợp.
- Drop zone phải dùng được bằng Enter/Space và có accessible label.
- Result/status/notice thay đổi phải được công bố qua live region phù hợp.
- Trạng thái lỗi không được phân biệt chỉ bằng màu; phải có icon/text mô tả.
- Trong loading, control thực sự không thao tác được; chỉ đặt thuộc tính trang trí
  trên custom element là chưa đủ.
- Khi mở khóa sau success/failure, action chỉ bật lại nếu input và key vẫn hợp lệ.

## 10. Những hành vi demo cũ FE không được copy

[`Caesar_Cipher_Tool_Demo.html`](../Caesar_Cipher_Tool_Demo.html) chỉ là UI reference
cũ. FE không được sao chép các hành vi sau:

- giới hạn file `1 MB` thay vì `5 MiB`;
- tên tải xuống dùng `_encrypted.txt`/`_decrypted.txt` thay vì dấu chấm;
- `USE_MOCK`, mock API hoặc tự tính result Caesar trong browser;
- `API_BASE=http://localhost:8080` hay bất kỳ backend host/port ghi cứng nào;
- bỏ `response_mode` trong multipart request;
- download file từ preview Blob làm mất trạng thái BOM;
- coi whitespace-only là text rỗng;
- chỉ hiện download cho nguồn file;
- nhãn/nội dung lỗi tiếng Anh như `Copy`, `Clear`, `Network error`;
- banner backend giả lập, dead navigation hoặc link không có đích.

FE có thể tham khảo ý tưởng mode tabs, input panels, analysis và shift-map của demo,
nhưng accepted behavior trong OpenSpec là bắt buộc.

## 11. Phạm vi loại trừ Week 1

Không thiết kế FE dựa trên các khả năng chưa tồn tại:

- database, persistence, session hoặc history;
- authentication/authorization;
- cipher thứ hai hoặc thuật toán chọn động;
- API cross-origin/CORS contract;
- upload lớn hơn 5 MiB hoặc streaming transform;
- CI/CD, cloud deployment hoặc public production hardening;
- rate limiting.

Đây là công cụ học tập. Không dùng Caesar Cipher để bảo vệ dữ liệu nhạy cảm và
không phơi backend trực tiếp ra Internet nếu chưa có reverse proxy/body limit/rate
limit phù hợp.

## 12. Thứ tự nguồn và quy tắc bảo trì

Thứ tự áp dụng cho FE integration:

1. [Completed OpenSpec change](../openspec/changes/caesar-cipher-week1-mvp/), đặc
   biệt các spec `web-ui`, `text-cipher-api`, `file-cipher-api`, `error-handling`,
   `caesar-core` và `app-runtime`.
2. Accepted backend implementation tại commit
   `fa009eb92b953000afd1a8c31273ae73d901a84a` để làm rõ cách contract được hiện thực.
3. [`BE Scope – Week 1 Caesar Cipher MVP.docx`](<../BE Scope – Week 1 Caesar Cipher MVP.docx>)
   và [bản Markdown bảo tồn](../docs/reference/be-scope-v1.0.md) để truy vết phạm vi.
4. [Demo HTML cũ](../Caesar_Cipher_Tool_Demo.html) chỉ để tham khảo hình thức.

Không đưa ma trận scenario đầy đủ, lịch sử quyết định, benchmark hoặc phương án đã
loại vào consumer guide này; chúng thuộc OpenSpec.

**Quy tắc bảo trì:** mọi thay đổi API hoặc behavior phải cập nhật OpenSpec trước,
sau đó cập nhật tài liệu này trong cùng change. Không sửa guide trước để tạo ra một
contract chưa được chấp nhận.

## 13. Checklist nghiệm thu FE integration

- [ ] FE dùng URL `/api/...` tương đối; dev server proxy `/api`, không yêu cầu CORS.
- [ ] Encrypt/decrypt text gửi JSON integer, không gửi numeric string.
- [ ] Text whitespace-only được chấp nhận; empty string bị chặn/được backend từ chối.
- [ ] Result hiển thị/copy/download đúng từng ký tự server trả về.
- [ ] Không có client-side Caesar result; shift-map chỉ là minh họa.
- [ ] File preview dùng `response_mode=content`.
- [ ] File download dùng request thứ hai với `response_mode=file`.
- [ ] File đúng 5 MiB được nhận; lớn hơn một byte bị từ chối.
- [ ] UI hiển thị nguyên văn lỗi `5 MB` dù nhãn giới hạn là 5 MiB.
- [ ] `.txt` được kiểm tra không phân biệt hoa thường.
- [ ] Error ở mode `file` được đọc như JSON, không như attachment.
- [ ] Filename `.encrypted.txt`/`.decrypted.txt`, UTF-8 BOM và LF/CRLF được bảo toàn.
- [ ] Input/key/mode/source thay đổi hoặc request lỗi đều xóa stale result.
- [ ] Loading khóa toàn bộ control và chặn submit/file-drop lặp.
- [ ] Clear từng vùng và reset toàn trang có hành vi khác nhau đúng state table.
- [ ] UI dùng được bằng bàn phím, có focus indicator, semantics và live region.
- [ ] Không có hành vi cũ bị cấm từ demo HTML.
- [ ] `/docs` và `/openapi.json` được dùng để đối chiếu contract khi tích hợp.
- [ ] Mọi behavior change đã cập nhật OpenSpec và guide trong cùng change.
