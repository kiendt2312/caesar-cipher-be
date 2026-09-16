"""Tests for Caesar core, one test per caesar-core scenario (23 scenarios).

1  encrypt('abc', 3)            -> 'def'
2  decrypt('def', 3)            -> 'abc'
3  decrypt(encrypt(t, k), k)    == t (round-trip)
4  invalid operation rejected   -> ValueError
5  key -3 == key 23             -> 'xyz'
6  key -29 normalizes to 23     -> 'xyz'
7  key 29 normalizes to 3       -> 'def'
8  key 26 equivalent to key 0
9  key 0 keeps text unchanged
10 wrap Z->A, z->a              ('Zz' +1 -> 'Aa')
11 wrap A->Z, a->z on decrypt   ('Aa' +1 -> 'Zz')
12 'AbCdEf' +2 -> 'CdEfGh'
13 full alphabet +13 -> rot13
14 digits/punct/symbols kept
15 space, tab, LF, CRLF kept
16 Vietnamese, emoji, Unicode kept
17 length & non-letter order kept
18 whitespace-only -> verbatim
19 empty string -> empty, no error
20 'Hello World' +3 -> 'Khoor Zruog'
21 decrypt 'Khoor Zruog' +3 -> 'Hello World'
22 identical content -> identical result
23 repeated calls stable, stateless
"""

from __future__ import annotations

import pytest

from app.core.caesar import transform_text

_CHARS = "abcdefghijklmnopqrstuvwxyz"
_KEYS = (-1000, -29, -27, -26, -13, -3, -1, 0, 1, 3, 7, 13, 25, 26, 29, 52, 1000)
_DIVERSE_TEXTS = [
    "",
    "Hello World",
    "The quick brown fox jumps over the lazy dog",
    "aBcDeFgHiJkLmNoPqRsTuVwXyZ",
    "abc 123 !@#$%^&*()",
    "Xin chào Việt Nam 🎉 café",
    " \t \n \r\n ",
    "dòng một\r\ndòng hai\n\tkết thúc\r\n",
    "emoji 🎉 plus ©«»—…😀 symbols",
    "giữa văn bản có \ufeff chữ đặc biệt giữa",
]


def _reference_transform(text: str, key: int, operation: str) -> str:
    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be 'encrypt' or 'decrypt'")
    shift = (-key if operation == "decrypt" else key) % 26
    upper_base = ord("A")
    lower_base = ord("a")
    result = []
    for char in text:
        code = ord(char)
        if "A" <= char <= "Z":
            result.append(chr((code - upper_base + shift) % 26 + upper_base))
        elif "a" <= char <= "z":
            result.append(chr((code - lower_base + shift) % 26 + lower_base))
        else:
            result.append(char)
    return "".join(result)


def test_encrypts_with_valid_key() -> None:
    assert transform_text("abc", 3, "encrypt") == "def"


def test_decrypts_with_valid_key() -> None:
    assert transform_text("def", 3, "decrypt") == "abc"


def test_round_trip_encrypt_then_decrypt() -> None:
    for text in _DIVERSE_TEXTS:
        for key in _KEYS:
            ciphertext = transform_text(text, key, "encrypt")
            assert transform_text(ciphertext, key, "decrypt") == text


def test_invalid_operation_is_rejected() -> None:
    for operation in (None, "ENCRYPT", "Decrypt", "rot13", "encrypt ", 1):
        with pytest.raises(ValueError):
            transform_text("abc", 3, operation)


def test_negative_key_matches_positive_equivalent() -> None:
    assert transform_text("abc", -3, "encrypt") == transform_text("abc", 23, "encrypt")
    assert transform_text("abc", -3, "encrypt") == "xyz"


def test_negative_key_abs_greater_than_26() -> None:
    assert transform_text("abc", -29, "encrypt") == "xyz"


def test_key_greater_than_25_normalizes_down() -> None:
    assert transform_text("abc", 29, "encrypt") == "def"


def test_key_26_acts_like_key_0() -> None:
    assert transform_text("Hello World", 26, "encrypt") == "Hello World"


def test_key_0_keeps_text_identical() -> None:
    assert transform_text("Hello World", 0, "encrypt") == "Hello World"
    assert transform_text("Hello World", 0, "decrypt") == "Hello World"


def test_wrap_at_end_of_alphabet() -> None:
    assert transform_text("Zz", 1, "encrypt") == "Aa"


def test_wrap_at_start_of_alphabet_when_decrypting() -> None:
    assert transform_text("Aa", 1, "decrypt") == "Zz"


def test_preserves_letter_case_per_character() -> None:
    assert transform_text("AbCdEf", 2, "encrypt") == "CdEfGh"


def test_full_alphabet_shifts_correctly() -> None:
    assert transform_text(_CHARS, 13, "encrypt") == "nopqrstuvwxyzabcdefghijklm"


def test_keeps_digits_punctuation_and_symbols() -> None:
    assert transform_text("abc 123 !@#$%^&*()", 3, "encrypt") == "def 123 !@#$%^&*()"


def test_keeps_whitespace_tab_lf_and_crlf() -> None:
    text = "a \tb\nc\r\nd"
    result = transform_text(text, 3, "encrypt")
    assert result == "d \te\nf\r\ng"
    assert result.count("\r\n") == text.count("\r\n")


def test_keeps_vietnamese_emoji_and_unicode() -> None:
    assert transform_text("Xin chào Việt Nam 🎉 café", 5, "encrypt") == "Cns hmàt Anệy Sfr 🎉 hfké"


def test_length_and_character_order_are_stable() -> None:
    text = "Zz! 🎉Xin-chào\nA1b\t"
    result = transform_text(text, 7, "encrypt")
    assert len(result) == len(text)
    for index, char in enumerate(text):
        if not ("a" <= char <= "z" or "A" <= char <= "Z"):
            assert result[index] == char


def test_whitespace_only_returned_verbatim() -> None:
    text = " \t\n\r\n  "
    assert transform_text(text, 7, "encrypt") == text
    assert transform_text(text, 7, "decrypt") == text


@pytest.mark.parametrize("key", _KEYS)
def test_empty_text_processed_without_error(key: int) -> None:
    assert transform_text("", key, "encrypt") == ""
    assert transform_text("", key, "decrypt") == ""


def test_acceptance_hello_world_encrypts() -> None:
    assert transform_text("Hello World", 3, "encrypt") == "Khoor Zruog"


def test_acceptance_khoor_zruog_decrypts() -> None:
    assert transform_text("Khoor Zruog", 3, "decrypt") == "Hello World"


def test_identical_content_yields_identical_result() -> None:
    keyboard_input = "Xin chào World 🎉"
    file_input = "Xin chào World 🎉"
    assert transform_text(keyboard_input, 6, "encrypt") == transform_text(file_input, 6, "encrypt")


def test_repeated_calls_are_stable_and_stateless() -> None:
    first = transform_text("Hello World", 3, "encrypt")
    assert first == "Khoor Zruog"
    for _ in range(5):
        assert transform_text("Hello World", 3, "encrypt") == first
    transform_text("aaa", 13, "encrypt")
    assert transform_text("Hello World", 3, "encrypt") == first


def test_reference_loop_equivalence_over_diverse_inputs() -> None:
    for text in _DIVERSE_TEXTS:
        for key in _KEYS:
            for operation in ("encrypt", "decrypt"):
                assert transform_text(text, key, operation) == _reference_transform(
                    text, key, operation
                )
