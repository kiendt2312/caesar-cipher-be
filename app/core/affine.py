"""Pure Affine cipher transformations over ASCII letters modulo 26."""

from __future__ import annotations

from math import gcd
from typing import Literal

Operation = Literal["encrypt", "decrypt"]
MODULUS = 26


def normalize_keys(multiplier: int, shift: int) -> tuple[int, int]:
    """Normalize an Affine key pair and reject a non-invertible multiplier."""

    normalized_multiplier = multiplier % MODULUS
    normalized_shift = shift % MODULUS
    if gcd(normalized_multiplier, MODULUS) != 1:
        raise ValueError("multiplier must be invertible modulo 26")
    return normalized_multiplier, normalized_shift


def modular_inverse(multiplier: int) -> int:
    """Return the positive inverse of an invertible multiplier modulo 26."""

    normalized_multiplier, _ = normalize_keys(multiplier, 0)
    for candidate in range(1, MODULUS):
        if normalized_multiplier * candidate % MODULUS == 1:
            return candidate
    raise ValueError("multiplier must be invertible modulo 26")


def transform_text(text: str, multiplier: int, shift: int, operation: Operation) -> str:
    """Encrypt or decrypt ASCII letters while preserving all other code points."""

    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be 'encrypt' or 'decrypt'")

    normalized_multiplier, normalized_shift = normalize_keys(multiplier, shift)
    inverse = modular_inverse(normalized_multiplier) if operation == "decrypt" else None
    result: list[str] = []

    for char in text:
        if "A" <= char <= "Z":
            base = ord("A")
        elif "a" <= char <= "z":
            base = ord("a")
        else:
            result.append(char)
            continue

        value = ord(char) - base
        if operation == "encrypt":
            transformed = normalized_multiplier * value + normalized_shift
        else:
            assert inverse is not None
            transformed = inverse * (value - normalized_shift)
        result.append(chr(transformed % MODULUS + base))

    return "".join(result)
