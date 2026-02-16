"""
Configuración centralizada de la aplicación usando Pydantic Settings.
Todas las variables de entorno se cargan desde .env o variables de entorno del sistema.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación para cloud deployment"""
    
    # Application
    app_name: str = "Invoice RPA Bot"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Database (Railway/Render proveen DATABASE_URL automáticamente)
    database_url: str
    
    # Redis (para caché y sesiones)
    redis_url: str = "redis://localhost:6379"
    
    # JWT Authentication
    secret_key: str  # Usar secretos aleatorios en producción
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Cloudinary (para almacenamiento de PDFs)
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    
    # CORS (frontend URLs - separadas por comas)
    # Ejemplo: "https://app.vercel.app,http://localhost:3000"
    frontend_url: str = "https://invoice-rpa-bot-frontend-nerivyw26-xchiats-projects.vercel.app"
    
    # Sentry (monitoreo de errores - opcional)
    sentry_dsn: Optional[str] = None
    
    # File Upload
    max_upload_size_mb: int = 10
    allowed_extensions: set = {".pdf"}
    
    # Processing
    extraction_timeout_seconds: int = 120
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins(self) -> list:
        """
        Lista de orígenes permitidos para CORS.
        Soporta múltiples URLs separadas por comas en FRONTEND_URL.
        """
        # Parsear URLs separadas por comas
        urls = [url.strip() for url in self.frontend_url.split(",")]
        
        # Agregar localhost para desarrollo local
        default_locals = [
            "http://localhost:3000",  # React/Next.js default
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",  # Vue default
        ]
        
        # Combinar y remover duplicados
        all_origins = list(set(urls + default_locals))
        return all_origins


# Instancia global de configuración
settings = Settings()
