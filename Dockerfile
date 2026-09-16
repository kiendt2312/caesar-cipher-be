# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY app ./app

FROM python:3.12-slim

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --no-create-home appuser

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
