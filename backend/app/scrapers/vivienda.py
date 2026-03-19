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

# URLs directas de descarga del Boletín Estadístico del Ministerio de Fomento/MIVAU.
# NOTA: Las URLs antiguas de mivau.gob.es/recursos_mivau/ devuelven HTTP 403 desde 2024.
#       Los ficheros estadísticos están ahora en apps.fomento.gob.es/Boletinonline/sedal/
#       Los datos son a nivel de Provincia de Madrid (no municipal).
URLS_ESTADISTICAS = {
    # Provincia de Madrid — Obra nueva: nº viviendas y superficie media (serie 2001-hoy)
    "visados_madrid_viviendas": (
        "https://apps.fomento.gob.es/Boletinonline/sedal/09032810.XLS"
    ),
    # Provincia de Madrid — Obra nueva y certificados: nº edificios
    "visados_madrid_edificios": (
        "https://apps.fomento.gob.es/Boletinonline/sedal/09032820.XLS"
    ),
    # Nacional — Viviendas libres iniciadas: serie anual
    "viviendas_libres_anual": (
        "https://apps.fomento.gob.es/BoletinOnline2/sedal/32200500.XLS"
    ),
    # Nacional — Viviendas libres terminadas: serie anual
    "viviendas_libres_terminadas": (
        "https://apps.fomento.gob.es/BoletinOnline2/sedal/32201000.XLS"
    ),
    # Provincia de Madrid — Precio medio €/m² vivienda libre tasada
    # NOTA: MIVAU no publica precios en el formato SEDAL (apps.fomento.gob.es/Boletinonline/sedal/).
    # El dato de precio se publica en el Portal Estadístico MIVAU (navegación manual necesaria).
    # URL placeholder — actualizar cuando se identifique la URL de descarga directa.
    # Ref: https://www.mivau.gob.es/vivienda/estadisticas/precio-vivienda-libre
    "precios_madrid_vivienda_libre": (
        "https://apps.fomento.gob.es/BoletinOnline2/sedal/09110010.XLS"
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
        Descarga datos de visados de obra nueva de la provincia de Madrid.

        Fuente actualizada: apps.fomento.gob.es (antiguo mivau.gob.es devuelve 403).
        El fichero es provincial (Madrid), no municipal: no es posible filtrar por Getafe.
        Devuelve DataFrame con columnas [anno, numero_viviendas, fuente].

        Estructura real del fichero SEDAL (09032810.XLS):
          - Filas 0-7:  metadatos / texto (título, provincia)
          - Filas 8-12: resumen anual de los últimos 5 años (col0=año, col2=NaN, col4=total)
          - Filas 14+:  desglose mensual (col0=año del primer mes, col2=mes, col4=viviendas)
          El histórico completo (desde 1991) está en el desglose mensual → se agrega por año.
        """
        contenido = self._descargar_fichero(URLS_ESTADISTICAS["visados_madrid_viviendas"])
        if contenido is None:
            logger.warning("No se pudo descargar fichero de visados (fomento.gob.es)")
            return pd.DataFrame()

        try:
            df_raw = pd.read_excel(BytesIO(contenido), sheet_name=0, header=None)

            # Abreviaturas de mes usadas por Fomento/SEDAL
            MESES = {"Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"}

            # Recorrer filas: el año aparece en col0 sólo en el primer mes de cada año.
            # col2 contiene la abreviatura del mes; col4 contiene el número de viviendas.
            year_totals: dict[int, float] = {}
            current_year: int | None = None

            for _, row in df_raw.iterrows():
                c0 = row.iloc[0]
                c2 = row.iloc[2]
                c4 = row.iloc[4]

                # Detectar cambio de año
                if isinstance(c0, (int, float)) and not pd.isna(c0):
                    try:
                        y = int(c0)
                        if 1990 < y < 2030:
                            current_year = y
                    except (TypeError, ValueError):
                        pass

                # Acumular viviendas del mes
                if current_year and isinstance(c2, str) and c2.strip() in MESES:
                    if pd.notna(c4):
                        year_totals[current_year] = year_totals.get(current_year, 0.0) + float(c4)

            if not year_totals:
                logger.warning("No se encontraron datos mensuales de viviendas en el fichero SEDAL")
                return pd.DataFrame()

            registros = [
                {
                    "anno": anno,
                    "numero_viviendas": int(round(total)),
                    "fuente": "mivau_fomento_provincia",
                }
                for anno, total in sorted(year_totals.items())
                if total > 0
            ]

            resultado = pd.DataFrame(registros)
            annos_rango = f"{resultado['anno'].min()}-{resultado['anno'].max()}"
            logger.info(
                f"Visados Madrid provincia: {len(resultado)} años ({annos_rango}) "
                f"descargados de fomento.gob.es"
            )
            return resultado

        except Exception as e:
            logger.error(f"Error procesando fichero de visados fomento: {e}")
            return pd.DataFrame()

    def get_precios_vivienda_getafe(self) -> pd.DataFrame:
        """
        Descarga la serie anual de viviendas libres iniciadas a nivel nacional.
        Fuente: apps.fomento.gob.es/BoletinOnline2 (serie 32200500).
        Se usa como proxy de evolución del mercado residencial.
        """
        contenido = self._descargar_fichero(URLS_ESTADISTICAS["viviendas_libres_anual"])
        if contenido is None:
            return pd.DataFrame()

        try:
            df_raw = pd.read_excel(BytesIO(contenido), sheet_name=0, header=None)

            # Mismo patrón de parseo: buscar fila con años
            header_row = None
            for i, row in df_raw.iterrows():
                nums = [v for v in row if isinstance(v, (int, float)) and 1990 < v < 2030]
                if len(nums) >= 3:
                    header_row = i
                    break

            if header_row is None:
                return pd.DataFrame()

            annos = [int(v) for v in df_raw.iloc[header_row]
                     if isinstance(v, (int, float)) and 1990 < v < 2030]
            logger.info(f"Viviendas libres nacional: {len(annos)} años ({min(annos)}-{max(annos)})")
            return df_raw

        except Exception as e:
            logger.error(f"Error procesando fichero viviendas libres: {e}")
            return pd.DataFrame()

    def get_precio_m2_vivienda_madrid(self) -> float | None:
        """
        Descarga el precio medio €/m² de vivienda libre tasada en la provincia de Madrid
        desde el boletín estadístico SEDAL del Ministerio de Fomento/MIVAU.

        URL candidata: 09110010.XLS (09=Madrid provincia, 11=precios tasación,
        0010=vivienda libre media). Sigue el mismo patrón de códigos SEDAL que las
        series de visados (09032810.XLS).

        Estrategia de parseo: escanea todas las celdas numéricas en busca de valores
        en el rango [800, 8000] €/m², que discrimina automáticamente los precios
        reales de los recuentos de viviendas (que son decenas de miles) y otros
        datos de metadatos.

        Returns:
            Precio más reciente encontrado (float), o None si el fichero no está
            disponible o no contiene datos en el rango esperado.
            El caller en initial_load.py usará 1800.0 €/m² como fallback.
        """
        contenido = self._descargar_fichero(URLS_ESTADISTICAS["precios_madrid_vivienda_libre"])
        if contenido is None:
            logger.warning("SEDAL precios: fichero no disponible (09110010.XLS)")
            return None

        try:
            df_raw = pd.read_excel(BytesIO(contenido), sheet_name=0, header=None)

            # Buscar pares (año, precio€/m²) escaneando todas las filas
            precio_por_anno: list[tuple[int, float]] = []
            current_year: int | None = None

            for _, row in df_raw.iterrows():
                c0 = row.iloc[0]

                # Detectar cambio de año en la primera columna
                if isinstance(c0, (int, float)) and not pd.isna(c0):
                    try:
                        y = int(c0)
                        if 1990 < y < 2030:
                            current_year = y
                    except (TypeError, ValueError):
                        pass

                if current_year is None:
                    continue

                # Buscar en el resto de la fila valores en rango plausible €/m²
                for val in row.iloc[1:]:
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        v = float(val)
                        if 800.0 < v < 8_000.0:
                            precio_por_anno.append((current_year, v))
                            break  # un precio por fila es suficiente

            if not precio_por_anno:
                logger.warning(
                    "SEDAL precios: no se encontraron valores en rango €/m² [800-8000]"
                    " — el fichero puede contener datos distintos a precios"
                )
                return None

            # Usar el valor del año más reciente disponible
            precio_por_anno.sort(key=lambda t: t[0], reverse=True)
            anno_ref, precio = precio_por_anno[0]
            logger.info(
                f"SEDAL precios Madrid provincia: {precio:.0f} €/m² (año {anno_ref})"
                f" — {len(precio_por_anno)} años disponibles"
            )
            return precio

        except Exception as e:
            logger.error(f"Error procesando SEDAL precios (09110010.XLS): {e}")
            return None

    def close(self):
        self.session.close()
