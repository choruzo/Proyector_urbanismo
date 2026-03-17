"""
Módulo de predicciones urbanísticas con ML.
Modelos implementados:
  - Prophet (Meta): predicción de series temporales (obra nueva, precios)
  - Regresión polinómica (scikit-learn): tendencias de valor del suelo
  - ARIMA (statsmodels): como modelo alternativo de comparación

Horizonte de predicción: 5-10 años vista.
"""
import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet no disponible. Instalar con: pip install prophet")

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score


class PrediccionObraNueva:
    """
    Predice la evolución de visados y obra nueva para Getafe a 5-10 años.
    Usa Prophet para capturar tendencias y estacionalidad anual.
    """

    def __init__(self, horizonte_anos: int = 10):
        self.horizonte = horizonte_anos
        self.model = None

    def entrenar(self, df: pd.DataFrame, col_fecha: str = "anno", col_valor: str = "num_viviendas") -> bool:
        """
        Entrena el modelo con datos históricos.
        df debe tener columnas de fecha (año) y valor numérico.
        """
        if not PROPHET_AVAILABLE:
            logger.error("Prophet no disponible para entrenamiento")
            return False

        if df.empty or len(df) < 5:
            logger.warning("Datos insuficientes para entrenar modelo de obra nueva (mínimo 5 años)")
            return False

        # Prophet requiere columnas 'ds' (datetime) y 'y' (valor)
        df_prophet = pd.DataFrame({
            "ds": pd.to_datetime(df[col_fecha].astype(str) + "-01-01"),
            "y": df[col_valor].astype(float),
        }).dropna()

        self.model = Prophet(
            yearly_seasonality=False,     # datos anuales, no hay estacionalidad intraanual
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.1,  # flexibilidad moderada a cambios de tendencia
            interval_width=0.80,          # intervalo de confianza del 80%
        )

        try:
            self.model.fit(df_prophet)
            logger.info(f"Modelo Prophet entrenado con {len(df_prophet)} años de datos")
            return True
        except Exception as e:
            logger.error(f"Error entrenando Prophet: {e}")
            return False

    def predecir(self) -> pd.DataFrame:
        """
        Genera predicciones para los próximos N años.
        Devuelve DataFrame con: anno, prediccion, lower_80, upper_80.
        """
        if self.model is None:
            logger.error("Modelo no entrenado. Llamar a entrenar() primero.")
            return pd.DataFrame()

        # Crear fechas futuras (frecuencia anual)
        anno_ultimo = datetime.now().year
        fechas_futuras = pd.DataFrame({
            "ds": pd.date_range(
                start=f"{anno_ultimo + 1}-01-01",
                periods=self.horizonte,
                freq="YS"
            )
        })

        forecast = self.model.predict(fechas_futuras)

        resultado = pd.DataFrame({
            "anno": forecast["ds"].dt.year,
            "prediccion": forecast["yhat"].clip(lower=0),
            "lower_80": forecast["yhat_lower"].clip(lower=0),
            "upper_80": forecast["yhat_upper"].clip(lower=0),
            "tipo": "prediccion",
        })

        logger.info(f"Predicciones generadas para {self.horizonte} años")
        return resultado


class PrediccionValorSuelo:
    """
    Proyecta la evolución del valor del suelo por barrio.
    Usa regresión polinómica + tendencia histórica de catastro.
    """

    def __init__(self, grado_polinomio: int = 2, horizonte_anos: int = 10):
        self.grado = grado_polinomio
        self.horizonte = horizonte_anos
        self.pipeline: Pipeline | None = None
        self.anno_base: int = 2001

    def entrenar(self, df: pd.DataFrame, col_anno: str = "anno", col_valor: str = "valor_medio_euro_m2") -> dict:
        """
        Entrena modelo de regresión por barrio.
        df debe tener columnas de año y valor €/m².
        Devuelve métricas del modelo.
        """
        df_clean = df[[col_anno, col_valor]].dropna()
        if len(df_clean) < 4:
            logger.warning("Datos insuficientes para predicción de valor del suelo")
            return {}

        X = df_clean[col_anno].values.reshape(-1, 1)
        y = df_clean[col_valor].values

        self.pipeline = Pipeline([
            ("poly", PolynomialFeatures(degree=self.grado, include_bias=False)),
            ("reg", LinearRegression()),
        ])
        self.pipeline.fit(X, y)

        y_pred = self.pipeline.predict(X)
        metricas = {
            "mae": float(mean_absolute_error(y, y_pred)),
            "r2": float(r2_score(y, y_pred)),
            "n_samples": len(y),
        }
        logger.info(f"Modelo valor suelo entrenado: R²={metricas['r2']:.3f}, MAE={metricas['mae']:.1f}€/m²")
        return metricas

    def predecir(self, anno_inicio: int | None = None) -> pd.DataFrame:
        """Genera proyecciones de valor del suelo."""
        if self.pipeline is None:
            return pd.DataFrame()

        if anno_inicio is None:
            anno_inicio = datetime.now().year + 1

        annos_futuros = np.arange(anno_inicio, anno_inicio + self.horizonte).reshape(-1, 1)
        predicciones = self.pipeline.predict(annos_futuros).clip(min=0)

        return pd.DataFrame({
            "anno": annos_futuros.flatten(),
            "valor_predicho_euro_m2": predicciones,
            "tipo": "prediccion",
        })


def combinar_historico_prediccion(historico: pd.DataFrame, prediccion: pd.DataFrame,
                                   col_anno: str = "anno") -> pd.DataFrame:
    """
    Une datos históricos y predicción en un único DataFrame para visualización.
    Los históricos se marcan como 'real', las predicciones como 'prediccion'.
    """
    if "tipo" not in historico.columns:
        historico = historico.copy()
        historico["tipo"] = "real"

    resultado = pd.concat([historico, prediccion], ignore_index=True)
    return resultado.sort_values(col_anno).reset_index(drop=True)
