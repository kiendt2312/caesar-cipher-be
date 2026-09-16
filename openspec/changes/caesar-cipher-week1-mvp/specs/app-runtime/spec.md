## Purpose

Định nghĩa cách ứng dụng Caesar Cipher được phục vụ và vận hành ở Tuần 1: một tiến trình duy nhất phục vụ cả giao diện web lẫn API trên cùng một origin và cùng cổng, truy cập được qua `/` và `/docs`, chạy được cả ở máy local lẫn trong container với hành vi giống nhau, và không lưu lại bất kỳ dữ liệu nào của người dùng sau khi request kết thúc.

## ADDED Requirements

### Requirement: Một tiến trình duy nhất phục vụ cả giao diện lẫn API

Ứng dụng SHALL phục vụ giao diện web và toàn bộ endpoint API từ cùng một tiến trình, trên cùng một origin (cùng scheme, host và cổng). Tuần 1 MUST KHÔNG có project frontend tách riêng và MUST KHÔNG có tiến trình phục vụ giao diện riêng biệt. Vì giao diện và API cùng origin nên ứng dụng SHALL KHÔNG cần và SHALL KHÔNG cấu hình CORS ở Tuần 1: mọi lời gọi API từ giao diện đều là lời gọi cùng origin bằng đường dẫn tương đối, không phụ thuộc vào host hay cổng cụ thể. Tài nguyên tĩnh của giao diện (CSS, JS và các tài sản đi kèm) SHALL được phục vụ từ chính ứng dụng này, cùng origin với giao diện và API. (Truy vết: docx §2.2, §8)

#### Scenario: Giao diện và API dùng chung một origin

- **WHEN** người dùng mở giao diện web tại một địa chỉ bất kỳ đang phục vụ ứng dụng
- **AND** giao diện gửi request tới một endpoint API của ứng dụng
- **THEN** request đi tới cùng scheme, host và cổng với trang giao diện đang mở
- **AND** request được xử lý thành công mà không cần bất kỳ header CORS nào trong phản hồi

#### Scenario: Giao diện gọi API bằng đường dẫn tương đối

- **WHEN** ứng dụng được phục vụ ở một host hoặc cổng khác với môi trường phát triển ban đầu
- **THEN** giao diện vẫn gọi đúng các endpoint API mà không cần sửa đổi hay cấu hình lại địa chỉ backend

#### Scenario: Tài nguyên tĩnh của giao diện được phục vụ từ cùng ứng dụng

- **WHEN** trình duyệt tải trang giao diện và yêu cầu các tài nguyên tĩnh CSS/JS mà trang tham chiếu
- **THEN** các tài nguyên đó được chính ứng dụng trả về thành công
- **AND** giao diện hiển thị và hoạt động được mà không cần một máy chủ tĩnh nào khác

### Requirement: Tuyến gốc trả về giao diện web

Ứng dụng SHALL đáp ứng request tới tuyến gốc `/` bằng trang giao diện web của công cụ Caesar Cipher. Phản hồi MUST là một tài liệu HTML hiển thị được trực tiếp trên trình duyệt, không yêu cầu bước cài đặt hay mở file thủ công nào từ phía người dùng. (Truy vết: docx §2.2, §7)

#### Scenario: Mở tuyến gốc trên trình duyệt

- **WHEN** người dùng truy cập `/` trên ứng dụng đang chạy
- **THEN** ứng dụng trả về trang giao diện web của công cụ Caesar Cipher
- **AND** trang hiển thị được ngay trên trình duyệt mà không báo lỗi

### Requirement: Tuyến tài liệu API tương tác

Ứng dụng SHALL đáp ứng request tới `/docs` bằng trang tài liệu API tương tác, liệt kê các endpoint mà ứng dụng cung cấp cùng hợp đồng request và response của chúng. Trang này MUST cho phép người dùng xem và thử gọi các endpoint ngay trên trình duyệt. (Truy vết: docx §7)

#### Scenario: Mở tài liệu API

- **WHEN** người dùng truy cập `/docs` trên ứng dụng đang chạy
- **THEN** ứng dụng trả về trang tài liệu API tương tác
- **AND** trang liệt kê các endpoint Caesar Cipher mà ứng dụng cung cấp

### Requirement: Ứng dụng lắng nghe cổng 8000

Ứng dụng SHALL lắng nghe trên cổng `8000` khi chạy ở máy local và khi chạy trong container, để địa chỉ truy cập là như nhau trong cả hai môi trường. Giao diện, tài nguyên tĩnh, tài liệu API và toàn bộ endpoint API MUST cùng được phục vụ trên cổng này; Tuần 1 MUST KHÔNG dùng thêm cổng thứ hai cho bất kỳ thành phần nào. (Truy vết: docx §7)

#### Scenario: Truy cập ứng dụng chạy local qua cổng 8000

- **WHEN** ứng dụng được khởi chạy ở máy local
- **THEN** giao diện truy cập được tại `/` trên cổng `8000`
- **AND** tài liệu API truy cập được tại `/docs` trên cùng cổng `8000`

#### Scenario: Không có thành phần nào dùng cổng khác

- **WHEN** ứng dụng đang chạy và phục vụ giao diện, tài nguyên tĩnh và các endpoint API
- **THEN** tất cả đều truy cập được qua cổng `8000`
- **AND** không có thành phần nào của ứng dụng yêu cầu người dùng truy cập một cổng khác

### Requirement: Chạy được bằng Docker với hành vi giống hệt local

Ứng dụng SHALL đóng gói và chạy được bằng Docker: từ mã nguồn trong repo có thể tạo được image và khởi chạy container mà không cần thao tác chuẩn bị thủ công nào ngoài các bước đã tài liệu hóa. Container đang chạy MUST phục vụ được `/` và `/docs` trên cổng `8000`, và hành vi quan sát được của ứng dụng — kết quả mã hóa/giải mã, HTTP status, cấu trúc phản hồi và thông báo lỗi — MUST giống hệt khi chạy local với cùng đầu vào. (Truy vết: docx §7)

#### Scenario: Truy cập ứng dụng chạy trong container

- **WHEN** image được tạo từ mã nguồn trong repo và container được khởi chạy
- **THEN** giao diện truy cập được tại `/` trên cổng `8000`
- **AND** tài liệu API truy cập được tại `/docs` trên cùng cổng

#### Scenario: Kết quả giống nhau giữa container và local

- **WHEN** gửi cùng một request tới ứng dụng chạy trong container và tới ứng dụng chạy local
- **THEN** hai phản hồi có cùng HTTP status, cùng cấu trúc và cùng nội dung kết quả

### Requirement: Ứng dụng stateless, không lưu dữ liệu người dùng

Ứng dụng SHALL hoạt động stateless: sau khi một request kết thúc, ứng dụng MUST KHÔNG lưu giữ văn bản đầu vào, file tải lên hay kết quả mã hóa/giải mã ở bất kỳ nơi nào có thể truy xuất lại. Tuần 1 MUST KHÔNG có database, MUST KHÔNG có phiên làm việc (session) và MUST KHÔNG có lịch sử thao tác; ứng dụng SHALL KHÔNG cung cấp bất kỳ cách nào để đọc lại dữ liệu của một request đã hoàn tất. Mỗi request SHALL được xử lý độc lập: hai request giống hệt nhau MUST cho kết quả giống hệt nhau, và kết quả của một request MUST KHÔNG bị ảnh hưởng bởi các request trước đó hay bởi thứ tự gửi request. (Truy vết: docx §8)

#### Scenario: Hai request giống nhau cho kết quả giống nhau

- **WHEN** gửi cùng một request mã hóa hai lần liên tiếp
- **THEN** cả hai lần đều trả về cùng một kết quả và cùng HTTP status

#### Scenario: Request không bị ảnh hưởng bởi request trước đó

- **WHEN** gửi một request mã hóa với văn bản và khóa bất kỳ
- **AND** sau đó gửi một request khác với văn bản và khóa khác
- **THEN** kết quả của request sau chỉ phụ thuộc vào đầu vào của chính nó, không phụ thuộc vào request trước

#### Scenario: Không truy xuất lại được dữ liệu sau khi request kết thúc

- **WHEN** người dùng tải lên một file và nhận kết quả xử lý
- **THEN** ứng dụng không giữ lại file đã tải lên hay kết quả đó sau khi phản hồi được trả về
- **AND** không có endpoint hay màn hình nào cho phép xem lại nội dung hoặc lịch sử của thao tác đã hoàn tất
