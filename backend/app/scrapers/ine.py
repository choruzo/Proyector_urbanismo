"""
Scraper para la API JSON del INE (Instituto Nacional de Estadística).
Documentación: https://www.ine.es/dyngs/DataLab/es/manual.htm?cid=1259945948443

Operaciones relevantes para urbanismo en Getafe (código INE: 28065):
  - 30062: Estadística continua de población (padrón)
  - 10058: Estadísticas de transmisiones de derechos de propiedad (compraventas)
  - Encuesta de Condiciones de Vida
  - Estadísticas de construcción (permisos de obra)
"""
import httpx
import pandas as pd
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings


INE_API_BASE = "https://servicios.ine.es/wstempus/js"


class INEScraper:
    """
    Cliente para la API JSON del INE.
    API pública, sin autenticación, con rate limiting moderado.
    """

    def __init__(self):
        self.municipio_ine = settings.MUNICIPIO_CODIGO_INE  # 28065 = Getafe
        self.session = httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "ProyectorUrbanisticoGetafe/0.1"}
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def get_serie(self, codigo_serie: str) -> list[dict]:
        """
        Obtiene los datos de una serie temporal del INE.
        Ejemplo: ET28065 = estadística de transacciones en Getafe
        """
        url = f"{INE_API_BASE}/ES/DATOS_SERIE/{codigo_serie}"
        params = {"date": f"{settings.YEAR_START}0101:{settings.YEAR_END}1231", "det": 0}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("Data", [])
        except httpx.HTTPError as e:
            logger.error(f"Error al obtener serie INE {codigo_serie}: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def get_tabla(self, id_tabla: str) -> list[dict]:
        """Obtiene los datos completos de una tabla INE."""
        url = f"{INE_API_BASE}/ES/DATOS_TABLA/{id_tabla}"
        try:
            response = self.session.get(url, timeout=120.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error al obtener tabla INE {id_tabla}: {e}")
            return []

    def get_poblacion_getafe(self) -> pd.DataFrame:
        """
        Obtiene la serie histórica de población de Getafe desde el padrón municipal.
        Tabla INE: Padrón municipal de habitantes — series por municipio.
        """
        # Serie de población total Getafe
        datos = self.get_serie("DPOB28004")  # ajustar código según disponibilidad
        if not datos:
            logger.warning("No se obtuvieron datos de población INE")
            return pd.DataFrame()
        df = pd.DataFrame(datos)
        df = df.rename(columns={"T3_Periodo": "anno", "Valor": "poblacion"})
        df["anno"] = pd.to_numeric(df["anno"], errors="coerce")
        df["poblacion"] = pd.to_numeric(df["poblacion"], errors="coerce")
        return df[df["anno"] >= settings.YEAR_START].sort_values("anno")

    def get_transacciones_inmobiliarias(self) -> pd.DataFrame:
        """
        Estadísticas de transmisiones de derechos de propiedad (compraventas).
        Fuente: INE — Estadística de Transmisiones de Derechos de la Propiedad.
        """
        datos = self.get_tabla("46964")  # ID tabla transacciones por municipio
        if not datos:
            logger.warning("No se obtuvieron datos de transacciones INE")
            return pd.DataFrame()
        df = pd.DataFrame(datos)
        # Filtrar por Getafe
        if "Nombre" in df.columns:
            df = df[df["Nombre"].str.contains("Getafe", case=False, na=False)]
        return df

    def get_indice_precios_vivienda(self) -> pd.DataFrame:
        """
        Índice de Precios de Vivienda (IPV) — serie nacional y de Madrid.
        Proxy para estimar evolución de precios en Getafe.
        """
        datos = self.get_serie("IPV761")  # IPV vivienda libre nueva y usada
        if not datos:
            return pd.DataFrame()
        return pd.DataFrame(datos)

    def close(self):
        self.session.close()
