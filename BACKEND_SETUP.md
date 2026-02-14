# 🚀 Invoice RPA Bot - Backend Setup Guide

Backend API para procesamiento automático de facturas chilenas con OCR e inteligencia artificial.

## 📋 Requisitos Previos

### Software Necesario
- **Python 3.11+**
- **PostgreSQL 14+** (o usar Railway/Render managed database)
- **Tesseract OCR** (para procesamiento de PDFs escaneados)
- **Poppler** (para conversión PDF a imágenes)

### Instalar Tesseract OCR

**Windows:**
```powershell
# Descargar instalador desde: https://github.com/UB-Mannheim/tesseract/wiki
# Agregar a PATH: C:\Program Files\Tesseract-OCR

# Verificar instalación
tesseract --version
```

**Linux/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

---

## ⚙️ Configuración Local

### 1. Clonar Repositorio

```bash
git clone https://github.com/xChiat/invoice-rpa-bot-python.git
cd invoice-rpa-bot-python
```

### 2. Crear Entorno Virtual

```bash
# Crear virtualenv
python -m venv venv

# Activar (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activar (Linux/Mac)
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copiar archivo de ejemplo y agregar credenciales:

```bash
# En raíz del proyecto
cp .env.example .env
```

**Editar `.env` y configurar:**

```bash
# ===== Database =====
DATABASE_URL=postgresql://user:password@localhost:5432/invoice_rpa

# ===== JWT Authentication =====
# Generar secreto aleatorio:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=tu-secreto-aleatorio-super-seguro-aqui

# ===== Cloudinary (Storage) =====
# Crear cuenta gratuita en: https://cloudinary.com/users/register/free
CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret

# ===== Frontend URL =====
FRONTEND_URL=http://localhost:3000

# ===== Opcional: Sentry Monitoring =====
SENTRY_DSN=https://tu-sentry-dsn@sentry.io/proyecto
```

---

## 🗄️ Configurar Base de Datos

### Opción A: PostgreSQL Local

**Instalar PostgreSQL:**
- Windows: https://www.postgresql.org/download/windows/
- Mac: `brew install postgresql`
- Linux: `sudo apt-get install postgresql postgresql-contrib`

**Crear base de datos:**

```sql
-- Conectarse a PostgreSQL
psql -U postgres

-- Crear database
CREATE DATABASE invoice_rpa;

-- Crear usuario
CREATE USER invoice_user WITH PASSWORD 'tu_password_seguro';

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE invoice_rpa TO invoice_user;

-- Salir
\q
```

**Actualizar DATABASE_URL en `.env`:**
```
DATABASE_URL=postgresql://invoice_user:tu_password_seguro@localhost:5432/invoice_rpa
```

### Opción B: Railway Managed Database (Recomendado para Cloud)

1. Ir a [railway.app](https://railway.app)
2. Crear cuenta y nuevo proyecto
3. Agregar servicio → PostgreSQL
4. Copiar `DATABASE_URL` de las variables de entorno
5. Pegar en tu `.env` local

---

## 🔧 Inicializar Base de Datos

### 1. Ejecutar Migraciones (Crear Tablas)

```bash
# Desde la raíz del proyecto
alembic upgrade head
```

Si no existe la migración inicial, crearla:

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 2. Poblar Datos Iniciales (Seed)

```bash
# Ejecutar script de seed
python -m backend.scripts.seed_data
```

Esto crea:
- Tipos de factura (Escaneada/Digital)

---

## 🚀 Ejecutar Servidor de Desarrollo

```bash
# Desde directorio raíz
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Verificar que funciona:**
- API Docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/health

---

## 🧪 Probar API

### 1. Registrar Empresa y Usuario Admin

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@tuempresa.com",
    "password": "Password123!",
    "full_name": "Admin Usuario",
    "empresa_nombre": "Mi Empresa SPA",
    "empresa_rut": "76.123.456-7"
  }'
```

**Guardar el `access_token` de la respuesta.**

### 2. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@tuempresa.com",
    "password": "Password123!"
  }'
```

### 3. Subir Factura PDF

```bash
curl -X POST http://localhost:8000/api/facturas/upload \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -F "file=@ruta/a/tu/factura.pdf"
```

### 4. Ver Estado de Procesamiento

```bash
curl http://localhost:8000/api/facturas/1/status \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

### 5. Obtener Dashboard de Estadísticas

```bash
curl http://localhost:8000/api/stats/dashboard \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

---

## ☁️ Deployment a Railway

### 1. Instalar Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Login y Crear Proyecto

```bash
railway login
railway init
```

### 3. Agregar Servicios

En el dashboard de Railway:
- **PostgreSQL**: Add Service → Database → PostgreSQL
- **Redis** (opcional): Add Service → Database → Redis

### 4. Configurar Variables de Entorno

En Railway Dashboard → Variables:

```
DATABASE_URL=${POSTGRES_URL}  # Auto-provisto
SECRET_KEY=<generar-aleatorio>
CLOUDINARY_CLOUD_NAME=<tu-cloud-name>
CLOUDINARY_API_KEY=<tu-api-key>
CLOUDINARY_API_SECRET=<tu-api-secret>
FRONTEND_URL=https://tu-frontend.vercel.app
DEBUG=false
```

### 5. Deploy

```bash
# Railway auto-deploya en cada push a main
git push origin main
```

**Railway ejecutará:**
1. `docker build` usando el Dockerfile
2. Ejecutará migraciones automáticamente
3. Iniciará el servidor con `uvicorn`

**URL generada:** `https://tu-proyecto.up.railway.app`

### 6. Ejecutar Migraciones en Producción

```bash
# Conectarse a Railway
railway link

# Ejecutar migraciones
railway run alembic upgrade head

# Seed inicial
railway run python -m backend.scripts.seed_data
```

---

## 📁 Estructura del Proyecto

```
invoice-rpa-bot-python/
├── backend/
│   ├── api/
│   │   ├── routes/          # Endpoints REST
│   │   │   ├── auth.py      # Registro, login, tokens
│   │   │   ├── facturas.py  # CRUD facturas, upload, export
│   │   │   ├── stats.py     # Dashboard, estadísticas
│   │   │   └── users.py     # Gestión usuarios (admin)
│   │   ├── dependencies.py  # Auth middleware, DI
│   │   └── main.py          # FastAPI app
│   ├── core/
│   │   ├── config.py        # Settings (Pydantic)
│   │   ├── database.py      # SQLAlchemy setup
│   │   └── security.py      # JWT, password hashing
│   ├── models/
│   │   ├── database/        # Modelos SQLAlchemy
│   │   └── schemas/         # Schemas Pydantic
│   ├── services/
│   │   ├── pdf_processor_service.py      # Extracción texto/OCR
│   │   ├── factura_extractor_service.py  # Parsing regex
│   │   ├── storage_service.py            # Cloudinary/S3
│   │   └── export_service.py             # Excel export
│   ├── alembic/             # Migraciones DB
│   └── requirements.txt
├── data/
│   ├── input/               # PDFs de prueba (local)
│   └── output/              # Resultados (local)
├── Dockerfile               # Container para Railway
├── railway.toml             # Config Railway
├── alembic.ini              # Config Alembic
└── .env.example             # Template variables
```

---

## 🔐 Cloudinary Setup (IMPORTANTE)

**Cloudinary** se usa para almacenar PDFs en la nube (free tier: 25 GB storage).

### Pasos:

1. **Crear cuenta gratuita:** https://cloudinary.com/users/register/free
2. **Obtener credenciales:**
   - Dashboard → Settings → Access Keys
   - Copiar: `Cloud name`, `API Key`, `API Secret`
3. **Agregar a `.env`:**
   ```
   CLOUDINARY_CLOUD_NAME=tu-cloud-name
   CLOUDINARY_API_KEY=123456789012345
   CLOUDINARY_API_SECRET=tu-secret-aqui
   ```

**Alternativa local:** Si no configuras Cloudinary, los PDFs se guardan en `data/pdfs/` (solo para desarrollo).

---

## 📊 Endpoints Disponibles

### Autenticación
- `POST /api/auth/register` - Registrar empresa y admin
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/refresh` - Refrescar token
- `GET /api/auth/me` - Info usuario actual

### Facturas
- `POST /api/facturas/upload` - Subir PDF
- `GET /api/facturas` - Listar facturas (paginado)
- `GET /api/facturas/{id}` - Detalle factura
- `GET /api/facturas/{id}/status` - Estado procesamiento
- `PATCH /api/facturas/{id}` - Actualizar campos
- `DELETE /api/facturas/{id}` - Eliminar (admin)
- `GET /api/facturas/export/excel` - Exportar a Excel

### Estadísticas
- `GET /api/stats/dashboard` - KPIs generales
- `GET /api/stats/top-emisores` - Top N emisores
- `GET /api/stats/resumen-mensual/{year}/{month}` - Resumen mes

### Usuarios (Admin)
- `GET /api/users` - Listar usuarios
- `POST /api/users` - Crear usuario
- `GET /api/users/{id}` - Detalle usuario
- `PATCH /api/users/{id}` - Actualizar usuario
- `DELETE /api/users/{id}` - Desactivar usuario

---

## 🐛 Troubleshooting

### Error: "Tesseract not found"

**Solución:**
```bash
# Windows: Agregar a PATH
setx PATH "%PATH%;C:\Program Files\Tesseract-OCR"

# Verificar
tesseract --version
```

### Error: "Could not connect to database"

**Verificar:**
1. PostgreSQL está corriendo: `pg_ctl status`
2. `DATABASE_URL` correcto en `.env`
3. Database existe: `psql -l | grep invoice_rpa`

### Error: "ModuleNotFoundError: backend"

**Solución:**
```bash
# Asegurar que estás en la raíz del proyecto
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Windows
$env:PYTHONPATH = "${env:PYTHONPATH};$(pwd)"
```

### Error: "Cloudinary upload failed"

**Verificar:**
1. Credenciales correctas en `.env`
2. Internet disponible
3. Free tier no excedido (25 GB)

**Alternativa:** Comentar uso de Cloudinary (usará filesystem local).

---

## 📝 Eliminar Carpeta `src/` Antigua

**✅ SÍ, puedes eliminar la carpeta `src/`**

Toda la lógica ha sido migrada a `backend/`:
- `src/extraction.py` → `backend/services/pdf_processor_service.py`
- `src/ai_extraction.py` → `backend/services/factura_extractor_service.py`
- `src/factura.py` → `backend/models/database/models.py`
- `src/main.py` → Ya no es necesario (reemplazado por API)

**Mantener:**
- `data/input/` - PDFs de prueba
- `data/output/` - Resultados antiguos (opcional, para referencia)

**Eliminar:**
```powershell
Remove-Item -Recurse -Force src/
```

---

## 🎯 Próximos Pasos

1. ✅ Backend completo
2. ⏳ Crear frontend React (ver carpeta `frontend/` en próximo commit)
3. ⏳ Deploy frontend a Vercel
4. ⏳ Conectar frontend con backend API
5. ⏳ Testing end-to-end

---

## 📚 Documentación API

Una vez corriendo el servidor, visitar:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

---

## 👥 Soporte

Para problemas o preguntas:
1. Revisar logs: `railway logs` (producción) o consola (local)
2. Verificar variables de entorno
3. Consultar este README
4. Abrir issue en GitHub

---

**¡Listo para procesar facturas! 🚀📄**
