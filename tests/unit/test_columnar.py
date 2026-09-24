from __future__ import annotations

import random

import pytest

from app.core.columnar import parse_key, transform_text


def _assert_invalid_key(key: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        parse_key(key)
    assert str(exc_info.value) == "invalid columnar key"
    if key:
        assert key not in str(exc_info.value)


@pytest.mark.parametrize(
    "key",
    [
        "3 6 2 1 5 4",
        "3,6,2,1,5,4",
        "3, 6\t2\n1,5 4",
        "{3 6 2 1 5 4}",
        "{ 3, 6\t2\n1,5 4 }",
    ],
)
def test_numeric_key_accepts_approved_separators_and_outer_braces(key: str) -> None:
    assert parse_key(key) == (3, 6, 2, 1, 5, 4)


@pytest.mark.parametrize("whitespace", [" ", "\t", "\r", "\n", "\f", "\v"])
def test_key_trims_only_each_approved_ascii_whitespace_character(whitespace: str) -> None:
    assert parse_key(f"{whitespace}2 1{whitespace}") == (2, 1)
    assert parse_key(f"{whitespace}AB{whitespace}") == (1, 2)


def test_key_does_not_trim_non_ascii_whitespace() -> None:
    _assert_invalid_key("\u00a0AB\u00a0")


@pytest.mark.parametrize(
    "key",
    [
        "312",
        "+1 2",
        "-1 2",
        "1.0 2",
        "1e0 2",
        "01 2",
        "1,,2",
        ",1 2",
        "1 2,",
        "{1 2",
        "1 2}",
        "{{1 2}}",
        "{1 {2}}",
        "\u0661 2",
        "1 1",
        "1 3",
        "0 1",
        "1",
        "",
        " \t\r\n\f\v ",
    ],
)
def test_numeric_key_rejects_non_permutation_and_malformed_forms(key: str) -> None:
    _assert_invalid_key(key)


def test_numeric_key_accepts_two_and_256_columns_but_rejects_257() -> None:
    assert parse_key("2 1") == (2, 1)
    key_256 = " ".join(str(rank) for rank in range(1, 257))
    assert parse_key(key_256) == tuple(range(1, 257))
    _assert_invalid_key(" ".join(str(rank) for rank in range(1, 258)))


def test_key_length_is_measured_after_ascii_trim_at_2048_and_2049() -> None:
    assert parse_key(" " * 2049 + "2 1" + "\t" * 2049) == (2, 1)
    numeric_tail = " ".join(str(rank) for rank in range(2, 257))
    key_at_limit = "1" + " " * (2048 - len(numeric_tail) - 1) + numeric_tail
    key_over_limit = "1" + " " * (2049 - len(numeric_tail) - 1) + numeric_tail
    assert len(key_at_limit) == 2048
    assert parse_key(key_at_limit) == tuple(range(1, 257))
    assert len(key_over_limit) == 2049
    _assert_invalid_key(key_over_limit)


def test_keyword_baloon_ranking_is_stable_and_case_insensitive() -> None:
    expected = (2, 1, 3, 4, 6, 7, 5)
    assert parse_key("BALLOON") == expected
    assert parse_key("balloon") == expected
    assert parse_key("BaLlOoN") == expected


def test_keyword_duplicate_letters_tie_break_left_to_right() -> None:
    assert parse_key("AAAA") == (1, 2, 3, 4)
    assert parse_key("BABA") == (3, 1, 4, 2)


def test_keyword_accepts_two_and_256_ascii_letters_but_rejects_other_forms() -> None:
    assert parse_key("AZ") == (1, 2)
    assert parse_key("A" * 256) == tuple(range(1, 257))
    for key in ("A", "A" * 257, "AB1", "A-B", "A B", "ÉTÉ", "\uff21\uff22"):
        _assert_invalid_key(key)


@pytest.mark.parametrize(
    ("plaintext", "ranks", "ciphertext"),
    [
        ("khoacongnghethongtin", (3, 6, 2, 1, 5, 4), "agnonokntioetchghghn"),
        ("ABCDE", (3, 1, 4, 2), "BDAEC"),
        ("MEET ME AT NOON", (2, 1, 3, 4, 6, 7, 5), "EAM NETT EO NMO"),
        ("A B\r\nC!", (2, 1, 3), " \nA\r!BC"),
        ("😀A𝄞é", (2, 1, 3), "A😀é𝄞"),
        ("XY", (3, 1, 2, 4), "YX"),
    ],
)
def test_canonical_vectors_encrypt_and_decrypt_exactly(
    plaintext: str,
    ranks: tuple[int, ...],
    ciphertext: str,
) -> None:
    assert transform_text(plaintext, ranks, "encrypt") == ciphertext
    assert transform_text(ciphertext, ranks, "decrypt") == plaintext
    assert len(ciphertext) == len(plaintext)


@pytest.mark.parametrize("operation", ["encrypt", "decrypt"])
def test_empty_core_input_stays_empty(operation: str) -> None:
    assert transform_text("", (2, 1), operation) == ""


@pytest.mark.parametrize(
    "text",
    [
        "e\u0301X",
        "A\ufeffB",
        "\t \r\n",
        "👨\u200d👩\u200d👧\u200d👦",
    ],
)
def test_each_unicode_code_point_participates_without_normalization(text: str) -> None:
    ranks = (2, 1, 3)
    ciphertext = transform_text(text, ranks, "encrypt")
    assert len(ciphertext) == len(text)
    assert transform_text(ciphertext, ranks, "decrypt") == text


def test_randomized_round_trip_covers_uneven_rows_and_more_columns_than_text() -> None:
    rng = random.Random(20260924)
    alphabet = [*"Ab z!\t\r\n", "é", "\u0301", "\ufeff", "😀", "𝄞"]

    for _ in range(200):
        column_count = rng.randint(2, 16)
        ranks = list(range(1, column_count + 1))
        rng.shuffle(ranks)
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))

        ciphertext = transform_text(text, tuple(ranks), "encrypt")

        assert len(ciphertext) == len(text)
        assert transform_text(ciphertext, tuple(ranks), "decrypt") == text


def test_transform_rejects_unknown_operation_without_echoing_text() -> None:
    secret = "do-not-leak"
    with pytest.raises(ValueError) as exc_info:
        transform_text(secret, (2, 1), "rotate")
    assert str(exc_info.value) == "operation must be 'encrypt' or 'decrypt'"
    assert secret not in str(exc_info.value)
