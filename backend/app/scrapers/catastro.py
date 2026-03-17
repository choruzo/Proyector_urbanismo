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

    def close(self):
        self.session.close()
