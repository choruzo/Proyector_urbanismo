"""Endpoints para el mapa interactivo de valor del suelo por barrios."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.catastral import Barrio, ValorSuelo
from geoalchemy2.functions import ST_AsGeoJSON
import json

router = APIRouter(prefix="/mapa", tags=["Mapa"])


@router.get("/barrios/geojson")
def get_barrios_geojson(
    anno: int = Query(default=2024, ge=2001, le=2030),
    db: Session = Depends(get_db),
):
    """
    GeoJSON de los barrios de Getafe con valor del suelo para el año dado.
    Listo para pintar directamente en React-Leaflet con coropletas.
    """
    resultados = (
        db.query(
            Barrio.id,
            Barrio.nombre,
            Barrio.distrito,
            Barrio.superficie_m2,
            ST_AsGeoJSON(Barrio.geom).label("geom_json"),
            ValorSuelo.valor_medio_euro_m2,
            ValorSuelo.anno,
        )
        .outerjoin(
            ValorSuelo,
            (ValorSuelo.barrio_id == Barrio.id) & (ValorSuelo.anno == anno) & (ValorSuelo.trimestre == None)
        )
        .all()
    )

    features = []
    for r in resultados:
        if r.geom_json is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": json.loads(r.geom_json),
            "properties": {
                "id": r.id,
                "nombre": r.nombre,
                "distrito": r.distrito,
                "superficie_m2": r.superficie_m2,
                "valor_euro_m2": r.valor_medio_euro_m2,
                "anno": r.anno or anno,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {"anno": anno, "num_barrios": len(features)},
    }


@router.get("/barrios/revalorizacion")
def get_revalorizacion_barrios(
    anno_inicio: int = Query(default=2015, ge=2001),
    anno_fin: int = Query(default=2024, ge=2001),
    db: Session = Depends(get_db),
):
    """
    Porcentaje de revalorización del suelo por barrio entre dos años.
    Útil para detectar zonas con mayor crecimiento de valor.
    """
    valores_inicio = {
        v.barrio_id: v.valor_medio_euro_m2
        for v in db.query(ValorSuelo).filter(ValorSuelo.anno == anno_inicio, ValorSuelo.trimestre == None).all()
        if v.valor_medio_euro_m2 and v.valor_medio_euro_m2 > 0
    }
    valores_fin = {
        v.barrio_id: v.valor_medio_euro_m2
        for v in db.query(ValorSuelo).filter(ValorSuelo.anno == anno_fin, ValorSuelo.trimestre == None).all()
    }
    barrios = db.query(Barrio).all()
    resultado = []
    for barrio in barrios:
        v_ini = valores_inicio.get(barrio.id)
        v_fin = valores_fin.get(barrio.id)
        if v_ini and v_fin:
            revalorizacion_pct = ((v_fin - v_ini) / v_ini) * 100
        else:
            revalorizacion_pct = None
        resultado.append({
            "barrio_id": barrio.id,
            "nombre": barrio.nombre,
            "distrito": barrio.distrito,
            "valor_inicio": v_ini,
            "valor_fin": v_fin,
            "revalorizacion_pct": round(revalorizacion_pct, 2) if revalorizacion_pct else None,
        })
    return sorted(resultado, key=lambda x: x["revalorizacion_pct"] or 0, reverse=True)
