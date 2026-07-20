FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /usr/local/bin/
# Layout mirrors the repo so the lockfile's relative path to vendiqo_shared resolves.
WORKDIR /repo/pi/backend
COPY packages/vendiqo_shared /repo/packages/vendiqo_shared
COPY pi/backend/pyproject.toml pi/backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY pi/backend/alembic.ini .
COPY pi/backend/alembic ./alembic
COPY pi/backend/app ./app
ARG APP_VERSION
ARG APP_BUILD_TIME
ENV APP_VERSION=$APP_VERSION
ENV APP_BUILD_TIME=$APP_BUILD_TIME
ENV PATH="/repo/pi/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
