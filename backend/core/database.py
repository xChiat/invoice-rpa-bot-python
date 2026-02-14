"""
Configuración de la base de datos con SQLAlchemy.
Maneja la conexión a PostgreSQL y el ciclo de vida de las sesiones.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from backend.core.config import settings


# Crear engine de SQLAlchemy
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verificar conexiones antes de usar
    pool_size=5,
    max_overflow=10,
    echo=settings.debug  # Log SQL queries en debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para todos los modelos
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos.
    Se usa en endpoints FastAPI para inyección de dependencias.
    
    Uso:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializar base de datos (crear todas las tablas).
    Llamar esto solo en desarrollo o usar Alembic en producción.
    """
    Base.metadata.create_all(bind=engine)
