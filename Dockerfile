# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SQLITE_PATH=/app/accidents.db \
    LANCEDB_DIR=/app/lancedb \
    CHATSTORE_PATH=/app/runtime/chats.db

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY accidents.db ./accidents.db
COPY lancedb/ ./lancedb/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist/

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/runtime \
    && chown appuser:appgroup /app/runtime

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
