"""Unit coverage for the framework-independent file-processing seam."""

from __future__ import annotations

import asyncio
from io import BytesIO

import pytest

from app import config
from app.errors.exceptions import FileReadError, FileTooLargeError, UnsupportedEncodingError
from app.services.file_processing import (
    UTF8_BOM,
    build_attachment_body,
    build_content_disposition,
    build_result_filename,
    decode_file_bytes,
    has_allowed_extension,
    read_limited_bytes,
)


class AsyncBytesReader:
    """Small async adapter around BytesIO, matching the service's reader protocol."""

    def __init__(self, payload: bytes) -> None:
        self._stream = BytesIO(payload)
        self.read_sizes: list[int] = []

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self._stream.read(size)


class FailingReader:
    async def read(self, size: int) -> bytes:
        del size
        raise OSError("simulated read failure")


class NonBytesReader:
    async def read(self, size: int) -> str:
        del size
        return "not bytes"


def _read(reader: object) -> bytes:
    return asyncio.run(read_limited_bytes(reader))


# Scenario 5.1: an exact-limit bytes stream is accepted and read in fixed-size chunks.
def test_read_limited_bytes_accepts_exact_limit_and_uses_chunk_size(
    exact_limit_bytes: bytes,
) -> None:
    reader = AsyncBytesReader(exact_limit_bytes)

    assert _read(reader) == exact_limit_bytes
    assert reader.read_sizes
    assert all(size == config.CHUNK_SIZE for size in reader.read_sizes)


# Scenario 5.1: the first byte over the limit stops the reader without consuming more data.
def test_read_limited_bytes_rejects_first_byte_over_limit(over_limit_bytes: bytes) -> None:
    reader = AsyncBytesReader(over_limit_bytes)

    with pytest.raises(FileTooLargeError):
        _read(reader)

    assert all(size == config.CHUNK_SIZE for size in reader.read_sizes)
    assert len(reader.read_sizes) == config.MAX_FILE_BYTES // config.CHUNK_SIZE + 1


# Scenario 5.1 / file-cipher-api 37: technical reader failures use the canonical application error.
def test_read_limited_bytes_wraps_reader_failures() -> None:
    with pytest.raises(FileReadError):
        _read(FailingReader())


def test_read_limited_bytes_wraps_non_bytes_reader_output() -> None:
    with pytest.raises(FileReadError):
        _read(NonBytesReader())


# Scenario 5.3: a UTF-8 code point split across chunks is decoded only after buffering completes.
def test_decode_file_bytes_handles_code_point_crossing_chunk_boundary() -> None:
    raw = b"A" * (config.CHUNK_SIZE - 1) + "é".encode()

    text, had_bom = decode_file_bytes(raw)

    assert text.endswith("é")
    assert not had_bom


# Scenario 5.2: utf-8-sig removes only an input BOM and records its presence.
def test_decode_file_bytes_detects_and_strips_leading_bom() -> None:
    text, had_bom = decode_file_bytes(UTF8_BOM + b"Hello")

    assert text == "Hello"
    assert had_bom


# Scenario 5.3: invalid bytes are mapped to the canonical unsupported-encoding error.
def test_decode_file_bytes_rejects_invalid_utf8() -> None:
    with pytest.raises(UnsupportedEncodingError):
        decode_file_bytes(b"latin-1: \xff")


# Scenario 5.2 / 5.3: all BOM-by-newline combinations round-trip their bytes.
@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_bom"),
    [
        pytest.param(b"a\nb", "a\nb", False, id="no-bom-lf"),
        pytest.param(UTF8_BOM + b"a\nb", "a\nb", True, id="bom-lf"),
        pytest.param(b"a\r\nb", "a\r\nb", False, id="no-bom-crlf"),
        pytest.param(UTF8_BOM + b"a\r\nb", "a\r\nb", True, id="bom-crlf"),
    ],
)
def test_bom_and_newline_variants_preserve_bytes(
    raw: bytes,
    expected_text: str,
    expected_bom: bool,
) -> None:
    text, had_bom = decode_file_bytes(raw)

    assert text == expected_text
    assert had_bom is expected_bom
    assert build_attachment_body(text, had_bom) == raw


# Scenario 5.2: attachment bytes preserve BOM state, while the content result has no BOM.
@pytest.mark.parametrize(
    ("had_bom", "expected"),
    [
        pytest.param(True, UTF8_BOM + b"Khoor", id="input-had-bom"),
        pytest.param(False, b"Khoor", id="input-no-bom"),
    ],
)
def test_build_attachment_body_preserves_input_bom_state(had_bom: bool, expected: bytes) -> None:
    assert build_attachment_body("Khoor", had_bom) == expected


# Scenario 5.4: output names remove only the final case-insensitive .txt suffix.
@pytest.mark.parametrize(
    ("original", "action", "expected"),
    [
        pytest.param("ghi-chu.txt", "encrypt", "ghi-chu.encrypted.txt", id="encrypt"),
        pytest.param("ghi-chu.txt", "decrypt", "ghi-chu.decrypted.txt", id="decrypt"),
        pytest.param("BaoCao.TXT", "encrypt", "BaoCao.encrypted.txt", id="uppercase-extension"),
        pytest.param(
            "bao.cao.v2.txt",
            "encrypt",
            "bao.cao.v2.encrypted.txt",
            id="multiple-dots",
        ),
    ],
)
def test_result_name_uses_dot_suffix_and_preserves_the_original_stem(
    original: str, action: str, expected: str
) -> None:
    assert build_result_filename(original, action) == expected


def test_unknown_action_cannot_produce_a_result_filename() -> None:
    with pytest.raises(ValueError):
        build_result_filename("input.txt", "rotate")


# Scenarios 5.4 and 6.2: only a final .txt extension is accepted, case-insensitively.
@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        pytest.param("a.txt", True, id="lowercase"),
        pytest.param("a.TXT", True, id="uppercase"),
        pytest.param("a.Txt", True, id="mixed-case"),
        pytest.param("a.md", False, id="wrong-extension"),
        pytest.param("a.txt.exe", False, id="double-extension"),
        pytest.param("readme", False, id="no-extension"),
        pytest.param(None, False, id="missing-name"),
    ],
)
def test_only_a_final_txt_extension_is_accepted_case_insensitively(
    filename: str, expected: bool
) -> None:
    assert has_allowed_extension(filename) is expected


# Attachment metadata must remain safe for quotes, path separators, controls, and Unicode names.
def test_build_content_disposition_quotes_and_sanitizes_filename() -> None:
    quoted = build_content_disposition('report"final.encrypted.txt')
    injected = build_content_disposition("../report\r\nX-Injected: yes.encrypted.txt")

    assert quoted == 'attachment; filename="report\\"final.encrypted.txt"'
    assert "\r" not in injected and "\n" not in injected
    assert "../" not in injected
    assert 'filename="' in injected


def test_build_content_disposition_supports_unicode_filename_safely() -> None:
    header = build_content_disposition("báo-cáo.encrypted.txt")

    assert 'filename="bao-cao.encrypted.txt"' in header
    assert "filename*=UTF-8''b%C3%A1o-c%C3%A1o.encrypted.txt" in header
