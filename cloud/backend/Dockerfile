FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /usr/local/bin/
# Layout mirrors the repo so the lockfile's relative path to vendiqo_shared resolves.
WORKDIR /repo/cloud/backend
COPY packages/vendiqo_shared /repo/packages/vendiqo_shared
COPY cloud/backend/pyproject.toml cloud/backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY cloud/backend/app ./app
ENV PATH="/repo/cloud/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
