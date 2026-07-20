# Build context: repository root (see cloud/docker-compose.yml).
FROM node:24-alpine
WORKDIR /app/cloud/frontend
COPY cloud/frontend/package*.json ./
RUN npm ci
COPY cloud/frontend/ .
COPY packages/frontend-shared /app/packages/frontend-shared
COPY scripts /app/scripts
COPY VERSION /app/VERSION
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
