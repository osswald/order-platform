FROM python:3.12-slim
WORKDIR /app
COPY packages/vendiqo_shared /packages/vendiqo_shared
RUN pip install --no-cache-dir -e /packages/vendiqo_shared
COPY cloud/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cloud/backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
