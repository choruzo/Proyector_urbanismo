"""
Tests para los scrapers BOCM, MIVAU e INE.

Tests estáticos (4): verifican constantes y configuración sin red ni BD.
Tests de integración (3): verifican conectividad HTTP real (requieren red).
  → Excluirlos en CI sin red: pytest -m "not integration"

Refs:
  - Bug BOCM: /buscador (404) → /advanced-search (200) — bocm.py
  - Bug MIVAU: mivau.gob.es (403) → apps.fomento.gob.es (200) — vivienda.py
  - Bug INE ETN: tabla 46964 inexistente → serie ETDP3899 (Madrid provincia) — ine.py
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


def test_ine_scraper_sigue_redirects():
    """INEScraper.session tiene follow_redirects=True (defensa ante redirects de la API INE)."""
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.ine import INEScraper
        scraper = INEScraper()
        assert scraper.session.follow_redirects is True, (
            "INEScraper debe inicializarse con follow_redirects=True"
        )
        scraper.close()


def test_ine_transacciones_usa_serie_etdp3899():
    """
    get_transacciones_inmobiliarias() usa la serie ETDP3899, no la tabla 46964.

    La tabla 46964 no existía en el INE (404 real tras redirect 301 a jsCache).
    La operación ETDP (Id=7) no publica datos municipales — el nivel más fino
    es provincia. Serie ETDP3899 = Madrid provincia, compraventa general.
    """
    content = (
        Path(__file__).parent.parent / "app" / "scrapers" / "ine.py"
    ).read_text(encoding="utf-8")
    assert "ETDP3899" in content, (
        "ine.py debe usar la serie ETDP3899 para transacciones inmobiliarias"
    )
    assert 'get_tabla("46964")' not in content, (
        "ine.py no debe usar get_tabla('46964') — esa tabla no existe en el INE"
    )


@pytest.mark.integration
def test_ine_etdp3899_devuelve_datos_madrid():
    """
    La serie ETDP3899 (Madrid provincia, compraventa general) devuelve datos reales del INE.

    Verifica que get_transacciones_inmobiliarias() retorna un DataFrame con datos anuales
    para al menos los años 2007-2020 (rango estable disponible en la serie ETDP).
    """
    with patch.dict(os.environ, _ENV_MOCK):
        from app.scrapers.ine import INEScraper
        scraper = INEScraper()
        try:
            df = scraper.get_transacciones_inmobiliarias()
            assert not df.empty, (
                "get_transacciones_inmobiliarias() devolvió DataFrame vacío — "
                "la serie ETDP3899 debería tener datos 2007-hoy"
            )
            assert "anno" in df.columns, "El DataFrame debe tener columna 'anno'"
            assert "transacciones" in df.columns, "El DataFrame debe tener columna 'transacciones'"
            assert len(df) >= 10, (
                f"Se esperan al menos 10 años de datos, se obtuvieron {len(df)}"
            )
            # Verificar rango razonable (Madrid provincia: ~41k-85k transacciones/año)
            assert df["transacciones"].max() > 10_000, (
                "El total anual de compraventas en Madrid provincia debe superar 10.000"
            )
        finally:
            scraper.close()


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
