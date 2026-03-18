"""Endpoints para tendencias urbanísticas históricas y KPIs del overview."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.construccion import VisadoEstadistico
from app.models.catastral import ValorSuelo
from app.models.ine import DatoINE

router = APIRouter(prefix="/tendencias", tags=["Tendencias"])


@router.get("/kpis")
def get_kpis_overview(db: Session = Depends(get_db)):
    """Resumen ejecutivo: KPIs principales del año en curso."""
    anno_actual = 2026

    # Último año con viviendas registradas (solo valores anuales)
    ultimo_visado = (
        db.query(VisadoEstadistico)
        .filter(
            VisadoEstadistico.trimestre.is_(None),
            VisadoEstadistico.numero_viviendas.isnot(None),
        )
        .order_by(VisadoEstadistico.anno.desc())
        .first()
    )

    # Valor medio del suelo del último año disponible (media de todos los barrios)
    ultimo_valor = (
        db.query(func.avg(ValorSuelo.valor_medio_euro_m2))
        .filter(
            ValorSuelo.trimestre.is_(None),
            ValorSuelo.anno == (
                db.query(func.max(ValorSuelo.anno))
                .filter(ValorSuelo.trimestre.is_(None))
                .scalar_subquery()
            ),
        )
        .scalar()
    )

    # Variación interanual del valor del suelo (último año vs anterior)
    annos_con_datos = (
        db.query(ValorSuelo.anno)
        .filter(ValorSuelo.trimestre.is_(None))
        .distinct()
        .order_by(ValorSuelo.anno.desc())
        .limit(2)
        .all()
    )
    variacion_valor = None
    if len(annos_con_datos) == 2:
        anno_prev = annos_con_datos[1][0]
        valor_prev = (
            db.query(func.avg(ValorSuelo.valor_medio_euro_m2))
            .filter(ValorSuelo.trimestre.is_(None), ValorSuelo.anno == anno_prev)
            .scalar()
        )
        if valor_prev and ultimo_valor:
            variacion_valor = round((ultimo_valor - valor_prev) / valor_prev * 100, 1)

    return {
        "anno": anno_actual,
        "anno_ultimo_visado": ultimo_visado.anno if ultimo_visado else None,
        "visados_ultimo_anno": ultimo_visado.numero_visados if ultimo_visado else None,
        "viviendas_ultimo_anno": ultimo_visado.numero_viviendas if ultimo_visado else None,
        "valor_suelo_medio_euro_m2": round(ultimo_valor, 0) if ultimo_valor else None,
        "variacion_valor_pct": variacion_valor,
    }


@router.get("/obra-nueva")
def get_tendencia_obra_nueva(
    anno_inicio: int = Query(default=2001, ge=1990, le=2030),
    anno_fin: int = Query(default=2026, ge=1990, le=2030),
    db: Session = Depends(get_db),
):
    """Serie histórica de visados y viviendas nuevas en Getafe."""
    datos = (
        db.query(VisadoEstadistico)
        .filter(
            VisadoEstadistico.anno >= anno_inicio,
            VisadoEstadistico.anno <= anno_fin,
            VisadoEstadistico.trimestre.is_(None),
        )
        .order_by(VisadoEstadistico.anno)
        .all()
    )
    return [
        {
            "anno": d.anno,
            "num_visados": d.numero_visados,
            "num_viviendas": d.numero_viviendas,
            "superficie_m2": d.superficie_m2,
            "presupuesto_total": d.presupuesto_total,
            "tipo_obra": d.tipo_obra,
        }
        for d in datos
    ]


@router.get("/valor-suelo")
def get_tendencia_valor_suelo(
    anno_inicio: int = Query(default=2001, ge=2001, le=2030),
    anno_fin: int = Query(default=2026, ge=2001, le=2030),
    barrio_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Serie histórica de valor del suelo (€/m²) en Getafe, global o por barrio."""
    query = db.query(ValorSuelo).filter(
        ValorSuelo.anno >= anno_inicio,
        ValorSuelo.anno <= anno_fin,
        ValorSuelo.trimestre.is_(None),
    )
    if barrio_id:
        query = query.filter(ValorSuelo.barrio_id == barrio_id)
    datos = query.order_by(ValorSuelo.anno).all()
    return [
        {
            "anno": d.anno,
            "barrio_id": d.barrio_id,
            "valor_medio_euro_m2": d.valor_medio_euro_m2,
            "valor_catastral_medio": d.valor_catastral_medio,
            "fuente": d.fuente,
        }
        for d in datos
    ]


@router.get("/transacciones")
def get_tendencia_transacciones(
    anno_inicio: int = Query(default=2001, ge=2001, le=2030),
    anno_fin: int = Query(default=2026, ge=2001, le=2030),
    db: Session = Depends(get_db),
):
    """Serie histórica de compraventas de vivienda en Getafe (fuente: INE)."""
    datos = (
        db.query(DatoINE)
        .filter(
            DatoINE.indicador == "transacciones",
            DatoINE.anno >= anno_inicio,
            DatoINE.anno <= anno_fin,
            DatoINE.trimestre.is_(None),
        )
        .order_by(DatoINE.anno)
        .all()
    )
    return [
        {"anno": d.anno, "num_transacciones": int(d.valor), "fuente": "ine"}
        for d in datos
    ]
