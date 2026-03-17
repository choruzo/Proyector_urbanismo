"""Endpoints para predicciones ML a largo plazo."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.construccion import VisadoEstadistico
from app.models.catastral import ValorSuelo
from app.analytics.predicciones import (
    PrediccionObraNueva,
    PrediccionValorSuelo,
    combinar_historico_prediccion,
)
import pandas as pd

router = APIRouter(prefix="/predicciones", tags=["Predicciones ML"])


@router.get("/obra-nueva")
def predecir_obra_nueva(
    horizonte: int = Query(default=10, ge=1, le=20, description="Años de predicción"),
    db: Session = Depends(get_db),
):
    """
    Proyección de obra nueva y visados a N años vista usando Prophet.
    Incluye datos históricos + predicción con bandas de confianza al 80%.
    """
    datos = (
        db.query(VisadoEstadistico)
        .filter(VisadoEstadistico.trimestre == None)
        .order_by(VisadoEstadistico.anno)
        .all()
    )
    if len(datos) < 5:
        raise HTTPException(
            status_code=422,
            detail="Se necesitan al menos 5 años de datos históricos para generar predicciones."
        )

    df_hist = pd.DataFrame([
        {"anno": d.anno, "num_viviendas": d.numero_viviendas or 0}
        for d in datos
    ])
    df_hist["tipo"] = "real"

    modelo = PrediccionObraNueva(horizonte_anos=horizonte)
    entrenado = modelo.entrenar(df_hist, col_fecha="anno", col_valor="num_viviendas")
    if not entrenado:
        raise HTTPException(status_code=500, detail="Error al entrenar el modelo predictivo.")

    df_pred = modelo.predecir()
    df_combinado = combinar_historico_prediccion(df_hist, df_pred)

    return df_combinado.to_dict(orient="records")


@router.get("/valor-suelo")
def predecir_valor_suelo(
    barrio_id: int | None = Query(default=None),
    horizonte: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Proyección del valor del suelo (€/m²) a N años.
    Si se especifica barrio_id, la predicción es específica para ese barrio.
    """
    query = db.query(ValorSuelo).filter(ValorSuelo.trimestre == None)
    if barrio_id:
        query = query.filter(ValorSuelo.barrio_id == barrio_id)
    datos = query.order_by(ValorSuelo.anno).all()

    if len(datos) < 4:
        raise HTTPException(
            status_code=422,
            detail="Datos históricos insuficientes para este barrio."
        )

    df_hist = pd.DataFrame([
        {"anno": d.anno, "valor_medio_euro_m2": d.valor_medio_euro_m2 or 0}
        for d in datos
    ])
    df_hist["tipo"] = "real"

    modelo = PrediccionValorSuelo(horizonte_anos=horizonte)
    metricas = modelo.entrenar(df_hist, col_anno="anno", col_valor="valor_medio_euro_m2")
    df_pred = modelo.predecir()
    df_combinado = combinar_historico_prediccion(
        df_hist.rename(columns={"valor_medio_euro_m2": "valor_predicho_euro_m2"}),
        df_pred
    )

    return {
        "datos": df_combinado.to_dict(orient="records"),
        "metricas_modelo": metricas,
    }
