"""Unit acceptance tests for the transport-independent Affine cipher core."""

import pytest

from app.core.affine import modular_inverse, normalize_keys, transform_text

VALID_MULTIPLIER_RESIDUES = (1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25)


def test_normalized_affine_key_space_has_exactly_312_pairs() -> None:
    pairs = {
        normalize_keys(multiplier, shift)
        for multiplier in VALID_MULTIPLIER_RESIDUES
        for shift in range(26)
    }

    assert {multiplier for multiplier, _ in pairs} == set(VALID_MULTIPLIER_RESIDUES)
    assert {shift for _, shift in pairs} == set(range(26))
    assert len(pairs) == 312


@pytest.mark.parametrize("multiplier", [0, 2, 13, 26])
def test_noninvertible_multiplier_is_rejected_without_repair(multiplier: int) -> None:
    with pytest.raises(ValueError, match="invertible"):
        normalize_keys(multiplier, 8)


def test_negative_and_large_keys_normalize_to_the_same_pair() -> None:
    assert normalize_keys(-21, -18) == (5, 8)
    assert normalize_keys(57, 60) == (5, 8)


@pytest.mark.parametrize("multiplier", VALID_MULTIPLIER_RESIDUES)
def test_modular_inverse_exists_for_every_valid_multiplier(multiplier: int) -> None:
    inverse = modular_inverse(multiplier)

    assert 0 <= inverse < 26
    assert multiplier * inverse % 26 == 1


def test_canonical_affine_vector_encrypts_and_decrypts() -> None:
    assert transform_text("HELLO", 5, 8, "encrypt") == "RCLLA"
    assert transform_text("RCLLA", 5, 8, "decrypt") == "HELLO"


def test_mixed_case_wraparound_unicode_and_whitespace_are_preserved() -> None:
    assert transform_text("Zz Aa", 5, 8, "encrypt") == "Dd Ii"
    assert transform_text("Hé🙂z!\t\r\n", 5, 8, "encrypt") == "Ré🙂d!\t\r\n"
    assert transform_text(" \t\r\n", 5, 8, "encrypt") == " \t\r\n"


def test_every_normalized_key_pair_round_trips_losslessly() -> None:
    text = "Hello, Việt Nam 🙂\r\n123!"

    for multiplier in VALID_MULTIPLIER_RESIDUES:
        for shift in range(26):
            encrypted = transform_text(text, multiplier, shift, "encrypt")
            assert transform_text(encrypted, multiplier, shift, "decrypt") == text


def test_equivalent_integer_keys_produce_the_same_result() -> None:
    expected = transform_text("Affine Zz", 5, 8, "encrypt")

    assert transform_text("Affine Zz", -21, -18, "encrypt") == expected
    assert transform_text("Affine Zz", 57, 60, "encrypt") == expected


def test_unknown_operation_is_rejected() -> None:
    with pytest.raises(ValueError, match="operation"):
        transform_text("HELLO", 5, 8, "rotate")  # type: ignore[arg-type]
