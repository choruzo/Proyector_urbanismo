"""
Scraper para el BOCM (Boletín Oficial de la Comunidad de Madrid).
URL base: https://www.bocm.es/

El BOCM publica licitaciones, convenios urbanísticos, aprobaciones de planes
de ordenación, y actos administrativos del Ayuntamiento de Getafe.
Se accede vía búsqueda web y feed RSS cuando está disponible.
"""
import re
from datetime import date, datetime, timedelta
import httpx
import feedparser
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings


BOCM_BASE_URL = "https://www.bocm.es"
BOCM_SEARCH_URL = "https://www.bocm.es/advanced-search"  # /buscador fue renombrado en 2024
BOE_API_BASE = "https://boe.es/diario_boe/xml.php"

# Palabras clave para filtrar publicaciones relevantes de Getafe
KEYWORDS_URBANISMO = [
    "Getafe", "EMSV", "Empresa Municipal de Suelo",
    "urbanismo", "licencia obra", "plan parcial", "PGOU",
    "vivienda protegida", "VPO", "licitación", "contrato obras",
    "planeamiento", "reparcelación", "compensación"
]


class BOCMScraper:
    """
    Scraper del Boletín Oficial de la Comunidad de Madrid.
    Detecta automáticamente publicaciones urbanísticas relacionadas con Getafe.
    """

    def __init__(self):
        self.session = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "ProyectorUrbanisticoGetafe/0.1 (investigacion ciudadana)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            }
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=3, max=15))
    def buscar_publicaciones_getafe(self, fecha: date) -> list[dict]:
        """
        Busca en el BOCM publicaciones relacionadas con Getafe para una fecha dada.

        Usa el buscador avanzado del portal BOCM (Drupal Views, SSR).
        URL actualizada en 2024: /buscador → /advanced-search
        Parámetros: keys (texto) + field_bulletin_field_date[value] (DD-MM-YYYY)
        """
        resultados = []
        fecha_str = fecha.strftime("%d-%m-%Y")  # formato Drupal: DD-MM-YYYY

        try:
            response = self.session.get(
                BOCM_SEARCH_URL,
                params={
                    "keys": "Getafe urbanismo",
                    "field_bulletin_field_date[value]": fecha_str,
                },
                headers={
                    **self.session.headers,
                    "Referer": BOCM_BASE_URL,
                },
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Selectores Drupal Views (patrón estándar del CMS)
            items = soup.select(".view-content .views-row")
            if not items:
                # Fallback: algunos temas Drupal omiten .view-content
                items = soup.select(".views-row")

            if not items:
                logger.debug(f"BOCM {fecha_str}: sin resultados en la página (fecha sin publicaciones o AJAX)")

            for item in items:
                # Título: campo Views o primer enlace del item
                titulo_el = (
                    item.select_one(".views-field-title a")
                    or item.select_one(".views-field-field-bulletin-description a")
                    or item.select_one("h3 a, h4 a, .field-content a")
                )
                enlace_el = item.select_one("a[href]")
                desc_el = (
                    item.select_one(".views-field-body .field-content")
                    or item.select_one(".views-field-field-bulletin-description .field-content")
                    or item.select_one("p")
                )

                if not titulo_el:
                    continue

                titulo_text = titulo_el.get_text(strip=True)
                if not titulo_text:
                    continue

                # Filtrar por relevancia (keywords urbanísticos de Getafe)
                if not any(kw.lower() in titulo_text.lower() for kw in KEYWORDS_URBANISMO):
                    continue

                href = enlace_el["href"] if enlace_el else ""
                url = (BOCM_BASE_URL + href) if href.startswith("/") else href or None

                resultados.append({
                    "titulo": titulo_text,
                    "descripcion": desc_el.get_text(strip=True) if desc_el else "",
                    "url": url,
                    "fecha_publicacion": fecha,
                    "fuente": "bocm",
                    "tipo": self._clasificar_tipo(titulo_text),
                    "importe_euros": self._extraer_importe(titulo_text),
                })

        except httpx.HTTPError as e:
            logger.error(f"Error al acceder BOCM para fecha {fecha_str}: {e}")

        return resultados

    def escanear_rango_fechas(self, dias_atras: int = 7) -> list[dict]:
        """Escanea los últimos N días del BOCM buscando publicaciones de Getafe."""
        todas = []
        hoy = date.today()
        for i in range(dias_atras):
            fecha = hoy - timedelta(days=i)
            # BOCM no publica sábados/domingos
            if fecha.weekday() < 5:
                publicaciones = self.buscar_publicaciones_getafe(fecha)
                todas.extend(publicaciones)
                logger.info(f"BOCM {fecha}: {len(publicaciones)} publicaciones encontradas")
        return todas

    def _clasificar_tipo(self, titulo: str) -> str:
        """Clasifica el tipo de alerta según el título."""
        titulo_lower = titulo.lower()
        if any(w in titulo_lower for w in ["licitación", "contrato", "concurso", "adjudicación"]):
            return "licitacion"
        if any(w in titulo_lower for w in ["convenio", "acuerdo"]):
            return "convenio"
        if any(w in titulo_lower for w in ["plan parcial", "pgou", "planeamiento", "plan especial"]):
            return "planeamiento"
        if any(w in titulo_lower for w in ["emsv", "vivienda protegida", "vpo"]):
            return "emsv"
        return "otro"

    def _extraer_importe(self, texto: str) -> float | None:
        """Intenta extraer un importe económico del texto."""
        patron = r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:euros|€|EUR)'
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            try:
                importe_str = match.group(1).replace(".", "").replace(",", ".")
                return float(importe_str)
            except ValueError:
                pass
        return None

    def close(self):
        self.session.close()


class BOEScraper:
    """
    Scraper del BOE (Boletín Oficial del Estado) para publicaciones de Getafe.
    Usa la API XML oficial del BOE.
    """

    def __init__(self):
        self.session = httpx.Client(timeout=30.0, follow_redirects=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def buscar_por_fecha(self, fecha: date) -> list[dict]:
        """Descarga el sumario del BOE para una fecha y filtra por Getafe."""
        url = f"https://boe.es/diario_boe/xml.php?id=BOE-S-{fecha.strftime('%Y%m%d')}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return self._parsear_sumario_xml(response.text, fecha)
        except httpx.HTTPError as e:
            logger.error(f"Error al acceder BOE para fecha {fecha}: {e}")
            return []

    def _parsear_sumario_xml(self, xml_text: str, fecha: date) -> list[dict]:
        """Parsea el XML del sumario del BOE y filtra por municipio."""
        import xml.etree.ElementTree as ET
        resultados = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item"):
                titulo = item.findtext("titulo", "")
                if "Getafe" not in titulo:
                    continue
                resultados.append({
                    "titulo": titulo,
                    "descripcion": item.findtext("texto", ""),
                    "url": item.findtext("urlPdf", ""),
                    "fecha_publicacion": fecha,
                    "fuente": "boe",
                    "tipo": "licitacion" if "contrato" in titulo.lower() else "otro",
                    "importe_euros": None,
                })
        except ET.ParseError as e:
            logger.error(f"Error parseando XML BOE: {e}")
        return resultados

    def close(self):
        self.session.close()
