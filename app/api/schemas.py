"""Request and response schemas for the text and file cipher endpoints."""

from __future__ import annotations

import re
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.errors.exceptions import (
    EmptyTextError,
    InvalidActionError,
    InvalidKeyError,
    InvalidResponseModeError,
    MissingKeyError,
)

MISSING: Final = object()
MULTIPART_KEY_MAX_LENGTH = 32
_MULTIPART_KEY_PATTERN = re.compile(r"^[+-]?[0-9]+$")


class TextCipherRequest(BaseModel):
    """Raw JSON fields retained for deterministic, application-level validation."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"required": ["text", "key"]},
    )

    text: Any = Field(default_factory=lambda: MISSING, json_schema_extra={"type": "string"})
    key: Any = Field(default_factory=lambda: MISSING, json_schema_extra={"type": "integer"})


class TextCipherResponse(BaseModel):
    """The exact success envelope returned by both text endpoints."""

    success: Literal[True]
    result: str


class FileCipherResponse(BaseModel):
    """The exact success envelope for the file endpoint's content mode."""

    success: Literal[True]
    result: str


def parse_key(value: Any) -> int:
    """Validate a key value decoded from a JSON request body."""

    if value is MISSING or value is None or (type(value) is str and value == ""):
        raise MissingKeyError()
    if type(value) is not int:
        raise InvalidKeyError()
    return value


def parse_multipart_key(value: Any) -> int:
    """Parse the explicitly supported decimal grammar used by multipart forms."""

    if value is MISSING or value is None:
        raise MissingKeyError()
    if type(value) is not str:
        raise InvalidKeyError()

    stripped = value.strip()
    if stripped == "":
        raise MissingKeyError()
    if len(stripped) > MULTIPART_KEY_MAX_LENGTH:
        raise InvalidKeyError()
    if _MULTIPART_KEY_PATTERN.fullmatch(stripped) is None:
        raise InvalidKeyError()

    try:
        return int(stripped)
    except (OverflowError, ValueError) as exc:
        raise InvalidKeyError() from exc


def validate_file_form_fields(
    key: Any,
    action: Any,
    response_mode: Any,
) -> tuple[int, str, str]:
    """Validate multipart scalar fields in the approved deterministic order."""

    if key is MISSING or key is None or (type(key) is str and key.strip() == ""):
        raise MissingKeyError()
    if action is MISSING or action is None:
        raise InvalidActionError()

    parsed_key = parse_multipart_key(key)
    if action not in ("encrypt", "decrypt"):
        raise InvalidActionError()

    if response_mode is MISSING or response_mode is None:
        parsed_response_mode = "content"
    elif response_mode not in ("content", "file"):
        raise InvalidResponseModeError()
    else:
        parsed_response_mode = response_mode

    return parsed_key, action, parsed_response_mode


def validate_text_request(payload: TextCipherRequest) -> tuple[str, int]:
    """Apply text validation before key presence and key type validation."""

    if payload.text is MISSING or type(payload.text) is not str or payload.text == "":
        raise EmptyTextError()
    return payload.text, parse_key(payload.key)
