# syntax=docker/dockerfile:1
# matcher-service image: dependencies resolved from uv.lock, non-root, no build tools at runtime.

FROM ghcr.io/astral-sh/uv:0.13.1 AS uv

FROM python:3.12.15-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependencies first, so this layer is cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12.15-slim AS runtime
RUN useradd --system --uid 10001 --no-create-home matcher
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER matcher
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status != 200)"]
CMD ["uvicorn", "matcher.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
