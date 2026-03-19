"""
Scraper para la API del Catastro (Dirección General del Catastro).
Documentación oficial: https://www.catastro.meh.es/esp/sede_servicios_webServices.asp

Servicios usados:
  - Consulta de datos de un inmueble por referencia catastral (OVCCallejero)
  - Consulta de coordenadas (OVCCoordenadas)
  - Descarga de cartografía INSPIRE (WFS)
"""
import httpx
import xml.etree.ElementTree as ET
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings


CATASTRO_BASE_URL = "https://ovc.catastro.meh.es"
CATASTRO_WFS_URL = "https://www.catastro.meh.es/INSPIRE/wfs"


class CatastroScraper:
    """
    Cliente para la API REST del Catastro español.
    Todos los endpoints son públicos y no requieren autenticación.
    """

    def __init__(self):
        self.municipio = settings.MUNICIPIO_NOMBRE
        self.codigo_municipio = settings.MUNICIPIO_CODIGO_CATASTRO
        self.provincia_codigo = settings.PROVINCIA_CODIGO
        self.session = httpx.Client(timeout=30.0, headers={"User-Agent": "ProyectorUrbanisticoGetafe/0.1"})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_inmueble_por_referencia(self, referencia_catastral: str) -> dict | None:
        """Obtiene datos de un inmueble por su referencia catastral."""
        url = f"{CATASTRO_BASE_URL}/ovcservweb/ovcswlocalizacionrc/ovccoordenadas.asmx/Consulta_RCCOOR"
        params = {"RC": referencia_catastral}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return self._parse_coordenadas_response(response.text)
        except httpx.HTTPError as e:
            logger.error(f"Error al consultar catastro RC={referencia_catastral}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_inmuebles_por_calle(self, nombre_via: str, numero: str = "") -> list[dict]:
        """
        Consulta inmuebles de una calle del municipio de Getafe.
        Endpoint: OVCCallejero — Consulta_DNPPP
        """
        url = f"{CATASTRO_BASE_URL}/ovcservweb/ovcswlocalizacionrc/ovccallejerocodigos.asmx/ConsultaMunicipio"
        params = {
            "Provincia": "Madrid",
            "Municipio": self.municipio,
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return self._parse_municipio_response(response.text)
        except httpx.HTTPError as e:
            logger.error(f"Error al consultar callejero Getafe: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_poligono_municipio_wfs(self) -> dict | None:
        """
        Descarga la capa de parcelas del municipio vía WFS INSPIRE del Catastro.
        Devuelve GeoJSON con las parcelas de Getafe.
        Nota: puede ser una petición pesada, usar sólo en carga inicial.
        """
        url = CATASTRO_WFS_URL
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": "CP:CadastralParcel",
            "COUNT": "1000",
            "CQL_FILTER": f"NationalCadastralReference LIKE '{self.codigo_municipio}%'",
            "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326",
        }
        try:
            response = self.session.get(url, params=params, timeout=120.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error al descargar WFS catastro: {e}")
            return None

    def _parse_coordenadas_response(self, xml_text: str) -> dict | None:
        """Parsea la respuesta XML del endpoint de coordenadas."""
        try:
            root = ET.fromstring(xml_text)
            ns = {"c": "http://www.catastro.meh.es/"}
            pc = root.find(".//c:pc", ns)
            if pc is None:
                return None
            return {
                "referencia_catastral": (pc.findtext("c:pc1", namespaces=ns) or "") + (pc.findtext("c:pc2", namespaces=ns) or ""),
                "latitud": float(root.findtext(".//c:lat", namespaces=ns) or 0),
                "longitud": float(root.findtext(".//c:lon", namespaces=ns) or 0),
            }
        except Exception as e:
            logger.error(f"Error parseando respuesta catastro: {e}")
            return None

    def _parse_municipio_response(self, xml_text: str) -> list[dict]:
        """Parsea respuesta XML de consulta de municipio."""
        try:
            root = ET.fromstring(xml_text)
            ns = {"c": "http://www.catastro.meh.es/"}
            resultados = []
            for muni in root.findall(".//c:muni", ns):
                resultados.append({
                    "codigo_municipio": muni.findtext("c:cm", namespaces=ns),
                    "nombre": muni.findtext("c:nm", namespaces=ns),
                    "codigo_provincia": muni.findtext("c:cp", namespaces=ns),
                })
            return resultados
        except Exception as e:
            logger.error(f"Error parseando respuesta municipio catastro: {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=10))
    def get_zonas_catastrales_wfs(self) -> dict | None:
        """
        Descarga la capa de zonas catastrales (CP:CadastralZoning) del municipio
        vía WFS INSPIRE del Catastro.

        CP:CadastralZoning es una capa INSPIRE que contiene polígonos de zonas
        catastrales con nombre/etiqueta. Para Getafe (código 28065) puede devolver
        zonas que aproximen los barrios administrativos con sus geometrías reales.

        En entorno de desarrollo Docker (sin acceso DNS a catastro.meh.es):
        lanzará excepción → el caller captura y continúa sin geometría.

        Returns:
            GeoJSON dict con features de zonas catastrales, o None si el servicio
            WFS no responde o no devuelve features para este municipio.
        """
        url = CATASTRO_WFS_URL
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": "CP:CadastralZoning",
            "COUNT": "500",
            "CQL_FILTER": f"NationalCadastralReference LIKE '{self.codigo_municipio}%'",
            "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326",
        }
        try:
            response = self.session.get(url, params=params, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            n_features = len(data.get("features", []))
            if n_features == 0:
                logger.warning("WFS CadastralZoning: 0 features para Getafe — sin geometría de barrios")
                return None
            logger.info(f"WFS CadastralZoning Getafe: {n_features} zonas descargadas")
            return data
        except httpx.HTTPError as e:
            logger.warning(f"WFS CadastralZoning no disponible ({e})")
            return None

    def close(self):
        self.session.close()


# ---------------------------------------------------------------------------
# Helpers de geometría (funciones libres, no métodos de clase)
# ---------------------------------------------------------------------------

def _extraer_geometrias_zonas(
    geojson: dict,
    barrios_getafe: list[dict],
) -> dict[str, dict]:
    """
    Intenta mapear features del GeoJSON de CadastralZoning a los barrios de Getafe
    por coincidencia de nombre (primera palabra, case-insensitive).

    Cada feature de CadastralZoning tiene propiedades como 'label', 'zoneType',
    'levelName' o similares según la implementación INSPIRE del Catastro español.

    Args:
        geojson:         GeoJSON devuelto por get_zonas_catastrales_wfs()
        barrios_getafe:  lista de dicts con al menos 'codigo' y 'nombre'

    Returns:
        dict {codigo_barrio: {"wkt": wkt_str, "superficie_m2": float}}
        Si geopandas no está disponible o el mapeo falla → devuelve {}
        (los barrios se insertarán sin geometría).
    """
    try:
        import geopandas as gpd
        from shapely.ops import unary_union
        import math

        features = geojson.get("features", [])
        if not features:
            return {}

        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

        # Identificar columnas de texto que pueden contener nombres de zona
        name_cols = [
            c for c in gdf.columns
            if any(k in c.lower() for k in ("label", "name", "nombre", "zone", "level"))
            and gdf[c].dtype == object
        ]

        result: dict[str, dict] = {}
        lat_ref = 40.3  # latitud media de Getafe para conversión de grados a metros

        for datos in barrios_getafe:
            codigo = datos["codigo"]
            primera_palabra = datos["nombre"].split()[0].lower()
            matched_geom = None

            for col in name_cols:
                mask = gdf[col].astype(str).str.lower().str.contains(
                    primera_palabra, na=False, regex=False
                )
                matched = gdf[mask]
                if not matched.empty:
                    merged = unary_union(matched.geometry.values)
                    matched_geom = merged
                    logger.debug(
                        f"Barrio {codigo} ({datos['nombre']}): match en col '{col}' "
                        f"→ {len(matched)} zona(s)"
                    )
                    break

            if matched_geom is None:
                continue

            # Convertir geometry a WKT extendido compatible con GeoAlchemy2
            wkt_str = matched_geom.wkt
            if not wkt_str.startswith("MULTIPOLYGON"):
                # Envolver Polygon en MULTIPOLYGON si es necesario
                if wkt_str.startswith("POLYGON"):
                    wkt_str = f"MULTIPOLYGON({wkt_str[7:]})"

            # Aproximación de superficie en m² (grados → metros en lat ~40°)
            m_per_deg_lat = 111_320.0
            m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat_ref))
            area_deg2 = matched_geom.area
            area_m2 = area_deg2 * m_per_deg_lat * m_per_deg_lon

            result[codigo] = {
                "wkt": f"SRID=4326;{wkt_str}",
                "superficie_m2": round(area_m2, 0),
            }

        logger.info(
            f"_extraer_geometrias_zonas: {len(result)}/{len(barrios_getafe)} barrios "
            f"mapeados desde {len(features)} zonas catastrales"
        )
        return result

    except ImportError:
        logger.warning("geopandas/shapely no disponible; barrios sin geometría")
        return {}
    except Exception as e:
        logger.warning(f"Error extrayendo geometrías de zonas catastrales: {e}")
        return {}
