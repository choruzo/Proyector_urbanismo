"""
Tests para app/tasks/initial_load.py

Patrón: estáticos (sin red ni BD real) + unitarios con mocks.
Siguiendo la misma estructura que tests/test_alembic.py.

Tests estáticos (7):
  1. El módulo existe
  2. Tiene bloque __main__
  3. Contiene las 4 funciones de carga por fuente
  4. Contiene la función orquestadora cargar_todo
  5. Tiene argparse con --fuente y --force
  6. BARRIOS_GETAFE tiene al menos 10 barrios con los campos requeridos
  7. VISADOS_REFERENCIA cubre desde 2001 hasta al menos 2020

Tests unitarios con mock (4):
  8.  _cargar_barrios: skip si ya hay datos y force=False
  9.  _cargar_barrios: inserta hardcoded aunque el WFS falle
  10. _cargar_visados: usa datos de referencia si scraper lanza excepción
  11. _cargar_visados: usa datos de referencia si scraper devuelve DataFrame vacío
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Directorio raíz del backend
BACKEND_DIR = Path(__file__).parent.parent
APP_DIR = BACKEND_DIR / "app"
INITIAL_LOAD_PATH = APP_DIR / "tasks" / "initial_load.py"

# Añadir backend al path para importar módulos de la app
sys.path.insert(0, str(BACKEND_DIR))

# Variables de entorno mínimas para que Pydantic Settings no falle en los tests unitarios
_ENV_MOCK = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "test_db",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
}


# ---------------------------------------------------------------------------
# Tests estáticos — sin BD ni red
# ---------------------------------------------------------------------------

def test_modulo_existe():
    """El archivo app/tasks/initial_load.py existe."""
    assert INITIAL_LOAD_PATH.exists(), "app/tasks/initial_load.py no encontrado"


def test_tiene_main_block():
    """El módulo tiene bloque if __name__ == '__main__'."""
    content = INITIAL_LOAD_PATH.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in content, (
        "initial_load.py debe tener bloque if __name__ == '__main__'"
    )


def test_funciones_por_fuente():
    """Contiene las 4 funciones privadas de carga por fuente."""
    content = INITIAL_LOAD_PATH.read_text(encoding="utf-8")
    for fn in (
        "_cargar_barrios",
        "_cargar_visados",
        "_cargar_valores_suelo",
        "_cargar_alertas_bocm",
    ):
        assert f"def {fn}" in content, f"Falta la función {fn} en initial_load.py"


def test_tiene_cargar_todo():
    """Contiene la función orquestadora cargar_todo."""
    content = INITIAL_LOAD_PATH.read_text(encoding="utf-8")
    assert "def cargar_todo" in content, "Falta función cargar_todo en initial_load.py"


def test_argparse_fuente_y_force():
    """Contiene argparse con --fuente y --force."""
    content = INITIAL_LOAD_PATH.read_text(encoding="utf-8")
    assert "--fuente" in content, "Falta argumento --fuente en argparse"
    assert "--force" in content, "Falta argumento --force en argparse"


def test_datos_fallback_barrios():
    """BARRIOS_GETAFE contiene al menos 10 barrios con los campos obligatorios."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import BARRIOS_GETAFE

    assert len(BARRIOS_GETAFE) >= 10, "BARRIOS_GETAFE debe tener al menos 10 barrios"
    for b in BARRIOS_GETAFE:
        assert "codigo" in b,   "Cada barrio debe tener campo 'codigo'"
        assert "nombre" in b,   "Cada barrio debe tener campo 'nombre'"
        assert "distrito" in b, "Cada barrio debe tener campo 'distrito'"
        assert b["codigo"].startswith("GF"), "Los códigos deben empezar por 'GF'"


def test_datos_fallback_visados():
    """VISADOS_REFERENCIA cubre desde 2001 hasta al menos 2020 (≥ 20 años)."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import VISADOS_REFERENCIA

    annos = {v["anno"] for v in VISADOS_REFERENCIA}
    assert 2001 in annos, "VISADOS_REFERENCIA debe incluir el año 2001"
    assert 2020 in annos, "VISADOS_REFERENCIA debe incluir hasta al menos 2020"
    assert len(annos) >= 20, "VISADOS_REFERENCIA debe cubrir al menos 20 años distintos"
    for row in VISADOS_REFERENCIA:
        assert "anno" in row,            "Cada fila de visados debe tener campo 'anno'"
        assert "numero_viviendas" in row, "Cada fila de visados debe tener 'numero_viviendas'"
        assert row["numero_viviendas"] > 0, f"Año {row['anno']}: numero_viviendas debe ser > 0"


# ---------------------------------------------------------------------------
# Tests unitarios con mocks
# ---------------------------------------------------------------------------

def test_cargar_barrios_skip_si_existen():
    """Si ya hay barrios y force=False, la función retorna sin insertar nada."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import _cargar_barrios

    db_mock = MagicMock()
    db_mock.query.return_value.count.return_value = 12  # tabla ya poblada

    resultado = _cargar_barrios(db_mock, force=False)

    assert resultado["insertados"] == 0
    db_mock.add.assert_not_called()
    db_mock.commit.assert_not_called()


def test_cargar_barrios_fallback_cuando_wfs_falla():
    """Si el WFS del Catastro falla, _cargar_barrios igualmente inserta los barrios hardcoded."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import _cargar_barrios, BARRIOS_GETAFE

    db_mock = MagicMock()
    db_mock.query.return_value.count.return_value = 0       # tabla vacía → no skip
    db_mock.query.return_value.filter.return_value.first.return_value = None  # sin duplicados

    with patch("app.tasks.initial_load.CatastroScraper") as MockScraper:
        MockScraper.return_value.get_poligono_municipio_wfs.side_effect = Exception("timeout")
        MockScraper.return_value.close = MagicMock()

        resultado = _cargar_barrios(db_mock, force=False)

    assert resultado["insertados"] == len(BARRIOS_GETAFE), (
        "Debe insertar todos los barrios hardcoded aunque el WFS falle"
    )
    assert resultado["errores"] == 0
    assert db_mock.add.call_count == len(BARRIOS_GETAFE)
    db_mock.commit.assert_called_once()


def test_cargar_visados_usa_referencia_si_scraper_falla():
    """Si el scraper MIVAU lanza excepción, _cargar_visados inserta los datos de referencia."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import _cargar_visados, VISADOS_REFERENCIA

    db_mock = MagicMock()
    db_mock.query.return_value.count.return_value = 0
    db_mock.query.return_value.filter.return_value.first.return_value = None

    with patch("app.tasks.initial_load.ViviendaScraper") as MockScraper:
        MockScraper.return_value.get_visados_getafe.side_effect = Exception("Connection refused")
        MockScraper.return_value.close = MagicMock()

        resultado = _cargar_visados(db_mock, force=False)

    assert resultado["insertados"] == len(VISADOS_REFERENCIA), (
        "Debe insertar todos los datos de referencia si el scraper falla"
    )
    assert resultado["errores"] == 0
    db_mock.commit.assert_called()


def test_cargar_visados_usa_referencia_si_df_vacio():
    """Si el scraper devuelve DataFrame vacío, _cargar_visados usa los datos de referencia."""
    pytest.importorskip("geoalchemy2", reason="geoalchemy2 solo disponible en Docker")

    with patch.dict(os.environ, _ENV_MOCK):
        from app.tasks.initial_load import _cargar_visados, VISADOS_REFERENCIA

    db_mock = MagicMock()
    db_mock.query.return_value.count.return_value = 0
    db_mock.query.return_value.filter.return_value.first.return_value = None

    with patch("app.tasks.initial_load.ViviendaScraper") as MockScraper:
        MockScraper.return_value.get_visados_getafe.return_value = pd.DataFrame()  # vacío
        MockScraper.return_value.close = MagicMock()

        resultado = _cargar_visados(db_mock, force=False)

    assert resultado["insertados"] == len(VISADOS_REFERENCIA), (
        "Debe insertar todos los datos de referencia si el DataFrame está vacío"
    )
    assert resultado["errores"] == 0
    db_mock.commit.assert_called()
