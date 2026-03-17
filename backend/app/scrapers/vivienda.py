"""
Scraper para estadísticas de obra nueva del Ministerio de Vivienda y Agenda Urbana.
URL: https://www.mivau.gob.es/vivienda/estadisticas

Datos disponibles públicamente:
  - Visados de obra nueva (Colegio de Arquitectos Técnicos) — serie desde 2000
  - Certificados de fin de obra
  - Compraventas inscritas (Notarial, Registro Propiedad)
  - Precios de vivienda libre
  - Hipotecas sobre vivienda
Granularidad disponible: municipio > provincia > CC.AA.
"""
import httpx
import pandas as pd
from io import StringIO, BytesIO
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings


MIVAU_ESTADISTICAS_BASE = "https://www.mivau.gob.es/vivienda/estadisticas"

# URLs directas de descarga de ficheros CSV/XLS del Ministerio
# Estas URLs se verifican y actualizan según las publicaciones oficiales
URLS_ESTADISTICAS = {
    "visados_nueva_planta": (
        "https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/"
        "construccion/visados_libre.xls"
    ),
    "certificados_fin_obra": (
        "https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/"
        "construccion/certificados_libre.xls"
    ),
    "transacciones_vivienda": (
        "https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/"
        "transacciones/transacciones.xls"
    ),
    "precio_vivienda_libre": (
        "https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/"
        "precios/anuales_ccaa_provmunicipio_libre.xls"
    ),
}


class ViviendaScraper:
    """
    Descarga y procesa las estadísticas oficiales del Ministerio de Vivienda.
    Los ficheros son Excel/CSV públicos actualizados trimestralmente.
    """

    def __init__(self):
        self.session = httpx.Client(
            timeout=120.0,
            follow_redirects=True,
            headers={"User-Agent": "ProyectorUrbanisticoGetafe/0.1"}
        )
        self.municipio = settings.MUNICIPIO_NOMBRE
        self.codigo_ine = settings.MUNICIPIO_CODIGO_INE

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=5, max=30))
    def _descargar_fichero(self, url: str) -> bytes | None:
        """Descarga un fichero del servidor del Ministerio."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error al descargar {url}: {e}")
            return None

    def get_visados_getafe(self) -> pd.DataFrame:
        """
        Descarga datos de visados de obra nueva y filtra por Getafe.
        Devuelve serie histórica anual/trimestral.
        """
        contenido = self._descargar_fichero(URLS_ESTADISTICAS["visados_nueva_planta"])
        if contenido is None:
            logger.warning("No se pudo descargar fichero de visados")
            return pd.DataFrame()

        try:
            df = pd.read_excel(BytesIO(contenido), sheet_name=None)
            # El fichero tiene varias hojas; buscar la de municipios
            for hoja_nombre, hoja_df in df.items():
                if "municipio" in hoja_nombre.lower() or "municipal" in hoja_nombre.lower():
                    # Filtrar por Getafe (por nombre o código INE)
                    mask = (
                        hoja_df.apply(lambda col: col.astype(str).str.contains("Getafe", case=False)).any(axis=1) |
                        hoja_df.apply(lambda col: col.astype(str).str.contains(self.codigo_ine)).any(axis=1)
                    )
                    resultado = hoja_df[mask]
                    if not resultado.empty:
                        logger.info(f"Visados Getafe: {len(resultado)} registros encontrados en hoja '{hoja_nombre}'")
                        return resultado
            logger.warning("No se encontraron datos de Getafe en el fichero de visados")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error procesando fichero de visados: {e}")
            return pd.DataFrame()

    def get_precios_vivienda_getafe(self) -> pd.DataFrame:
        """
        Descarga precios de vivienda libre por municipio del Ministerio.
        Fuente: Encuesta de precios del Mº de Vivienda (trimestral).
        """
        contenido = self._descargar_fichero(URLS_ESTADISTICAS["precio_vivienda_libre"])
        if contenido is None:
            return pd.DataFrame()

        try:
            df = pd.read_excel(BytesIO(contenido), skiprows=5)  # cabeceras suelen tener filas vacías
            # Buscar Getafe
            mask = df.apply(lambda col: col.astype(str).str.contains("Getafe", case=False)).any(axis=1)
            resultado = df[mask]
            logger.info(f"Precios vivienda Getafe: {len(resultado)} registros")
            return resultado
        except Exception as e:
            logger.error(f"Error procesando fichero de precios: {e}")
            return pd.DataFrame()

    def close(self):
        self.session.close()
