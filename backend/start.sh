#!/bin/bash
set -e

# Roda migrations
alembic upgrade head

# Inicia Celery worker em background
celery -A app.tasks.celery_app worker --loglevel=info &

# Inicia API em foreground (exec substitui o shell — PID correto para o Render)
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
