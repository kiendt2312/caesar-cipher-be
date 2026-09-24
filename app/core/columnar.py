"""Pure Columnar Transposition key parsing and text transformation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

ASCII_WHITESPACE = " \t\r\n\f\v"
MIN_COLUMNS = 2
MAX_COLUMNS = 256
MAX_KEY_CHARS = 2048

_INVALID_KEY_MESSAGE = "invalid columnar key"
_ASCII_KEYWORD_PATTERN = re.compile(r"[A-Za-z]+")
_NUMERIC_BODY_PATTERN = re.compile(
    r"[0-9]+(?:(?:[ \t\r\n\f\v]+|[ \t\r\n\f\v]*,[ \t\r\n\f\v]*)[0-9]+)*"
)
_NUMERIC_TOKEN_PATTERN = re.compile(r"[0-9]+")


def _invalid_key() -> ValueError:
    return ValueError(_INVALID_KEY_MESSAGE)


def _numeric_body(key: str) -> str | None:
    """Return the body of a syntactically numeric key, or ``None`` otherwise."""

    if "{" in key or "}" in key:
        if not (key.startswith("{") and key.endswith("}")):
            return None
        body = key[1:-1]
        if "{" in body or "}" in body:
            return None
        body = body.strip(ASCII_WHITESPACE)
    else:
        body = key

    if _NUMERIC_BODY_PATTERN.fullmatch(body) is None:
        return None
    return body


def _parse_numeric_key(key: str) -> tuple[int, ...] | None:
    body = _numeric_body(key)
    if body is None:
        return None

    tokens = _NUMERIC_TOKEN_PATTERN.findall(body)
    if any(len(token) > 1 and token.startswith("0") for token in tokens):
        raise _invalid_key()
    if not MIN_COLUMNS <= len(tokens) <= MAX_COLUMNS:
        raise _invalid_key()

    ranks: list[int] = []
    for token in tokens:
        if len(token) > 3:
            raise _invalid_key()
        rank = int(token)
        if not 1 <= rank <= len(tokens):
            raise _invalid_key()
        ranks.append(rank)

    if len(set(ranks)) != len(ranks):
        raise _invalid_key()
    return tuple(ranks)


def _rank_keyword(keyword: str) -> tuple[int, ...]:
    if not MIN_COLUMNS <= len(keyword) <= MAX_COLUMNS:
        raise _invalid_key()

    physical_columns = sorted(
        range(len(keyword)),
        key=lambda index: (keyword[index].upper(), index),
    )
    ranks = [0] * len(keyword)
    for rank, column in enumerate(physical_columns, start=1):
        ranks[column] = rank
    return tuple(ranks)


def parse_key(key: str) -> tuple[int, ...]:
    """Parse one approved numeric permutation or ASCII keyword into column ranks."""

    if type(key) is not str:
        raise _invalid_key()

    stripped = key.strip(ASCII_WHITESPACE)
    if not stripped or len(stripped) > MAX_KEY_CHARS:
        raise _invalid_key()

    numeric_ranks = _parse_numeric_key(stripped)
    if numeric_ranks is not None:
        return numeric_ranks

    if _ASCII_KEYWORD_PATTERN.fullmatch(stripped) is None:
        raise _invalid_key()
    return _rank_keyword(stripped)


def _rank_to_column(ranks: Sequence[int]) -> tuple[int, ...]:
    rank_tuple = tuple(ranks)
    column_count = len(rank_tuple)
    if not MIN_COLUMNS <= column_count <= MAX_COLUMNS:
        raise ValueError("invalid columnar ranks")
    if sorted(rank_tuple) != list(range(1, column_count + 1)):
        raise ValueError("invalid columnar ranks")

    columns = [0] * column_count
    for column, rank in enumerate(rank_tuple):
        columns[rank - 1] = column
    return tuple(columns)


def transform_text(
    text: str,
    ranks: Sequence[int],
    operation: Literal["encrypt", "decrypt"],
) -> str:
    """Encrypt or decrypt text by transposing Python Unicode code points."""

    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be 'encrypt' or 'decrypt'")

    columns_by_rank = _rank_to_column(ranks)
    column_count = len(columns_by_rank)

    if operation == "encrypt":
        return "".join(text[column::column_count] for column in columns_by_rank)

    complete_rows, extra_columns = divmod(len(text), column_count)
    column_lengths = [complete_rows + (column < extra_columns) for column in range(column_count)]
    columns = [""] * column_count
    offset = 0
    for column in columns_by_rank:
        next_offset = offset + column_lengths[column]
        columns[column] = text[offset:next_offset]
        offset = next_offset

    row_count = complete_rows + bool(extra_columns)
    return "".join(
        columns[column][row]
        for row in range(row_count)
        for column in range(column_count)
        if row < len(columns[column])
    )
