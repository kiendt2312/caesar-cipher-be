"""JSON endpoints for encrypting and decrypting text."""

from fastapi import APIRouter

from app.api.schemas import TextCipherRequest, TextCipherResponse, validate_text_request
from app.core.caesar import transform_text

router = APIRouter(prefix="/api/caesar", tags=["text"])


@router.post("/encrypt", response_model=TextCipherResponse)
async def encrypt_text(payload: TextCipherRequest) -> TextCipherResponse:
    text, key = validate_text_request(payload)
    return TextCipherResponse(success=True, result=transform_text(text, key, "encrypt"))


@router.post("/decrypt", response_model=TextCipherResponse)
async def decrypt_text(payload: TextCipherRequest) -> TextCipherResponse:
    text, key = validate_text_request(payload)
    return TextCipherResponse(success=True, result=transform_text(text, key, "decrypt"))
