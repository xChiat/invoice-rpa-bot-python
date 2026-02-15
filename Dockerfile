# Base image
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/ ./backend/
COPY alembic.ini .
COPY start.sh .

# Crear directorio para datos temporales
RUN mkdir -p /app/data/pdfs

# Dar permisos de ejecución al script de inicio
RUN chmod +x start.sh

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Exponer puerto
EXPOSE ${PORT}

# Comando de inicio
CMD ["./start.sh"]
