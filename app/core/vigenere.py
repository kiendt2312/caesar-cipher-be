"""Pure repeating-key Vigenere transformations over ASCII letters."""

from __future__ import annotations

from typing import Literal

Operation = Literal["encrypt", "decrypt"]


def normalize_key(key: str) -> str:
    """Return an uppercase ASCII key or reject the unsupported key grammar."""

    if not key or any(not ("A" <= char <= "Z" or "a" <= char <= "z") for char in key):
        raise ValueError("key must contain ASCII letters only")
    return "".join(chr(ord(char) - 32) if "a" <= char <= "z" else char for char in key)


def transform_text(text: str, key: str, operation: Operation) -> str:
    """Encrypt or decrypt text while preserving non-ASCII-letter characters."""

    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be 'encrypt' or 'decrypt'")

    normalized_key = normalize_key(key)
    direction = 1 if operation == "encrypt" else -1
    key_index = 0
    result: list[str] = []

    for char in text:
        if "A" <= char <= "Z":
            base = ord("A")
        elif "a" <= char <= "z":
            base = ord("a")
        else:
            result.append(char)
            continue

        shift = ord(normalized_key[key_index % len(normalized_key)]) - ord("A")
        result.append(chr((ord(char) - base + direction * shift) % 26 + base))
        key_index += 1

    return "".join(result)
