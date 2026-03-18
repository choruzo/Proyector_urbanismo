"""
Tests para los scrapers BOCM y MIVAU tras corrección de URLs rotas.

Tests estáticos (3): verifican que las constantes apuntan a las URLs correctas.
Tests de integración (2): verifican conectividad HTTP real (requieren red).
  → Excluirlos en CI sin red: pytest -m "not integration"

Refs:
  - Bug BOCM: /buscador (404) → /advanced-search (200) — bocm.py
  - Bug MIVAU: mivau.gob.es (403) → apps.fomento.gob.es (200) — vivienda.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

_ENV_MOCK = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "test_db",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
}


# ---------------------------------------------------------------------------
# Tests estáticos — verifican las constantes sin red ni BD
# ---------------------------------------------------------------------------

def test_bocm_url_constante_actualizada():
    """BOCM_SEARCH_URL apunta a /advanced-search, no al antiguo /buscador."""
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.bocm import BOCM_SEARCH_URL

    assert "/advanced-search" in BOCM_SEARCH_URL, (
        "BOCM_SEARCH_URL debe apuntar a /advanced-search (el antiguo /buscador devuelve 404)"
    )
    assert "/buscador" not in BOCM_SEARCH_URL, (
        "BOCM_SEARCH_URL no debe usar la ruta /buscador (obsoleta)"
    )


def test_bocm_params_formato_fecha():
    """buscar_publicaciones_getafe usa el parámetro 'keys' y formato de fecha DD-MM-YYYY."""
    content = (BACKEND_DIR / "app" / "scrapers" / "bocm.py").read_text(encoding="utf-8")
    assert '"keys"' in content, (
        "bocm.py debe usar el parámetro 'keys' (no 'busqueda') para el texto de búsqueda"
    )
    assert "field_bulletin_field_date" in content, (
        "bocm.py debe usar 'field_bulletin_field_date[value]' como parámetro de fecha"
    )
    assert '"%d-%m-%Y"' in content, (
        "El formato de fecha debe ser DD-MM-YYYY (separador guión), requerido por Drupal Views"
    )


def test_mivau_urls_apuntan_a_fomento():
    """Todas las URLs en URLS_ESTADISTICAS apuntan a apps.fomento.gob.es, no a mivau.gob.es."""
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.vivienda import URLS_ESTADISTICAS

    assert len(URLS_ESTADISTICAS) > 0, "URLS_ESTADISTICAS no debe estar vacío"
    for nombre, url in URLS_ESTADISTICAS.items():
        assert "mivau.gob.es" not in url, (
            f"URL '{nombre}' aún apunta a mivau.gob.es (devuelve 403). "
            f"Debe usar apps.fomento.gob.es"
        )
        assert "fomento.gob.es" in url, (
            f"URL '{nombre}' debe apuntar a fomento.gob.es — valor actual: {url}"
        )


# ---------------------------------------------------------------------------
# Tests de integración — requieren acceso a red real
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_bocm_search_url_responde_200():
    """GET a la nueva URL del buscador BOCM responde HTTP 200 (no 404)."""
    import httpx
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.bocm import BOCM_SEARCH_URL

    response = httpx.get(
        BOCM_SEARCH_URL,
        params={"keys": "Getafe"},
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "ProyectorUrbanisticoGetafe/0.1"},
    )
    assert response.status_code == 200, (
        f"BOCM advanced-search devolvió {response.status_code}, esperado 200. "
        f"URL: {response.url}"
    )


@pytest.mark.integration
def test_mivau_url_visados_descarga_xls():
    """GET a la nueva URL de visados fomento.gob.es responde HTTP 200 y devuelve un XLS."""
    import httpx
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.vivienda import URLS_ESTADISTICAS

    url = URLS_ESTADISTICAS["visados_madrid_viviendas"]
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    assert response.status_code == 200, (
        f"MIVAU/Fomento visados devolvió {response.status_code}, esperado 200. URL: {url}"
    )
    assert len(response.content) > 10_000, (
        f"El fichero XLS descargado parece vacío ({len(response.content)} bytes)"
    )
    # Verificar que es un fichero Excel (cabecera OLE2 o ZIP/OOXML)
    magic = response.content[:4]
    assert magic in (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"), (
        "El contenido descargado no parece un fichero Excel válido (OLE2 o OOXML)"
    )
