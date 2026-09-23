"""Application assembly for the Caesar Cipher service and same-origin UI."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.api.request_size_guard import MultipartCompletionGuard, RequestSizeGuard
from app.api.routes_additional_file import playfair_file_router, vigenere_file_router
from app.api.routes_additional_text import playfair_router, vigenere_router
from app.api.routes_affine_file import router as affine_file_router
from app.api.routes_affine_text import router as affine_text_router
from app.api.routes_file import router as file_router
from app.api.routes_text import router as text_router
from app.errors import messages
from app.errors.handlers import register_exception_handlers

app = FastAPI()
app.add_middleware(RequestSizeGuard, max_bytes=config.MAX_REQUEST_BYTES)
app.add_middleware(MultipartCompletionGuard)
register_exception_handlers(app)
app.include_router(text_router)
app.include_router(file_router)
app.include_router(vigenere_router)
app.include_router(playfair_router)
app.include_router(affine_text_router)
app.include_router(affine_file_router)
app.include_router(vigenere_file_router)
app.include_router(playfair_file_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "max_file_bytes": config.MAX_FILE_BYTES,
            "ui_messages": {
                "file_type": messages.UNSUPPORTED_FILE_TYPE,
                "file_size": messages.FILE_TOO_LARGE,
                "file_empty": messages.EMPTY_FILE,
                "key_missing": messages.MISSING_KEY,
                "key_invalid": messages.INVALID_KEY,
                "system": messages.UNEXPECTED_FAILURE,
            },
        },
    )
