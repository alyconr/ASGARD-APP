#!/bin/sh
set -e

echo "[entrypoint] esperando PostgreSQL..."
for i in $(seq 1 30); do
  if python -c "
import socket, sys
from urllib.parse import urlparse
from src.infrastructure.config.settings import get_settings

url = urlparse(get_settings().alembic_database_url.replace('postgresql+psycopg', 'postgresql'))
host = url.hostname or 'localhost'
port = url.port or 5432
sys.exit(0 if socket.create_connection((host, port), timeout=2) else 1)
" 2>/dev/null; then
    break
  fi
  sleep 2
done

echo "[entrypoint] aplicando migraciones Alembic..."
alembic upgrade head

echo "[entrypoint] iniciando API..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
