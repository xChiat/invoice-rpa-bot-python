"""
Aplicación principal FastAPI.
Configura CORS, rutas, middleware y manejo de errores.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.database import engine, Base
from backend.models.database.models import (
    User, Empresa, Factura, TipoFactura, AuditLog
)

# Configurar logging
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True  # Forzar reconfiguración si ya existe
)
logger = logging.getLogger(__name__)
logger.info("="*80)
logger.info(f"Logging configured at {settings.log_level.upper()} level")
logger.info(f"DEBUG mode: {settings.debug}")
logger.info(f"Frontend URL from config: {settings.frontend_url}")
logger.info(f"CORS origins that will be configured: {settings.cors_origins}")
logger.info("="*80)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Middleware de logging para todas las requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log detallado de todas las requests entrantes"""
    logger.info("="*80)
    logger.info(f"🔵 INCOMING REQUEST: {request.method} {request.url.path}")
    logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
    logger.info(f"Origin header: {request.headers.get('origin', 'NO ORIGIN')}")
    logger.info(f"All headers: {dict(request.headers)}")
    logger.info(f"Query params: {dict(request.query_params)}")
    
    # Special handling for OPTIONS
    if request.method == "OPTIONS":
        logger.warning(f"⚠️  OPTIONS (CORS Preflight) request detected")
        logger.info(f"Access-Control-Request-Method: {request.headers.get('access-control-request-method', 'NONE')}")
        logger.info(f"Access-Control-Request-Headers: {request.headers.get('access-control-request-headers', 'NONE')}")
    
    # Log body para POST/PUT/PATCH
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            logger.info(f"Body (raw): {body.decode('utf-8') if body else 'EMPTY'}")
            # Rehacer el body para que esté disponible para el endpoint
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        except Exception as e:
            logger.error(f"Error reading body: {e}")
    
    # Procesar request
    try:
        response = await call_next(request)
        
        if request.method == "OPTIONS":
            logger.info(f"🟢 OPTIONS Response status: {response.status_code}")
            # Log CORS headers in response
            logger.info("Response CORS headers:")
            for key in ['access-control-allow-origin', 'access-control-allow-methods', 
                       'access-control-allow-headers', 'access-control-allow-credentials']:
                value = response.headers.get(key, 'NOT SET')
                logger.info(f"  {key}: {value}")
        else:
            logger.info(f"Response status: {response.status_code}")
        
        logger.info("="*80)
        return response
    except Exception as e:
        logger.error(f"❌ Request failed with exception: {e}", exc_info=True)
        logger.info("="*80)
        raise

# Configurar CORS
logger.info("Configuring CORS middleware...")
logger.info(f"Allowed origins: {settings.cors_origins}")

# Usar allow_origin_regex como fallback si hay problemas con origins específicos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.cors_origins,  # Allow all en debug
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)
logger.info("✅ CORS middleware configured")


# Manejadores de errores globales
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejar errores de validación de Pydantic"""
    logger.error(f"\n{'='*80}")
    logger.error(f"VALIDATION ERROR on {request.method} {request.url.path}")
    logger.error(f"Errors: {exc.errors()}")
    logger.error(f"Body received: {exc.body}")
    logger.error(f"{'='*80}\n")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejar errores generales"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Endpoint de health check para monitoreo.
    Railway/Render usan esto para verificar que la app está funcionando.
    """
    try:
        # Verificar conexión a base de datos
        from sqlalchemy import text
        from backend.core.database import SessionLocal
        
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": db_status
    }


@app.get("/debug/cors", tags=["Debug"])
async def debug_cors(request: Request):
    """Endpoint de diagnóstico CORS - muestra configuración y headers"""
    return {
        "allowed_origins": settings.cors_origins,
        "request_origin": request.headers.get("origin"),
        "request_headers": dict(request.headers),
        "cors_configured": True
    }


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.app_version,
        "docs": "/api/docs",
        "health": "/health"
    }


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Acciones al iniciar la aplicación"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Environment: {'development' if settings.debug else 'production'}")
    logger.info(f"Logging level: {logging.getLogger().level} ({logging.getLevelName(logging.getLogger().level)})")
    logger.info(f"CORS origins configured: {settings.cors_origins}")
    logger.info(f"Database URL: {settings.database_url.split('@')[-1]}")  # Log sin credenciales
    
    # Inicializar Sentry si está configurado
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.1,
                environment="production" if not settings.debug else "development"
            )
            logger.info("Sentry initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}")
    
    # Crear tablas en desarrollo (en producción usar Alembic)
    if settings.debug:
        logger.info("Creating database tables (development mode)...")
        Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
async def shutdown_event():
    """Acciones al apagar la aplicación"""
    logger.info(f"Shutting down {settings.app_name}")


# Importar y registrar rutas
from backend.api.routes import auth, facturas, stats, users
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(facturas.router, prefix="/api/facturas", tags=["Facturas"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
