"""Endpoints para alertas BOCM/BOE y proyectos EMSV."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.alertas import Alerta, TipoAlerta, FuenteAlerta

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("/")
def get_alertas(
    dias: int = Query(default=30, ge=1, le=365, description="Alertas de los últimos N días"),
    tipo: TipoAlerta | None = Query(default=None),
    fuente: FuenteAlerta | None = Query(default=None),
    leida: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista de alertas urbanísticas recientes, con filtros opcionales."""
    fecha_desde = date.today() - timedelta(days=dias)
    query = db.query(Alerta).filter(Alerta.fecha_publicacion >= fecha_desde)
    if tipo:
        query = query.filter(Alerta.tipo == tipo)
    if fuente:
        query = query.filter(Alerta.fuente == fuente)
    if leida is not None:
        query = query.filter(Alerta.leida == leida)
    alertas = query.order_by(Alerta.fecha_publicacion.desc()).limit(100).all()
    return [
        {
            "id": a.id,
            "titulo": a.titulo,
            "descripcion": a.descripcion,
            "tipo": a.tipo,
            "fuente": a.fuente,
            "url": a.url,
            "fecha_publicacion": a.fecha_publicacion,
            "importe_euros": a.importe_euros,
            "organismo_contratante": a.organismo_contratante,
            "leida": a.leida,
            "relevancia_score": a.relevancia_score,
        }
        for a in alertas
    ]


@router.get("/resumen")
def get_resumen_alertas(db: Session = Depends(get_db)):
    """Conteo de alertas por tipo y fuente en los últimos 30 días."""
    from sqlalchemy import func
    fecha_desde = date.today() - timedelta(days=30)
    totales = (
        db.query(Alerta.tipo, Alerta.fuente, func.count(Alerta.id).label("total"))
        .filter(Alerta.fecha_publicacion >= fecha_desde)
        .group_by(Alerta.tipo, Alerta.fuente)
        .all()
    )
    return [{"tipo": t.tipo, "fuente": t.fuente, "total": t.total} for t in totales]


@router.patch("/{alerta_id}/marcar-leida")
def marcar_alerta_leida(alerta_id: int, db: Session = Depends(get_db)):
    """Marca una alerta como leída."""
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not alerta:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alerta.leida = True
    db.commit()
    return {"ok": True}
