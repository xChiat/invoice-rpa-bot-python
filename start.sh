#!/bin/bash
set -e

echo "🚀 Starting Invoice RPA Bot Backend..."

echo "📊 Running database migrations..."
alembic upgrade head || echo "⚠️  Migration failed or not needed"

echo "✅ Starting FastAPI server..."
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
