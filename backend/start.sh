#!/bin/bash
set -e

# Roda migrations
alembic upgrade head

# Celery com pool=solo (single-thread) — reduz footprint de memória no free tier
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1 --pool=solo &

# API em foreground
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
