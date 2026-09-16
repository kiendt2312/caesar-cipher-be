import string
from typing import Literal

Operation = Literal["encrypt", "decrypt"]

_UP = string.ascii_uppercase
_LO = string.ascii_lowercase
_TABLES = [str.maketrans(_UP + _LO, _UP[k:] + _UP[:k] + _LO[k:] + _LO[:k]) for k in range(26)]


def transform_text(text: str, key: int, operation: Operation) -> str:
    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be 'encrypt' or 'decrypt'")
    table = _TABLES[key % 26] if operation == "encrypt" else _TABLES[(-key) % 26]
    return text.translate(table)
