#!/bin/bash
set -e

echo "🚀 Starting Invoice RPA Bot Backend..."

# Configurar PORT por defecto si no existe
: ${PORT:=8000}

echo "📊 Running database migrations..."
alembic upgrade head || echo "⚠️  Migration failed or not needed"

echo "✅ Starting FastAPI server on port $PORT..."
exec uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
