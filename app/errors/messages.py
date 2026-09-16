"""Canonical user-facing error messages.

This module is the single source of truth for the error strings shared by the
application's exception classes and HTTP adapters.
"""

TEXT_EMPTY = "Văn bản không được để trống."
MISSING_KEY = "Thiếu khóa."
INVALID_KEY = "Khóa phải là số nguyên."
MISSING_FILE = "Thiếu file."
EMPTY_FILE = "File không được để trống."
UNSUPPORTED_FILE_TYPE = "Chỉ chấp nhận file .txt."
FILE_TOO_LARGE = "File vượt quá dung lượng tối đa 5 MB."
UNSUPPORTED_ENCODING = "File phải sử dụng UTF-8."
INVALID_ACTION = "Action phải là encrypt hoặc decrypt."
INVALID_RESPONSE_MODE = "Response mode phải là content hoặc file."
FILE_READ_FAILURE = "Không thể đọc file."
UNEXPECTED_FAILURE = "Đã xảy ra lỗi hệ thống."
INVALID_REQUEST_BODY = "Dữ liệu gửi lên không hợp lệ."

# Owner-approved infrastructure exception; not a canonical DOCX §5 business message.
REQUEST_TOO_LARGE = "Yêu cầu vượt quá dung lượng cho phép."

CANONICAL_MESSAGES = (
    TEXT_EMPTY,
    MISSING_KEY,
    INVALID_KEY,
    MISSING_FILE,
    EMPTY_FILE,
    UNSUPPORTED_FILE_TYPE,
    FILE_TOO_LARGE,
    UNSUPPORTED_ENCODING,
    INVALID_ACTION,
    INVALID_RESPONSE_MODE,
    FILE_READ_FAILURE,
    UNEXPECTED_FAILURE,
    INVALID_REQUEST_BODY,
)
