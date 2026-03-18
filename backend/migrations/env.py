"""
Configuración del entorno de Alembic para el Proyector Urbanístico de Getafe.

- Lee DATABASE_URL desde Pydantic Settings (app.core.config)
- Importa todos los modelos para que autogenerate los detecte
- Configura soporte para tipos GeoAlchemy2 (PostGIS)
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Añadir el directorio raíz de la app al path para que funcione dentro del contenedor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar Base y TODOS los modelos — necesario para que autogenerate detecte las tablas
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  — activa los imports del __init__.py

# Importar settings para obtener DATABASE_URL desde variables de entorno
from app.core.config import settings  # noqa: E402

# Objeto de configuración de Alembic (lee alembic.ini)
config = context.config

# Inyectar la URL de conexión desde Pydantic Settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar logging si alembic.ini tiene sección [loggers]
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadatos de los modelos para autogenerate
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filtra los objetos a incluir en la migración.
    Excluye tablas de extensiones PostGIS (spatial_ref_sys, geometry_columns, etc.)
    """
    if type_ == "table" and name in (
        "spatial_ref_sys",
        "geometry_columns",
        "geography_columns",
        "raster_columns",
        "raster_overviews",
    ):
        return False
    return True


def run_migrations_offline() -> None:
    """
    Modo offline: genera el SQL sin conexión activa a la BD.
    Útil para revisar las migraciones antes de aplicarlas.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: conecta a la BD y aplica las migraciones.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=False,
            # Necesario para comparar tipos de columnas correctamente con GeoAlchemy2
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
