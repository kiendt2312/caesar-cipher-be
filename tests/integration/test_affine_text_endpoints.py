"""Integration contract for the strict Affine JSON endpoints."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.errors import messages
from app.main import app

ENCRYPT_PATH = "/api/affine/encrypt"
DECRYPT_PATH = "/api/affine/decrypt"
AFFINE_TEXT_PATHS = (ENCRYPT_PATH, DECRYPT_PATH)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_success(response, expected: str) -> None:
    assert response.status_code == 200
    assert response.json() == {"success": True, "result": expected}
    assert set(response.json()) == {"success", "result"}


def _assert_error(response, message: str, status: int = 422) -> None:
    assert response.status_code == status
    assert response.json() == {"success": False, "message": message}
    assert set(response.json()) == {"success", "message"}


@pytest.mark.parametrize(
    ("path", "payload", "expected"),
    [
        (ENCRYPT_PATH, {"text": "HELLO", "a": 5, "b": 8}, "RCLLA"),
        (DECRYPT_PATH, {"text": "RCLLA", "a": 5, "b": 8}, "HELLO"),
        (ENCRYPT_PATH, {"text": "Zz Aa", "a": 5, "b": 8}, "Dd Ii"),
        (ENCRYPT_PATH, {"text": "Hé🙂z!", "a": 5, "b": 8}, "Ré🙂d!"),
        (ENCRYPT_PATH, {"text": " \t\r\n", "a": 5, "b": 8}, " \t\r\n"),
        (ENCRYPT_PATH, {"text": "HELLO", "a": -21, "b": -18}, "RCLLA"),
        (ENCRYPT_PATH, {"text": "HELLO", "a": 57, "b": 60}, "RCLLA"),
        (
            ENCRYPT_PATH,
            {"text": "HELLO", "a": 9007199254741017, "b": 9007199254740994},
            "RCLLA",
        ),
    ],
)
def test_affine_text_success_contract(
    client: TestClient,
    path: str,
    payload: dict[str, object],
    expected: str,
) -> None:
    _assert_success(client.post(path, json=payload), expected)


def test_affine_text_round_trip_is_lossless(client: TestClient) -> None:
    original = "Hello, Việt Nam 🙂\r\n123!"
    encrypted = client.post(ENCRYPT_PATH, json={"text": original, "a": 5, "b": 8})
    decrypted = client.post(
        DECRYPT_PATH,
        json={"text": encrypted.json()["result"], "a": 5, "b": 8},
    )

    _assert_success(decrypted, original)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": b"not-json", "headers": {"content-type": "application/json"}},
        {"content": b"[]", "headers": {"content-type": "application/json"}},
        {
            "content": b'{"text":"HELLO","a":5,"b":8,"x":1}',
            "headers": {"content-type": "application/json"},
        },
        {
            "content": b'{"text":"HELLO","a":5,"a":7,"b":8}',
            "headers": {"content-type": "application/json"},
        },
        {"content": b'{"text":"HELLO","a":5,"b":8}', "headers": {"content-type": "text/plain"}},
    ],
)
@pytest.mark.parametrize("path", AFFINE_TEXT_PATHS)
def test_affine_text_rejects_invalid_body_framing(
    client: TestClient,
    path: str,
    kwargs: dict[str, object],
) -> None:
    _assert_error(client.post(path, **kwargs), messages.INVALID_REQUEST_BODY)


@pytest.mark.parametrize("path", AFFINE_TEXT_PATHS)
@pytest.mark.parametrize("text", [None, "", 123, [], {}])
def test_affine_text_field_precedes_key_validation(
    client: TestClient,
    path: str,
    text: object,
) -> None:
    _assert_error(
        client.post(path, json={"text": text, "a": 2}),
        messages.TEXT_EMPTY,
    )


@pytest.mark.parametrize("value", ["5", 5.0, True, False, [], {}, ""])
def test_affine_multiplier_rejects_non_integer_json_types(
    client: TestClient,
    value: object,
) -> None:
    _assert_error(
        client.post(ENCRYPT_PATH, json={"text": "HELLO", "a": value, "b": 8}),
        messages.INVALID_AFFINE_MULTIPLIER,
    )


@pytest.mark.parametrize(
    "payload",
    [{"text": "HELLO", "b": 8}, {"text": "HELLO", "a": None, "b": 8}],
)
def test_affine_multiplier_is_required_without_default(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    _assert_error(client.post(ENCRYPT_PATH, json=payload), messages.MISSING_AFFINE_MULTIPLIER)


@pytest.mark.parametrize("multiplier", [0, 2, 13, 26])
def test_affine_multiplier_must_be_invertible(client: TestClient, multiplier: int) -> None:
    _assert_error(
        client.post(ENCRYPT_PATH, json={"text": "HELLO", "a": multiplier}),
        messages.NON_INVERTIBLE_AFFINE_MULTIPLIER,
    )


@pytest.mark.parametrize("value", ["8", 8.0, True, False, [], {}, ""])
def test_affine_shift_rejects_non_integer_json_types(client: TestClient, value: object) -> None:
    _assert_error(
        client.post(ENCRYPT_PATH, json={"text": "HELLO", "a": 5, "b": value}),
        messages.INVALID_AFFINE_SHIFT,
    )


@pytest.mark.parametrize(
    "payload",
    [{"text": "HELLO", "a": 5}, {"text": "HELLO", "a": 5, "b": None}],
)
def test_affine_shift_is_required_without_default(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    _assert_error(client.post(ENCRYPT_PATH, json=payload), messages.MISSING_AFFINE_SHIFT)


def test_affine_accepts_an_integer_token_beyond_runtime_conversion_limit(
    client: TestClient,
) -> None:
    multiplier = b"26" + b"0" * 5000 + b"5"
    shift = b"26" + b"0" * 5000 + b"8"
    body = b'{"text":"HELLO","a":' + multiplier + b',"b":' + shift + b"}"

    _assert_success(
        client.post(ENCRYPT_PATH, content=body, headers={"content-type": "application/json"}),
        "RCLLA",
    )


def test_affine_text_routes_raise_only_the_highest_priority_error(client: TestClient) -> None:
    _assert_error(
        client.post(ENCRYPT_PATH, json={"a": 2, "b": "bad"}),
        messages.TEXT_EMPTY,
    )
    _assert_error(
        client.post(ENCRYPT_PATH, json={"text": "", "a": 2}),
        messages.TEXT_EMPTY,
    )
    _assert_error(
        client.post(ENCRYPT_PATH, json={"text": "HELLO", "a": 2, "b": "bad"}),
        messages.NON_INVERTIBLE_AFFINE_MULTIPLIER,
    )


def test_affine_text_openapi_is_exact(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    for path in AFFINE_TEXT_PATHS:
        operation = schema["paths"][path]["post"]
        request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert request_schema["required"] == ["text", "a", "b"]
        assert request_schema["additionalProperties"] is False
        assert request_schema["properties"] == {
            "text": {"type": "string", "title": "Text"},
            "a": {"type": "integer", "title": "A"},
            "b": {"type": "integer", "title": "B"},
        }
        assert all("default" not in item for item in request_schema["properties"].values())
        assert set(operation["responses"]) == {"200", "413", "422", "500"}
        for status in ("413", "422", "500"):
            error_schema = operation["responses"][status]["content"]["application/json"]["schema"]
            assert set(error_schema["required"]) == {"success", "message"}
            assert set(error_schema["properties"]) == {"success", "message"}


def test_affine_route_inventory_has_only_the_three_explicit_paths(client: TestClient) -> None:
    paths = {
        path
        for path, operations in client.get("/openapi.json").json()["paths"].items()
        if path.startswith("/api/affine") and "post" in operations
    }

    assert paths == {ENCRYPT_PATH, DECRYPT_PATH, "/api/affine/file"}


def test_existing_text_routes_keep_accepting_additional_members(client: TestClient) -> None:
    _assert_success(
        client.post(
            "/api/caesar/encrypt",
            json={"text": "abc", "key": 1, "existing_behavior": True},
        ),
        "bcd",
    )
    _assert_success(
        client.post(
            "/api/vigenere/encrypt",
            json={"text": "AAA", "key": "B", "existing_behavior": True},
        ),
        "BBB",
    )
