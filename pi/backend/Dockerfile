FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /usr/local/bin/
# Layout mirrors the repo so the lockfile's relative path to vendiqo_shared resolves.
WORKDIR /repo/pi/backend
COPY packages/vendiqo_shared /repo/packages/vendiqo_shared
COPY pi/backend/pyproject.toml pi/backend/uv.lock ./
# copy avoids hardlink edge cases under some builders; fail the build if console
# scripts are empty (the failure mode seen with QEMU-emulated arm64 publishes).
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev \
    && test -s /repo/pi/backend/.venv/bin/uvicorn \
    && test -s /usr/local/bin/uv \
    && /repo/pi/backend/.venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"
COPY pi/backend/alembic.ini .
COPY pi/backend/alembic ./alembic
COPY pi/backend/app ./app
ARG APP_VERSION
ARG APP_BUILD_TIME
ENV APP_VERSION=$APP_VERSION
ENV APP_BUILD_TIME=$APP_BUILD_TIME
ENV PATH="/repo/pi/backend/.venv/bin:$PATH"
EXPOSE 8000
# Prefer the module form so a missing/empty console script cannot mask a bad image.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
