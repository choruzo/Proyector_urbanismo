"""
Tests estáticos de la configuración Alembic (sin necesidad de PostgreSQL activo).

Verifican:
  1. alembic.ini existe y tiene script_location correcto
  2. models/__init__.py importa los 3 módulos de modelos
  3. Base.metadata registra las 8 tablas esperadas
  4. main.py NO contiene create_all()
  5. Existe al menos un archivo de migración en versions/
  6. La migración inicial contiene soporte PostGIS
  7. La migración inicial tiene función downgrade()
"""
import configparser
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Directorio raíz del backend (un nivel arriba de tests/)
BACKEND_DIR = Path(__file__).parent.parent
APP_DIR = BACKEND_DIR / "app"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"

# Añadir backend al path para importar módulos de la app
sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Test 1: alembic.ini existe y tiene script_location = migrations
# ---------------------------------------------------------------------------
def test_alembic_ini_exists():
    ini_path = BACKEND_DIR / "alembic.ini"
    assert ini_path.exists(), "alembic.ini no encontrado en backend/"

    config = configparser.ConfigParser()
    config.read(ini_path)

    assert "alembic" in config.sections(), "alembic.ini no tiene sección [alembic]"
    assert config["alembic"]["script_location"] == "migrations", (
        "script_location debe ser 'migrations'"
    )


# ---------------------------------------------------------------------------
# Test 2: models/__init__.py importa los 3 módulos
# ---------------------------------------------------------------------------
def test_models_init_imports_all_modules():
    init_path = APP_DIR / "models" / "__init__.py"
    assert init_path.exists(), "app/models/__init__.py no encontrado"

    content = init_path.read_text(encoding="utf-8")
    assert "catastral" in content, "__init__.py debe importar de catastral"
    assert "construccion" in content, "__init__.py debe importar de construccion"
    assert "alertas" in content, "__init__.py debe importar de alertas"


# ---------------------------------------------------------------------------
# Test 3: Base.metadata registra las 8 tablas esperadas
# ---------------------------------------------------------------------------
EXPECTED_TABLES = {
    "barrios",
    "parcelas",
    "valores_suelo",
    "obras_nueva",
    "visados_estadisticos",
    "alertas",
    "inversiones_publicas",
    "proyectos_emsv",
}

def test_base_metadata_has_all_tables():
    # Requiere geoalchemy2 (disponible dentro del contenedor Docker)
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en el contenedor Docker")

    with patch.dict(os.environ, {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
    }):
        from app.core.database import Base
        import app.models  # noqa: F401 — activa los imports

        registered = set(Base.metadata.tables.keys())
        missing = EXPECTED_TABLES - registered
        assert not missing, f"Tablas faltantes en Base.metadata: {missing}"


# ---------------------------------------------------------------------------
# Test 4: main.py NO contiene create_all()
# ---------------------------------------------------------------------------
def test_main_no_create_all():
    main_path = APP_DIR / "main.py"
    assert main_path.exists(), "app/main.py no encontrado"

    content = main_path.read_text(encoding="utf-8")
    assert "create_all" not in content, (
        "main.py todavía contiene create_all() — debe eliminarse y dejar que Alembic gestione el esquema"
    )


# ---------------------------------------------------------------------------
# Test 5: existe al menos un archivo de migración en versions/
# ---------------------------------------------------------------------------
def test_migration_file_exists():
    assert VERSIONS_DIR.exists(), "migrations/versions/ no encontrado"
    version_files = [
        f for f in VERSIONS_DIR.iterdir()
        if f.suffix == ".py" and f.name != "__init__.py"
    ]
    assert len(version_files) >= 1, (
        "No hay archivos de migración en migrations/versions/"
    )


# ---------------------------------------------------------------------------
# Test 6: la migración inicial contiene soporte PostGIS
# ---------------------------------------------------------------------------
def test_migration_has_postgis():
    version_files = sorted(VERSIONS_DIR.glob("*.py"))
    assert version_files, "No hay archivos de migración"

    first_migration = version_files[0].read_text(encoding="utf-8")
    assert "postgis" in first_migration.lower(), (
        "La migración inicial debe incluir CREATE EXTENSION postgis"
    )


# ---------------------------------------------------------------------------
# Test 7: la migración inicial tiene función downgrade()
# ---------------------------------------------------------------------------
def test_migration_has_downgrade():
    version_files = sorted(VERSIONS_DIR.glob("*.py"))
    assert version_files, "No hay archivos de migración"

    first_migration = version_files[0].read_text(encoding="utf-8")
    assert "def downgrade" in first_migration, (
        "La migración inicial debe definir la función downgrade()"
    )
