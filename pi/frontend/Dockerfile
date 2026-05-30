# Build context: repository root (see pi/docker-compose.yml).
FROM node:20-alpine
WORKDIR /app/pi/frontend
COPY pi/frontend/package.json pi/frontend/package-lock.json* ./
RUN npm install
COPY pi/frontend/ .
COPY scripts /app/scripts
COPY VERSION /app/VERSION
EXPOSE 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
