"""
Script inicial de configuración para Alembic.
Configura la conexión a base de datos y el contexto de migraciones.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Importar configuración y modelos
from backend.core.config import settings
from backend.core.database import Base
from backend.models.database.models import (
    User, Empresa, Factura, TipoFactura, AuditLog
)

# Configuración de Alembic
config = context.config

# Interpretar el archivo de configuración para logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos SQLAlchemy
target_metadata = Base.metadata

# Sobreescribir sqlalchemy.url con el valor de settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Ejecutar migraciones en modo 'offline'.
    
    Configura el contexto con solo una URL, sin Engine.
    Útil para generar SQL scripts.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecutar migraciones en modo 'online'.
    
    Crea un Engine y asocia una conexión con el contexto.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
