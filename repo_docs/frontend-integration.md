# Handoff tích hợp Frontend — Caesar, Vigenère và Playfair

Tài liệu này là **consumer contract duy nhất cho Frontend** khi tích hợp với backend
Caesar, Vigenère và Playfair. Nội dung độc lập framework: FE có thể dùng React,
Vue, Svelte hoặc JavaScript thuần, nhưng hành vi API và trạng thái quan sát được
phải giữ đúng contract dưới đây.

- Backend áp dụng: commit `1792a29a8925dc7122ebbe62fe55caef14a00a18`.
- Ngày cập nhật guide: `2026-09-18`.
- Backend hiện có 9 endpoint cipher; UI static đang đi kèm backend vẫn là UI
  Caesar-only. Việc FE bổ sung control cho Vigenère/Playfair không thay đổi backend.
- [OpenSpec Playfair/Vigenère đã hoàn thành](../openspec/changes/add-playfair-vigenere-ciphers/),
  [OpenSpec Caesar Week 1](../openspec/changes/caesar-cipher-week1-mvp/) và runtime/OpenAPI
  tại commit trên là nguồn có thẩm quyền. Guide này chỉ phản chiếu contract đó.

## 1. Nguyên tắc tích hợp

FE bắt buộc giữ nguyên:

- endpoint, method, content type, field và kiểu key theo từng cipher;
- response JSON đúng hai trường, status và thứ tự validation;
- kết quả do server tính; FE không tự tính result dùng trong production;
- file preview/download hai request, giới hạn 5 MiB, UTF-8, BOM và filename;
- xóa stale result khi cipher/mode/source/input/key thay đổi hoặc request lỗi;
- same-origin và URL `/api/...` tương đối.

FE được tự do chọn framework, component/state store, layout, CSS và cách tổ chức
API client. FE validation chỉ hỗ trợ UX; backend luôn là authority cuối cùng.

## 2. Runtime boundary và kiến trúc

```text
Browser / FE
  │
  │  same-origin: /api/{cipher}/...
  ▼
FastAPI :8000
  ├── request guards: valid Content-Length > 64 MiB + multipart framing
  ├── HTTP adapters + validation precedence
  ├── file processing: .txt / 5 MiB / UTF-8 / BOM / filename
  ├── canonical error handlers
  └── pure core theo từng thuật toán
        ├── Caesar
        ├── Vigenère
        └── Playfair
  │
  └── JSON preview/error hoặc text/plain attachment
```

Backend phục vụ UI và API cùng origin trên cổng `8000`. FE gọi đường dẫn tương đối,
ví dụ `/api/vigenere/encrypt`; không ghi cứng backend host/port trong production.

Khi chạy FE dev server riêng, cấu hình dev proxy theo contract tương đương:

```text
/api/*  ──proxy──>  http://localhost:8000/api/*
```

Không yêu cầu backend bật CORS cho workflow này. Không khôi phục `API_BASE` trỏ
`localhost:8080`, mock toggle hoặc local cipher service từ demo cũ.

Machine-readable surfaces của backend đang chạy:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

Không copy OpenAPI thành một YAML tĩnh khác trong FE vì bản sao sẽ dễ trôi lệch.
Backend stateless: không lưu input, key, file, result, session hoặc history sau request.

## 3. Danh mục 9 endpoint

| Cipher | Text encrypt | Text decrypt | File |
|---|---|---|---|
| Caesar | `POST /api/caesar/encrypt` | `POST /api/caesar/decrypt` | `POST /api/caesar/file` |
| Vigenère | `POST /api/vigenere/encrypt` | `POST /api/vigenere/decrypt` | `POST /api/vigenere/file` |
| Playfair | `POST /api/playfair/encrypt` | `POST /api/playfair/decrypt` | `POST /api/playfair/file` |

Text endpoints nhận `application/json`. File endpoints nhận
`multipart/form-data` và có cùng hai response mode: `content` hoặc `file`.

## 4. Thuật toán FE cần hiểu

Phần này chỉ đủ để FE giải thích UX và viết test. **Server là nơi duy nhất tạo kết
quả chính thức.** Visualization phía client không được thay thế response server.

### 4.1 Caesar

Với khóa `k`, backend chuẩn hóa bằng modulo 26:

```text
k' = ((k mod 26) + 26) mod 26
Encrypt: E(x) = (x + k') mod 26
Decrypt: D(x) = (x - k') mod 26
```

Chỉ ASCII `A-Z`/`a-z` thay đổi và giữ case. Số, dấu câu, whitespace, LF/CRLF,
chữ có dấu, emoji và Unicode khác giữ nguyên đúng vị trí.

```text
Hello World + key 3  → Khoor Zruog
Khoor Zruog + key 3 → Hello World
Xin chào! Zz + key 29 → Alq fkàr! Cc
```

Trong Caesar mode, FE phải giữ shift-map hai hàng 26 chữ cái theo accepted UI;
shift-map chỉ là visualization, không phải result production. Hiển thị thêm giá trị
key đã chuẩn hóa bên cạnh là tùy chọn.

### 4.2 Vigenère repeating-key

Key là chuỗi không rỗng chỉ gồm ASCII `A-Z`/`a-z`, được backend chuyển uppercase.
Key lặp lại; chỉ chữ cái ASCII trong input tiêu thụ một vị trí key. Case input được
giữ; whitespace, CRLF, số, dấu câu và mọi Unicode ngoài ASCII giữ nguyên và không
làm key tiến lên.

```text
Plaintext:  Attack at dawn!
Key stream: LEMONL EM ONLE
Encrypt:    Lxfopv ef rnhr!
Decrypt:    Attack at dawn!
```

Ví dụ key-position: `AéA` với key `BC` mã hóa thành `BéC`; `é` không tiêu thụ `C`.

### 4.3 Playfair 5×5

Playfair là luồng **normalize có mất dữ liệu**:

1. Keyword: uppercase ASCII → chỉ giữ `A-Z` → `J` thành `I` → loại trùng, giữ lần đầu.
2. Matrix 5×5 điền keyword rồi alphabet `A-Z` bỏ `J`, theo hàng.
3. Plaintext: uppercase ASCII, loại mọi non-letter, `J` thành `I`.
4. Chia digraph. Cặp lặp hoặc ký tự cuối lẻ dùng filler `X`; nếu ký tự đang xử lý
   là `X`, dùng fallback `Q` để tránh cặp `XX`.
5. Encrypt/decrypt theo rule cùng hàng, cùng cột hoặc hình chữ nhật.

Matrix cho key `PLAYFAIR EXAMPLE`:

```text
P L A Y F
I R E X M
B C D G H
K N O Q S
T U V W Z
```

Các vector bắt buộc:

| Operation | Input | Prepared/normalized | Result |
|---|---|---|---|
| Encrypt | `HIDE THE GOLD IN THE TREE STUMP` | `HIDETHEGOLDINTHETREXESTUMP` | `BMODZBXDNABEKUDMUIXMMOUVIF` |
| Decrypt | `BMODZBXDNABEKUDMUIXMMOUVIF` | — | `HIDETHEGOLDINTHETREXESTUMP` |
| Encrypt | `XX` | `XQXQ` | `GWGW` |
| Encrypt | `ABX` | `ABXQ` | `PDGW` |
| Decrypt | `GWGW` | — | `XQXQ` |

Playfair output luôn uppercase ASCII. Decrypt giữ nguyên mọi `X`/`Q`; backend
không đoán filler nào được chèn và không phục hồi `J`, case, whitespace, dấu câu
hoặc Unicode đã bị loại. FE **không được heuristic-strip filler** và **không được
cố dựng lại formatting nguyên bản**. UI phải cảnh báo rõ rằng round-trip Playfair
chỉ trả prepared plaintext, không phải input ban đầu.

## 5. TypeScript contract dùng trực tiếp

Các type dưới đây mô tả consumer model. Caesar text dùng integer token; Vigenère
và Playfair dùng string key. Multipart luôn truyền field `key` dưới dạng chuỗi.

```ts
export type Cipher = "caesar" | "vigenere" | "playfair";
export type StringKeyCipher = Exclude<Cipher, "caesar">;
export type Operation = "encrypt" | "decrypt";
export type ResponseMode = "content" | "file";

export interface SuccessResponse {
  success: true;
  result: string;
}

export interface ErrorResponse {
  success: false;
  message: string;
}

/** OpenAPI/wire shape khi key nằm trong Number safe range. */
export interface CaesarTextRequest {
  text: string;
  key: number;
}

export interface StringKeyTextRequest {
  text: string;
  key: string;
}

export interface CaesarTextInput {
  cipher: "caesar";
  text: string;
  /** Chuỗi integer người dùng nhập; serializer phát JSON number token. */
  key: string;
}

export interface StringKeyTextInput {
  cipher: StringKeyCipher;
  text: string;
  key: string;
}

export type TextInput = CaesarTextInput | StringKeyTextInput;

export interface FileInput {
  cipher: Cipher;
  file: File;
  /** FormData luôn truyền string; backend áp policy theo cipher. */
  key: string;
  action: Operation;
}

export interface AttachmentResult {
  blob: Blob;
  filename: string;
}
```

Lưu ý: wire request Caesar text bắt buộc là JSON integer, không phải string.
`CaesarTextInput.key` là chuỗi UI để tránh mất chính xác trong JavaScript; helper
ở phần sau phát token số không có dấu nháy. Không gọi `JSON.stringify()` trực tiếp
trên `bigint`. `CaesarTextRequest` mô tả shape OpenAPI cho integer nằm trong safe
range; với integer lớn hơn, dùng serializer raw-token thay vì ép sang `number`.
`StringKeyTextRequest` có thể được `JSON.stringify()` trực tiếp.

## 6. JSON response và xử lý lỗi

Mọi success dùng đúng HTTP `200`. Success JSON luôn đúng hai trường:

```json
{"success":true,"result":"Khoor Zruog"}
```

JSON error luôn đúng hai trường, kể cả request `response_mode=file`:

```json
{"success":false,"message":"Khóa phải là số nguyên."}
```

Không có machine `code`, `detail`, field errors, `normalizedInput`, matrix hoặc
metadata bổ sung. FE phải hiển thị `message` tiếng Việt hợp lệ do server trả về,
nhưng **không dùng nội dung message làm stable identifier hoặc nhánh business**.
Để quản lý UI, dùng request context (cipher/field/action) và HTTP status; message
chỉ dành cho người dùng.

Helper TypeScript framework-neutral:

```ts
class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) return false;
  const body = value as Record<string, unknown>;
  return body.success === false && typeof body.message === "string";
}

async function readJsonSuccess(response: Response): Promise<SuccessResponse> {
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  if (!contentType.includes("application/json")) {
    throw new ApiError("Đã xảy ra lỗi hệ thống.", response.status);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError("Đã xảy ra lỗi hệ thống.", response.status);
  }

  if (response.status !== 200 || isErrorResponse(body)) {
    const message = isErrorResponse(body)
      ? body.message
      : "Đã xảy ra lỗi hệ thống.";
    throw new ApiError(message, response.status);
  }

  const success = body as Partial<SuccessResponse>;
  if (success.success !== true || typeof success.result !== "string") {
    throw new ApiError("Đã xảy ra lỗi hệ thống.", response.status);
  }
  return success as SuccessResponse;
}
```

## 7. Text flow

### 7.1 Request shape và key

| Cipher | JSON body | Key hợp lệ |
|---|---|---|
| Caesar | `{"text":"...","key":3}` | JSON integer thật; âm, 0, >25 và integer rất lớn đều hợp lệ |
| Vigenère | `{"text":"...","key":"LEMON"}` | String không rỗng, toàn bộ khớp `[A-Za-z]+` |
| Playfair | `{"text":"...","key":"PLAYFAIR EXAMPLE"}` | String không rỗng và còn ít nhất một ASCII letter sau normalization |

`text` phải là string khác rỗng. Whitespace-only hợp lệ với Caesar/Vigenère;
Playfair đi tiếp qua normalization rồi bị từ chối vì không còn ASCII letter.

Caesar từ chối boolean, float, numeric string, array và object làm key. Vigenère/
Playfair từ chối key JSON có giá trị nhưng không phải string bằng message
`Khóa phải là chuỗi.`

### 7.2 Native fetch

```ts
function caesarJsonBody(text: string, rawKey: string): string {
  const value = rawKey.trim();
  if (!/^[+-]?[0-9]+$/.test(value)) {
    throw new Error(value === "" ? "Thiếu khóa." : "Khóa phải là số nguyên.");
  }
  const integerToken = BigInt(value).toString();
  return `{"text":${JSON.stringify(text)},"key":${integerToken}}`;
}

async function transformText(
  operation: Operation,
  input: TextInput,
): Promise<SuccessResponse> {
  const body = input.cipher === "caesar"
    ? caesarJsonBody(input.text, input.key)
    : JSON.stringify({ text: input.text, key: input.key });

  const response = await fetch(`/api/${input.cipher}/${operation}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return readJsonSuccess(response);
}
```

FE phải xóa result/analysis cũ trước khi gọi, khóa control khi request đang chạy,
và chỉ hiển thị/copy/download `result` nhận từ server.

Với **nguồn text**, FE được tạo file UTF-8 từ chính `result` server bằng `Blob`;
tên mặc định hiện hành là `ket-qua.encrypted.txt` hoặc `ket-qua.decrypted.txt`.
Quy tắc request attachment lần hai ở phần file chỉ áp dụng cho **nguồn file upload**.

### 7.3 curl

```bash
curl -sS -X POST http://localhost:8000/api/caesar/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello World","key":3}'
# {"success":true,"result":"Khoor Zruog"}

curl -sS -X POST http://localhost:8000/api/vigenere/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Attack at dawn!","key":"LEMON"}'
# {"success":true,"result":"Lxfopv ef rnhr!"}

curl -sS -X POST http://localhost:8000/api/playfair/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"HIDE THE GOLD IN THE TREE STUMP","key":"PLAYFAIR EXAMPLE"}'
# {"success":true,"result":"BMODZBXDNABEKUDMUIXMMOUVIF"}

# Representative text error: Vigenère key có khoảng trắng
curl -sS -i -X POST http://localhost:8000/api/vigenere/encrypt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Attack","key":"LE MON"}'
# HTTP 422; {"success":false,"message":"Khóa Vigenère chỉ được chứa chữ cái A-Z hoặc a-z."}
```

Đổi `encrypt` thành `decrypt` và truyền ciphertext tương ứng để gọi ba endpoint
decrypt. Ví dụ Playfair decrypt trả normalized/prepared plaintext, không phục hồi input.

## 8. File flow

### 8.1 Multipart contract

| Field | Bắt buộc | Giá trị |
|---|---:|---|
| `file` | Có | File có filename kết thúc bằng `.txt`, không phân biệt hoa thường |
| `key` | Có | String trong multipart; policy phụ thuộc cipher |
| `action` | Có | Chính xác `encrypt` hoặc `decrypt` |
| `response_mode` | Không | `content` hoặc `file`; mặc định `content` |

Không tự đặt `Content-Type` khi gửi `FormData`; browser phải thêm multipart boundary.
`action` và `response_mode` phân biệt hoa thường.

Caesar multipart key được trim, phải khớp `[+-]?[0-9]+` và dài tối đa 32 ký tự.
Vigenère key phải khớp `[A-Za-z]+` mà không tự trim/sửa. Playfair key lọc ký tự
không phải ASCII letter và hợp lệ nếu normalization còn ít nhất một chữ cái.

### 8.2 Hai request bắt buộc

1. Preview: gửi file gốc với `response_mode=content`; nhận JSON `{success,result}`.
2. Download: khi người dùng bấm tải, gửi lại file gốc bằng request thứ hai với
   `response_mode=file`; nhận attachment server-owned.

FE không được đóng preview result vào Blob để giả làm official file download.
Preview không mang trạng thái BOM đầu vào và không phải authority cho filename.

### 8.3 Native fetch

```ts
function createFileForm(
  input: FileInput,
  responseMode: ResponseMode,
): FormData {
  const data = new FormData();
  data.append("file", input.file);
  data.append("key", input.key);
  data.append("action", input.action);
  data.append("response_mode", responseMode);
  return data;
}

async function previewFile(input: FileInput): Promise<SuccessResponse> {
  const response = await fetch(`/api/${input.cipher}/file`, {
    method: "POST",
    body: createFileForm(input, "content"),
  });
  return readJsonSuccess(response);
}

function attachmentFilename(disposition: string): string | null {
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8) return decodeURIComponent(utf8[1]);

  const quoted = disposition.match(/filename="((?:\\.|[^"])*)"/i);
  return quoted ? quoted[1].replace(/\\([\\"])/g, "$1") : null;
}

async function downloadFile(input: FileInput): Promise<AttachmentResult> {
  const response = await fetch(`/api/${input.cipher}/file`, {
    method: "POST",
    body: createFileForm(input, "file"),
  });
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";

  if (response.status !== 200 || contentType.includes("application/json")) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Dùng fallback bên dưới.
    }
    throw new ApiError(
      isErrorResponse(body) ? body.message : "Không thể tải kết quả. Vui lòng thử lại.",
      response.status,
    );
  }

  if (!contentType.startsWith("text/plain")) {
    throw new ApiError("Đã xảy ra lỗi hệ thống.", response.status);
  }
  const filename = attachmentFilename(
    response.headers.get("content-disposition") ?? "",
  );
  if (!filename) throw new ApiError("Đã xảy ra lỗi hệ thống.", response.status);

  return { blob: await response.blob(), filename };
}
```

Sau khi nhận `AttachmentResult`, FE tạo object URL, kích hoạt download bằng
`filename` từ server và gọi `URL.revokeObjectURL()` sau khi dùng.

### 8.4 curl

```bash
# Caesar preview
curl -sS -X POST http://localhost:8000/api/caesar/file \
  -F 'file=@input.txt;type=text/plain' -F 'key=3' \
  -F 'action=encrypt' -F 'response_mode=content'

# Vigenère preview
curl -sS -X POST http://localhost:8000/api/vigenere/file \
  -F 'file=@input.txt;type=text/plain' -F 'key=LEMON' \
  -F 'action=encrypt' -F 'response_mode=content'

# Playfair preview
curl -sS -X POST http://localhost:8000/api/playfair/file \
  -F 'file=@input.txt;type=text/plain' -F 'key=PLAYFAIR EXAMPLE' \
  -F 'action=encrypt' -F 'response_mode=content'

# Official attachment; áp dụng tương tự cho cả ba cipher
curl -sS -OJ -X POST http://localhost:8000/api/playfair/file \
  -F 'file=@input.txt;type=text/plain' -F 'key=PLAYFAIR EXAMPLE' \
  -F 'action=encrypt' -F 'response_mode=file'

# Representative file error: lỗi vẫn là JSON dù yêu cầu attachment
curl -sS -i -X POST http://localhost:8000/api/caesar/file \
  -F 'file=@input.md;type=text/plain' -F 'key=3' \
  -F 'action=encrypt' -F 'response_mode=file'
# HTTP 415; {"success":false,"message":"Chỉ chấp nhận file .txt."}
```

### 8.5 Byte, encoding, BOM và filename

- Giới hạn chính xác: `5 MiB = 5 * 1024 * 1024 = 5.242.880 byte` nội dung file.
- Đúng `5.242.880` byte qua bước size; `5.242.881` byte trả HTTP `413`.
- Message cố ý dùng `File vượt quá dung lượng tối đa 5 MB.` dù phép đo là MiB.
- Chỉ chấp nhận UTF-8 thường hoặc UTF-8 có BOM. Invalid UTF-8 trả HTTP `415`.
- Content preview không chứa `U+FEFF` ở đầu result.
- Attachment giữ BOM nếu và chỉ nếu input có BOM.
- File `0` byte bị từ chối. Whitespace-only hợp lệ với Caesar/Vigenère nhưng không
  hợp lệ với Playfair sau normalization.
- `.txt` kiểm tra không phân biệt hoa thường; `a.txt.exe` bị từ chối.

Filename do server tạo:

```text
note.txt       + encrypt → note.encrypted.txt
note.txt       + decrypt → note.decrypted.txt
bao.cao.TXT    + encrypt → bao.cao.encrypted.txt
```

Server chỉ bỏ phần `.txt` cuối cùng, giữ các dấu chấm trước đó, không thêm tên
thuật toán và luôn dùng `.txt` thường cho output.

### 8.6 Nội dung file theo cipher

| Cipher | LF/CRLF, whitespace, số, dấu câu | Unicode ngoài ASCII | Case/output |
|---|---|---|---|
| Caesar | Giữ nguyên | Giữ nguyên | Chỉ ASCII letter đổi, giữ case |
| Vigenère | Giữ nguyên; không làm key tiến | Giữ nguyên; không làm key tiến | Chỉ ASCII letter đổi, giữ case |
| Playfair | Bị loại khi normalize | Bị loại | Uppercase ASCII, `J→I`, có thể có filler `X/Q` |

## 9. Validation, status và message

| Status | Trường hợp | Message chính xác |
|---:|---|---|
| `200` | Text/content mode thành công hoặc file mode trả attachment | Không có error message |
| `413` | File vượt 5 MiB hoặc file-route request có một `Content-Length` hợp lệ lớn hơn 64 MiB | `File vượt quá dung lượng tối đa 5 MB.` |
| `413` | Request text có một `Content-Length` decimal hợp lệ lớn hơn 64 MiB | `Yêu cầu vượt quá dung lượng cho phép.` |
| `415` | Filename không kết thúc `.txt` | `Chỉ chấp nhận file .txt.` |
| `415` | File không phải UTF-8 | `File phải sử dụng UTF-8.` |
| `422` | JSON/multipart không đọc được | `Dữ liệu gửi lên không hợp lệ.` |
| `422` | Text thiếu, null, rỗng hoặc sai kiểu | `Văn bản không được để trống.` |
| `422` | Key thiếu, null hoặc chuỗi rỗng | `Thiếu khóa.` |
| `422` | Caesar key có giá trị nhưng không phải integer | `Khóa phải là số nguyên.` |
| `422` | Vigenère/Playfair JSON key có giá trị nhưng không phải string | `Khóa phải là chuỗi.` |
| `422` | Vigenère key có ký tự ngoài ASCII letter | `Khóa Vigenère chỉ được chứa chữ cái A-Z hoặc a-z.` |
| `422` | Playfair key normalize không còn ASCII letter | `Khóa Playfair phải chứa ít nhất một chữ cái A-Z hoặc a-z.` |
| `422` | Playfair text normalize không còn ASCII letter | `Văn bản Playfair phải chứa ít nhất một chữ cái A-Z hoặc a-z.` |
| `422` | Playfair ciphertext có số letter lẻ | `Bản mã Playfair phải chứa số lượng chữ cái chẵn.` |
| `422` | Playfair ciphertext có digraph hai letter giống nhau | `Bản mã Playfair không được chứa cặp hai chữ cái giống nhau.` |
| `422` | Thiếu file | `Thiếu file.` |
| `422` | File 0 byte | `File không được để trống.` |
| `422` | Action thiếu/sai | `Action phải là encrypt hoặc decrypt.` |
| `422` | Response mode sai | `Response mode phải là content hoặc file.` |
| `500` | Lỗi đọc file | `Không thể đọc file.` |
| `500` | Lỗi hệ thống khác | `Đã xảy ra lỗi hệ thống.` |

Thứ tự lỗi text sau request-size guard:

```text
JSON object đọc được
→ text presence/type/non-empty
→ key presence
→ key type
→ key policy của cipher
→ Playfair normalized text/ciphertext validation
```

Thứ tự lỗi file sau request-size/multipart guard:

```text
multipart đọc được
→ file presence
→ key presence
→ action presence
→ key format/policy
→ action value
→ response_mode
→ extension
→ 5 MiB
→ 0 byte
→ UTF-8
→ Playfair normalized content/ciphertext validation
```

Backend dừng ở lỗi đầu tiên. FE không nên tự suy diễn rằng lỗi file/encoding đã
qua chỉ vì request bị từ chối sớm ở key.

Trần hạ tầng 64 MiB chỉ từ chối sớm khi request có **đúng một** header
`Content-Length` decimal hợp lệ và giá trị vượt trần. Header thiếu, trùng hoặc sai
định dạng được chuyển tiếp để tầng sau xử lý; điều này không thay đổi giới hạn file
nghiệp vụ 5 MiB được đếm từ bytes nội dung upload.

## 10. FE validation và phân chia trách nhiệm

| FE chịu trách nhiệm | Backend chịu trách nhiệm |
|---|---|
| Kiểm tra sơ bộ để bật/tắt action | Kiểm tra wire type, policy và precedence thật |
| Giữ key input type phù hợp cipher | Normalize/validate key và chạy core |
| Hiển thị cảnh báo Playfair lossy | Quyết định prepared plaintext và filler |
| Kiểm tra sơ bộ extension, `File.size`, 0 byte | Đếm byte, UTF-8, BOM và filename attachment |
| Loading, stale-result clearing, focus, live region | Status và exact response envelope/message |
| Visualization minh họa | Result production-authoritative |
| Dùng attachment/filename server trả | Quyết định bytes, BOM và official filename |

FE không được:

- coi client validation là bằng chứng request chắc chắn hợp lệ;
- tính Caesar/Vigenère/Playfair client-side để thay result server;
- trim/sửa key Vigenère rồi gửi một giá trị khác người dùng nhập;
- xóa filler Playfair hoặc phục hồi formatting bằng heuristic;
- dùng preview Blob làm official download cho nguồn file;
- branch business logic theo chuỗi message tiếng Việt.

## 11. UI state và transition

State tối thiểu:

```text
cipher     = caesar | vigenere | playfair
mode       = encrypt | decrypt
source     = text | file
text/file  = input hiện tại
key        = raw input
result     = null | server result
loading    = boolean
error      = null | user-facing message
view       = result | analysis
```

| Event | State bắt buộc | UX |
|---|---|---|
| Mở trang | `cipher=caesar`, `mode=encrypt`, `source=text`, `result=null`, `loading=false` | Action disabled tới khi hợp lệ |
| Đổi cipher | Xóa result/analysis/error; validate lại key/input | Đổi key hint và Playfair warning |
| Đổi encrypt/decrypt | Giữ input/key nếu phù hợp; xóa stale result/error | Đổi label plaintext/ciphertext |
| Đổi text/file | Bắt buộc giữ draft riêng của text và file; xóa result/error | Hiện panel nguồn mới |
| Sửa text, file hoặc key | Xóa result/analysis/error | Validate lại ngay |
| Submit preview/text | Xóa result; `loading=true` | Khóa control và chặn submit lặp |
| Success | Lưu đúng server result; xóa error | Mở copy/download |
| API/network failure | `result=null`, xóa analysis; lưu fallback/message | Mở khóa để retry |
| Download click | Request file mode lần hai | Không dùng preview Blob |
| Download failure | Xóa trạng thái success cũ | Hiện lỗi, không kích hoạt download |
| Clear output | Chỉ xóa result/analysis | Giữ input/key |
| Reset | Xóa toàn bộ state/draft/result/error; đưa status về neutral và view về result | Quay lại `caesar` + `encrypt` + `text` |

Playfair phải có cảnh báo luôn nhìn thấy trước submit hoặc cạnh result:

> Playfair chuẩn hóa thành chữ hoa ASCII, gộp J/I, loại định dạng và giữ filler
> X/Q khi giải mã; kết quả không khôi phục nguyên văn đầu vào.

Trong loading, khóa mọi đường thay đổi/gửi lặp: click, keyboard shortcut,
Enter/Space trên drop zone và file drop. Status/error/result thay đổi phải được công
bố qua live region; lỗi không chỉ biểu diễn bằng màu; mọi control dùng được bằng
bàn phím và có focus indicator.

Các invariant UI Week 1 tiếp tục bắt buộc khi mở rộng thêm cipher:

- Có ba status độc lập cho input, key và output; mỗi status có neutral/valid/error
  bằng text và dấu hiệu không chỉ dựa vào màu.
- Result read-only có hai tab **Văn bản** và **Phân tích**; mặc định là Văn bản.
  Analysis chỉ diễn giải server result/input, không tự tạo ciphertext/plaintext.
- Copy/Clear output và Download bị vô hiệu khi chưa có result. Clear output giữ
  input/key; Reset toàn trang có semantics riêng như bảng trên.
- Notice success/error đóng được và tự ẩn khi cipher/mode/source/input/key thay đổi.
- File panel hỗ trợ picker lẫn drag/drop, hiển thị tên, kích thước nhị phân, preview,
  **Đổi file** và **Gỡ file**.
- Caesar mode giữ **Tạo ví dụ** (`Hello World`, key `3`) và shift-map hai hàng 26
  chữ cái. Shift-map chỉ là visualization client-side; production result vẫn từ server.
- Tabs/selectors/drop zone có semantics/ARIA phù hợp; copy failure có thông báo
  tiếng Việt và không làm UI kẹt.

Ma trận UI đầy đủ vẫn nằm trong
[accepted web-ui spec](../openspec/changes/caesar-cipher-week1-mvp/specs/web-ui/spec.md);
phần tóm tắt này không làm yếu bất kỳ requirement nào của spec đó.

## 12. Migration checklist từ UI Caesar-only

- [ ] Thêm selector `caesar | vigenere | playfair`; không tạo endpoint động ngoài bảng 9 endpoint.
- [ ] Route text/file dựa trên cipher đang chọn và luôn là URL `/api/...` tương đối.
- [ ] Giữ input key dạng raw string trong UI; serialize Caesar text thành JSON integer token.
- [ ] Dùng string key nguyên trạng cho Vigenère/Playfair; đổi hint/validation theo cipher.
- [ ] Thêm cảnh báo Playfair lossy, uppercase, `J→I` và retained filler `X/Q`.
- [ ] Xóa stale result khi cipher/mode/source/input/key thay đổi hoặc request thất bại.
- [ ] Preview file dùng `response_mode=content`; download dùng request thứ hai mode `file`.
- [ ] Dùng server attachment và filename; không tạo official file từ preview.
- [ ] Gỡ mock, `USE_MOCK`, local cipher result và hard-coded `API_BASE`/cổng 8080.
- [ ] Dev server proxy `/api` tới backend 8000; không yêu cầu CORS.
- [ ] Không thêm `normalizedInput`, machine `code` hoặc nhánh logic theo error message.

## 13. Hành vi demo cũ không được sao chép

[`Caesar_Cipher_Tool_Demo.html`](../Caesar_Cipher_Tool_Demo.html) chỉ là reference UI cũ.
Không sao chép:

- giới hạn `1 MB` thay vì 5 MiB;
- `_encrypted.txt`/`_decrypted.txt` thay vì `.encrypted.txt`/`.decrypted.txt`;
- mock API, `USE_MOCK` hoặc local Caesar service;
- `API_BASE=http://localhost:8080` hay backend URL hard-coded;
- CORS như một yêu cầu mặc định cho dev;
- bỏ `response_mode` hoặc tải file từ preview Blob;
- message/label tiếng Anh hoặc error shape có `code`;
- bất kỳ client-generated production result nào.

Demo không định nghĩa Playfair/Vigenère. Các ý tưởng layout có thể tham khảo, nhưng
runtime/OpenSpec hiện tại quyết định hành vi.

## 14. Acceptance checklist

- [ ] Cả 9 endpoint được chọn đúng theo cipher/source/operation.
- [ ] Caesar vector `Hello World`, key `3` cho `Khoor Zruog` và decrypt đúng chiều ngược lại.
- [ ] Vigenère vector `Attack at dawn!`/`LEMON` cho `Lxfopv ef rnhr!` và decrypt đúng.
- [ ] Playfair canonical vector cho `BMODZBXDNABEKUDMUIXMMOUVIF` và decrypt giữ prepared text.
- [ ] Playfair `XX→XQXQ→GWGW`, `ABX→ABXQ→PDGW`, `GWGW→XQXQ` đều đúng.
- [ ] FE không strip filler và hiển thị cảnh báo Playfair không lossless.
- [ ] Caesar text gửi JSON integer; Vigenère/Playfair text gửi string key.
- [ ] Whitespace-only: Caesar/Vigenère thành công, Playfair trả normalized-empty 422.
- [ ] Vigenère giữ Unicode/CRLF và không làm key tiến; Caesar giữ non-ASCII/CRLF.
- [ ] Playfair loại Unicode/CRLF/format và trả uppercase ASCII.
- [ ] Validation hiển thị server message nhưng không dùng message làm identifier.
- [ ] Error envelope chỉ có `success,message`; success JSON chỉ có `success,result`.
- [ ] Preview và download file là hai request; lỗi file mode vẫn được đọc như JSON.
- [ ] File đúng `5.242.880` byte qua size; thêm một byte trả 413.
- [ ] Invalid UTF-8 trả 415; `.TXT` hợp lệ; `.txt.exe` bị từ chối.
- [ ] Content preview bỏ BOM; attachment giữ BOM đúng theo input.
- [ ] Filename dùng `.encrypted.txt`/`.decrypted.txt`, kể cả tên nhiều dấu chấm.
- [ ] Cipher/mode/source/input/key thay đổi hoặc request lỗi đều xóa stale result.
- [ ] Loading chặn submit/drop lặp; UI có keyboard, focus và live-region behavior.
- [ ] Caesar regression: ba endpoint và integer-key contract cũ vẫn hoạt động như trước.
- [ ] FE dùng same-origin `/api`; local dev dùng proxy, không mock/CORS/API base cũ.
- [ ] `/docs` và `/openapi.json` được dùng để đối chiếu runtime contract.

## 15. Source precedence và bảo trì

Thứ tự áp dụng:

1. [Completed OpenSpec Playfair/Vigenère](../openspec/changes/add-playfair-vigenere-ciphers/)
   cùng [completed OpenSpec Caesar Week 1](../openspec/changes/caesar-cipher-week1-mvp/).
2. Runtime và `/openapi.json` tại backend commit
   `1792a29a8925dc7122ebbe62fe55caef14a00a18` để xác nhận cách contract được hiện thực.
3. Consumer guide này, là bản diễn giải dành cho FE và phải được sửa nếu lệch hai nguồn trên.
4. Source DOCX và [bản scope Caesar bảo tồn](../docs/reference/be-scope-v1.0.md) để truy vết.
5. Demo HTML/mock cũ chỉ để tham khảo, không có quyền ghi đè accepted behavior.

Guide không lặp toàn bộ ma trận scenario hoặc decision history của OpenSpec. Khi
API/behavior thay đổi, cập nhật OpenSpec trước, rồi cập nhật guide này trong cùng
change. Không thêm `/v1`, endpoint, field hoặc behavior mới chỉ bằng cách sửa tài liệu.
