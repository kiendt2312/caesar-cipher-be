<!-- Tự động trích từ 'BE Scope – Week 1 Caesar Cipher MVP.docx' v1.0. File .docx là bản gốc; file này chỉ để đọc/grep. -->


## SCOPE TUẦN 1 – CAESAR CIPHER WEB APP
Đặc tả chức năng và tiêu chí nghiệm thu
[TABLE]
| Phiên bản | 1.0 |
| Phạm vi | Tuần 1 |
| Loại ứng dụng | Web app chạy cùng FastAPI |
| Trạng thái | Đã thống nhất để triển khai |
[/TABLE]

### 1. Mục tiêu
Xây dựng một ứng dụng web Caesar Cipher có giao diện, cho phép người dùng nhập văn bản từ bàn phím hoặc tải file .txt, thực hiện mã hóa hoặc giải mã, xem kết quả và tải kết quả xuống.
Ứng dụng phải xử lý các trường hợp đặc biệt và hiển thị thông báo lỗi bằng tiếng Việt, rõ ràng, không để lỗi kỹ thuật hoặc stack trace xuất hiện trên giao diện.

### 2. Phạm vi chức năng

#### 2.1. Caesar Cipher Core
- Cung cấp một interface chính: transform_text(text, key, operation).
- Hỗ trợ hai operation: encrypt và decrypt.
- Chuẩn hóa mọi key về khoảng 0–25 bằng phép modulo 26; hỗ trợ key âm và key lớn hơn 25.
- Chỉ dịch các ký tự ASCII A-Z và a-z.
- Giữ nguyên chữ hoa/chữ thường, khoảng trắng, xuống dòng, số, tiếng Việt, Unicode và ký tự đặc biệt.
- Cùng một module Caesar Core phải được tái sử dụng cho cả input bàn phím và file.

#### 2.2. Giao diện web
- Giao diện được phục vụ từ chính ứng dụng FastAPI, không tách project frontend.
- Cho phép chuyển đổi giữa hai nguồn input: “Nhập văn bản” và “Tải file”.
- Có textarea nhập văn bản, file picker, ô nhập key và lựa chọn “Mã hóa”/“Giải mã”.
- Nhãn nút hành động đổi động theo chế độ (“Mã hóa”/“Giải mã”), không phải nhãn cố định. Có các nút: “Mã hóa”, “Sao chép”, “Xóa”, “Đổi file”, “Gỡ file”, “Tải kết quả”, “Tạo ví dụ” và “Làm mới”.
- Khu vực kết quả chỉ đọc; có thông báo thành công, lỗi và trạng thái đang xử lý.
- Trong lúc gửi request, khóa toàn bộ cụm điều khiển để tránh gửi lặp.
- Giao diện responsive và sử dụng được bằng bàn phím.

#### 2.3. Nhập văn bản từ bàn phím
- Người dùng nhập văn bản, key và chọn mã hóa hoặc giải mã.
- Kết quả được hiển thị trên giao diện.
- Người dùng có thể sao chép hoặc tải kết quả thành file UTF-8.

#### 2.4. Xử lý file văn bản
- Chỉ chấp nhận file có đuôi .txt, không phân biệt hoa thường.
- Dung lượng tối đa: 5 MiB.
- Chấp nhận UTF-8 thường và UTF-8 BOM; từ chối encoding không hợp lệ.
- Cho phép mã hóa hoặc giải mã nội dung file.
- Hiển thị bản xem trước kết quả và cho phép tải file kết quả.
- File kết quả có tên <ten-goc>.encrypted.txt hoặc <ten-goc>.decrypted.txt.
- Nếu file đầu vào có UTF-8 BOM, file tải xuống phải giữ BOM.

### 3. Luồng người dùng

#### 3.1. Luồng nhập bàn phím
- Chọn “Nhập văn bản”.
- Nhập văn bản và key.
- Chọn “Mã hóa” hoặc “Giải mã”.
- Nhấn nút hành động (“Mã hóa”/“Giải mã”) để xử lý.
- Xem kết quả, sao chép hoặc tải xuống.

#### 3.2. Luồng xử lý file
- Chọn “Tải file”.
- Chọn file .txt, nhập key và chọn operation.
- Nhấn nút hành động (“Mã hóa”/“Giải mã”) để xử lý.
- Xem trước kết quả.
- Nhấn “Tải kết quả” để lưu file đã mã hóa hoặc giải mã.

### 4. HTTP endpoints

#### 4.1. Mã hóa văn bản
POST /api/caesar/encrypt

#### 4.2. Giải mã văn bản
POST /api/caesar/decrypt
Request JSON:
{
  "text": "Khoor Zruog",
  "key": 3
}
Success response:
{
  "success": true,
  "result": "Hello World"
}
key phải là JSON integer; không chấp nhận boolean, float hoặc numeric string.

#### 4.3. Xử lý file
POST /api/caesar/file
Request multipart/form-data:
[TABLE]
| Field | Kiểu/giá trị | Yêu cầu |
| file | File .txt | Bắt buộc |
| key | Số nguyên có dấu | Bắt buộc |
| action | encrypt | decrypt | Bắt buộc |
| response_mode | content | file | Mặc định content |
[/TABLE]
- Mode content: trả JSON theo success response.
- Mode file: trả attachment text/plain; charset=utf-8.
- Mọi lỗi, kể cả trong mode file, đều trả JSON theo error response chuẩn.

### 5. Validation và Error Handling
Error response chuẩn:
{
  "success": false,
  "message": "Khóa phải là số nguyên."
}
Thứ tự kiểm tra khi nhiều lỗi có thể xảy ra cùng lúc:
Bước 0 – Body malformed hoặc không đọc được: trả ngay JSON chuẩn với status 422 của dòng “Body JSON không hợp lệ”. Đây là bước tiên quyết, xảy ra trước mọi kiểm tra khác.
Thứ tự 6 bước khi nhiều lỗi xảy ra cùng lúc: hiện diện trường bắt buộc (text/file → key → action) → định dạng trường vô hướng (key → action → response_mode) → đuôi file phải là .txt → dung lượng tối đa 5 MiB → file 0 byte → file phải là UTF-8.
Với luồng JSON: body đọc được → văn bản → hiện diện key → định dạng key (theo đúng thứ tự này).
Với luồng file: hiện diện trường (file → key → action) → định dạng trường (key → action → response_mode) → đuôi .txt (415) → dung lượng (413) → 0 byte (422) → UTF-8 (415).
[TABLE]
| Trường hợp | HTTP status | Thông báo |
| Thiếu hoặc rỗng text | 422 | Văn bản không được để trống. |
| Thiếu key | 422 | Thiếu khóa. |
| Key không phải số nguyên | 422 | Khóa phải là số nguyên. |
| Thiếu file | 422 | Thiếu file. |
| File 0 byte | 422 | File không được để trống. |
| File không có đuôi .txt | 415 | Chỉ chấp nhận file .txt. |
| File lớn hơn 5 MiB | 413 | File vượt quá dung lượng tối đa 5 MB. |
| File không phải UTF-8 | 415 | File phải sử dụng UTF-8. |
| Action không hợp lệ | 422 | Action phải là encrypt hoặc decrypt. |
| Response mode không hợp lệ | 422 | Response mode phải là content hoặc file. |
| Lỗi đọc file | 500 | Không thể đọc file. |
| Lỗi ngoài dự kiến | 500 | Đã xảy ra lỗi hệ thống. |
| Body JSON không hợp lệ | 422 | Dữ liệu gửi lên không hợp lệ. |
[/TABLE]

### 6. Thiết kế module
[TABLE]
| Module | Interface / trách nhiệm |
| Caesar Core | transform_text(text, key, operation); giấu toàn bộ quy tắc dịch ký tự và chuẩn hóa key. |
| File Processing | Kiểm tra tên, kích thước, encoding; đọc nội dung và tạo kết quả tải xuống. |
| HTTP Adapter | Chuyển JSON/multipart request thành lời gọi tới các module và chuyển kết quả thành HTTP response. |
| Web UI | Thu thập input, gọi HTTP endpoint, hiển thị thông báo, preview, copy và download. |
| Exception Handling | Chuyển validation/system error thành error response chuẩn và log lỗi nội bộ. |
[/TABLE]
Không tạo abstract cipher interface hoặc repository pattern trong Tuần 1. Chỉ thêm seam dùng chung khi một feature tương lai thực sự cần implementation thứ hai.

### 7. Tiêu chí nghiệm thu
- Nhập Hello World, key 3, chọn mã hóa và nhận Khoor Zruog.
- Giải mã Khoor Zruog, key 3 và nhận lại Hello World.
- Cả input bàn phím và file đều hỗ trợ mã hóa, giải mã, xem trước và tải kết quả.
- Key âm, key lớn hơn 25, ký tự hoa/thường, số, Unicode, ký tự đặc biệt và xuống dòng được xử lý đúng.
- Các trường hợp validation trả đúng HTTP status, cấu trúc và thông báo.
- File đúng 5 MiB được chấp nhận; file 5 MiB + 1 byte bị từ chối.
- Backend test đạt coverage tối thiểu 90%; Ruff check/format đạt.
- Ứng dụng chạy local và bằng Docker; truy cập được giao diện / và tài liệu /docs.

### 8. Giả định và ngoài phạm vi
- Chuỗi hoặc file chỉ chứa whitespace vẫn hợp lệ; chỉ chuỗi rỗng/null hoặc file 0 byte bị coi là rỗng.
- Ứng dụng stateless, không lưu input, file hoặc kết quả sau request.
- UI và backend cùng origin nên Tuần 1 không cần CORS.
- Không gồm database, authentication, lịch sử thao tác, React, CI/CD hoặc triển khai cloud.
- Các task của tuần tiếp theo sẽ được bổ sung theo module và phải có regression test cho chức năng Tuần 1.
Lưu ý: Caesar Cipher chỉ phục vụ mục đích học tập và minh họa thuật toán; không dùng để bảo vệ dữ liệu nhạy cảm.
