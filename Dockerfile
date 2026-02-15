# Multi-stage build para optimizar tamaño
FROM python:3.11-slim as base

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/ /app/backend/
COPY alembic.ini /app/
COPY init_backend.py /app/

# Crear directorio para datos temporales
RUN mkdir -p /app/data/pdfs

# Variables de entorno por defecto (sobreescritas por Railway)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/health', timeout=5)"

# Exponer puerto (Railway usa PORT dinámico)
EXPOSE ${PORT}

# Script de inicio que ejecuta migraciones antes de iniciar
COPY <<'EOF' /app/start.sh
#!/bin/bash
set -e
echo "Running database migrations..."
alembic upgrade head || echo "Migration failed or not needed"
echo "Starting application..."
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}
EOF

RUN chmod +x /app/start.sh

# Comando para iniciar la aplicación
CMD ["/app/start.sh"]
