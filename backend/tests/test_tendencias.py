"""
Tests de integración para los endpoints de Tendencias.

Requieren acceso a la BD PostgreSQL con datos cargados (initial_load ejecutado).
Ejecutar con:
    pytest tests/test_tendencias.py -v
    pytest tests/test_tendencias.py -v -m "not integration"  # solo tests estructurales
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/tendencias/kpis
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_kpis_devuelve_200():
    response = client.get("/api/v1/tendencias/kpis")
    assert response.status_code == 200


@pytest.mark.integration
def test_kpis_estructura_y_datos_reales():
    response = client.get("/api/v1/tendencias/kpis")
    data = response.json()
    # Campos obligatorios presentes
    assert "anno" in data
    assert "valor_suelo_medio_euro_m2" in data
    assert "viviendas_ultimo_anno" in data
    assert "variacion_valor_pct" in data
    # Con datos cargados no deben ser null
    assert data["valor_suelo_medio_euro_m2"] is not None
    assert data["viviendas_ultimo_anno"] is not None
    assert data["variacion_valor_pct"] is not None


# ---------------------------------------------------------------------------
# GET /api/v1/tendencias/obra-nueva
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_obra_nueva_serie_completa():
    response = client.get("/api/v1/tendencias/obra-nueva?anno_inicio=1991&anno_fin=2025")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 20  # al menos 20 años con datos
    annos = [d["anno"] for d in data]
    assert annos == sorted(annos)  # ordenado cronológicamente


@pytest.mark.integration
def test_obra_nueva_filtro_annos():
    response = client.get("/api/v1/tendencias/obra-nueva?anno_inicio=2010&anno_fin=2015")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 6
    for item in data:
        assert 2010 <= item["anno"] <= 2015
        assert "num_viviendas" in item


# ---------------------------------------------------------------------------
# GET /api/v1/tendencias/valor-suelo
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_valor_suelo_global():
    response = client.get("/api/v1/tendencias/valor-suelo")
    assert response.status_code == 200
    data = response.json()
    # 12 barrios × 26 años = 312 registros
    assert len(data) == 312
    for item in data:
        assert item["valor_medio_euro_m2"] is not None
        assert item["valor_medio_euro_m2"] > 0


@pytest.mark.integration
def test_valor_suelo_por_barrio():
    response = client.get("/api/v1/tendencias/valor-suelo?barrio_id=1")
    assert response.status_code == 200
    data = response.json()
    # Un barrio × 26 años = 26 registros
    assert len(data) == 26
    assert all(d["barrio_id"] == 1 for d in data)


# ---------------------------------------------------------------------------
# GET /api/v1/tendencias/transacciones
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_transacciones_serie_completa():
    response = client.get("/api/v1/tendencias/transacciones")
    assert response.status_code == 200
    data = response.json()
    # 22 años de datos (2004-2025)
    assert len(data) == 22
    annos = [d["anno"] for d in data]
    assert annos == sorted(annos)
    for item in data:
        assert item["num_transacciones"] > 0
        assert item["fuente"] == "ine"
