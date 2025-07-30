# syntax=docker/dockerfile:1

# ------------- Build stage -------------
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies (cached)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy source and install the project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ------------- Runtime stage -------------
FROM python:3.12-alpine

# Install minimal FFmpeg for audio processing
RUN apk add --no-cache ffmpeg

# Create unprivileged user
RUN addgroup -g 1001 worker && adduser -D -u 1001 -G worker worker

# Copy the entire app directory from builder
COPY --from=builder --chown=worker:worker /app /app

WORKDIR /app
USER worker
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "app.run_worker"]
