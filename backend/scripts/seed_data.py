"""
Script para poblar datos iniciales en la base de datos.
Ejecutar después de crear las tablas con Alembic.
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import SessionLocal, init_db
from backend.models.database.models import TipoFactura
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_tipos_factura():
    """Poblar tabla de tipos de factura"""
    db = SessionLocal()
    try:
        # Verificar si ya existen datos
        existing_count = db.query(TipoFactura).count()
        if existing_count > 0:
            logger.info(f"TipoFactura table already has {existing_count} records. Skipping seed.")
            return
        
        # Crear tipos de factura
        tipos = [
            TipoFactura(
                id=1,
                tipo="Escaneada",
                descripcion="Factura escaneada procesada con OCR"
            ),
            TipoFactura(
                id=2,
                tipo="Digital",
                descripcion="Factura digital con texto extraíble"
            )
        ]
        
        db.add_all(tipos)
        db.commit()
        
        logger.info("✓ Tipos de factura creados exitosamente")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Ejecutar todos los seeds"""
    logger.info("Starting database seed...")
    
    # Asegurar que las tablas existen (solo en desarrollo)
    # En producción usar Alembic migrations
    logger.info("Creating tables if they don't exist...")
    init_db()
    
    # Poblar datos iniciales
    seed_tipos_factura()
    
    logger.info("✓ Database seed completed successfully!")


if __name__ == "__main__":
    main()
