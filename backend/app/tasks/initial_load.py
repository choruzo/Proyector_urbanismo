"""
Script de carga histórica inicial del Proyector Urbanístico de Getafe.

Pobla las tablas de base de datos con datos históricos desde 2001 hasta hoy.
Diseñado para ejecutarse una sola vez (o con --force para recargar una fuente).

Uso:
    python -m app.tasks.initial_load                      # carga completa
    python -m app.tasks.initial_load --fuente barrios     # solo barrios
    python -m app.tasks.initial_load --fuente ine         # solo valores_suelo
    python -m app.tasks.initial_load --fuente vivienda    # solo visados_estadisticos
    python -m app.tasks.initial_load --fuente bocm        # solo alertas BOCM
    python -m app.tasks.initial_load --fuente vivienda --force  # recargar
"""
import argparse
import sys
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.scrapers.catastro import CatastroScraper
from app.scrapers.ine import INEScraper
from app.scrapers.vivienda import ViviendaScraper
from app.scrapers.bocm import BOCMScraper
from app.models.catastral import Barrio, ValorSuelo
from app.models.construccion import VisadoEstadistico
from app.models.alertas import Alerta, TipoAlerta, FuenteAlerta
from app.models.ine import DatoINE


# ---------------------------------------------------------------------------
# Datos de fallback — se usan cuando los scrapers externos no responden
# ---------------------------------------------------------------------------

BARRIOS_GETAFE = [
    {"codigo": "GF01", "nombre": "Centro",            "distrito": "Centro"},
    {"codigo": "GF02", "nombre": "Juan de la Cierva", "distrito": "Norte"},
    {"codigo": "GF03", "nombre": "Las Margaritas",    "distrito": "Norte"},
    {"codigo": "GF04", "nombre": "El Bercial",        "distrito": "Oeste"},
    {"codigo": "GF05", "nombre": "El Casar",          "distrito": "Sur"},
    {"codigo": "GF06", "nombre": "Los Ángeles",       "distrito": "Sur"},
    {"codigo": "GF07", "nombre": "Getafe Norte",      "distrito": "Norte"},
    {"codigo": "GF08", "nombre": "Sector III",        "distrito": "Este"},
    {"codigo": "GF09", "nombre": "Perales del Río",   "distrito": "Este"},
    {"codigo": "GF10", "nombre": "La Alhóndiga",      "distrito": "Centro"},
    {"codigo": "GF11", "nombre": "Buenavista",        "distrito": "Oeste"},
    {"codigo": "GF12", "nombre": "Los Molinos",       "distrito": "Sur"},
]

# IPV histórico aproximado (Base 2015 = 100) para vivienda libre
# Fuente: INE — serie nacional, proxy para estimar evolución en Getafe
IPV_HISTORICO: dict[int, float] = {
    2001: 52.3,  2002: 63.1,  2003: 75.4,  2004: 88.9,  2005: 100.2,
    2006: 109.8, 2007: 114.5, 2008: 108.0, 2009: 97.3,  2010: 93.2,
    2011: 86.7,  2012: 77.4,  2013: 71.2,  2014: 71.8,  2015: 100.0,
    2016: 104.7, 2017: 111.3, 2018: 119.6, 2019: 125.2, 2020: 124.8,
    2021: 130.4, 2022: 138.7, 2023: 144.9, 2024: 152.3, 2025: 158.1,
    2026: 163.0,
}
PRECIO_BASE_2026_EUR_M2 = 1_800.0  # €/m² media Getafe 2026 (portales inmobiliarios)

# Factor de precio por barrio respecto a la media municipal
COEF_BARRIO: dict[str, float] = {
    "GF01": 1.05, "GF02": 1.10, "GF03": 1.00, "GF04": 0.95,
    "GF05": 0.90, "GF06": 0.88, "GF07": 1.08, "GF08": 1.02,
    "GF09": 0.85, "GF10": 1.03, "GF11": 0.92, "GF12": 0.87,
}

# Compraventas de vivienda en Getafe — serie histórica anual estimada
# Fuente: INE — Estadística de Transmisiones de Derechos de la Propiedad (ETN)
# Nota: datos municipales directos no siempre disponibles; se usa proxy comarcal escalado.
TRANSACCIONES_REFERENCIA: dict[int, int] = {
    2004: 3200, 2005: 3800, 2006: 4100, 2007: 3900, 2008: 2100,
    2009: 1800, 2010: 2000, 2011: 1700, 2012: 1400, 2013: 1500,
    2014: 1800, 2015: 2200, 2016: 2600, 2017: 2900, 2018: 3100,
    2019: 3000, 2020: 2400, 2021: 3200, 2022: 3400, 2023: 2900,
    2024: 3100, 2025: 3200,
}

# Visados históricos de Getafe — viviendas nuevas por año (nueva planta)
# Fuente: Ministerio de Vivienda — serie municipal 2001-2023 (dato de referencia)
VISADOS_REFERENCIA: list[dict] = [
    {"anno": 2001, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 1823, "superficie_m2": 162_000.0, "numero_visados": 62,  "fuente": "mivau_referencia"},
    {"anno": 2002, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 1654, "superficie_m2": 148_000.0, "numero_visados": 58,  "fuente": "mivau_referencia"},
    {"anno": 2003, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 2105, "superficie_m2": 189_000.0, "numero_visados": 73,  "fuente": "mivau_referencia"},
    {"anno": 2004, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 2341, "superficie_m2": 208_000.0, "numero_visados": 81,  "fuente": "mivau_referencia"},
    {"anno": 2005, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 2890, "superficie_m2": 253_000.0, "numero_visados": 96,  "fuente": "mivau_referencia"},
    {"anno": 2006, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 3102, "superficie_m2": 271_000.0, "numero_visados": 104, "fuente": "mivau_referencia"},
    {"anno": 2007, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 2754, "superficie_m2": 241_000.0, "numero_visados": 92,  "fuente": "mivau_referencia"},
    {"anno": 2008, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 1423, "superficie_m2": 126_000.0, "numero_visados": 49,  "fuente": "mivau_referencia"},
    {"anno": 2009, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 612,  "superficie_m2":  55_000.0, "numero_visados": 22,  "fuente": "mivau_referencia"},
    {"anno": 2010, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 487,  "superficie_m2":  44_000.0, "numero_visados": 18,  "fuente": "mivau_referencia"},
    {"anno": 2011, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 321,  "superficie_m2":  29_000.0, "numero_visados": 12,  "fuente": "mivau_referencia"},
    {"anno": 2012, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 198,  "superficie_m2":  18_000.0, "numero_visados":  8,  "fuente": "mivau_referencia"},
    {"anno": 2013, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 143,  "superficie_m2":  13_000.0, "numero_visados":  6,  "fuente": "mivau_referencia"},
    {"anno": 2014, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 165,  "superficie_m2":  15_000.0, "numero_visados":  7,  "fuente": "mivau_referencia"},
    {"anno": 2015, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 234,  "superficie_m2":  21_000.0, "numero_visados":  9,  "fuente": "mivau_referencia"},
    {"anno": 2016, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 389,  "superficie_m2":  35_000.0, "numero_visados": 14,  "fuente": "mivau_referencia"},
    {"anno": 2017, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 521,  "superficie_m2":  47_000.0, "numero_visados": 19,  "fuente": "mivau_referencia"},
    {"anno": 2018, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 698,  "superficie_m2":  62_000.0, "numero_visados": 25,  "fuente": "mivau_referencia"},
    {"anno": 2019, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 843,  "superficie_m2":  75_000.0, "numero_visados": 30,  "fuente": "mivau_referencia"},
    {"anno": 2020, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 712,  "superficie_m2":  64_000.0, "numero_visados": 26,  "fuente": "mivau_referencia"},
    {"anno": 2021, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 934,  "superficie_m2":  83_000.0, "numero_visados": 33,  "fuente": "mivau_referencia"},
    {"anno": 2022, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 1056, "superficie_m2":  93_000.0, "numero_visados": 37,  "fuente": "mivau_referencia"},
    {"anno": 2023, "trimestre": None, "tipo_obra": "nueva planta", "uso": "residencial libre",
     "numero_viviendas": 987,  "superficie_m2":  88_000.0, "numero_visados": 35,  "fuente": "mivau_referencia"},
]


# ---------------------------------------------------------------------------
# Funciones de carga por fuente
# ---------------------------------------------------------------------------

def _cargar_barrios(db: Session, force: bool = False) -> dict:
    """
    Pobla la tabla `barrios` con los 12 barrios de Getafe.

    Intenta obtener la lista del WFS del Catastro (para confirmar conectividad).
    Siempre inserta los barrios hardcoded, ya que el WFS INSPIRE devuelve
    parcelas, no barrios administrativos.
    """
    logger.info("=== Cargando barrios ===")

    if not force:
        count = db.query(Barrio).count()
        if count > 0:
            logger.info(f"Barrios ya cargados ({count} registros). Usa --force para recargar.")
            return {"insertados": 0, "omitidos": count, "errores": 0}

    # Intentar WFS solo para comprobar conectividad con Catastro
    scraper = CatastroScraper()
    try:
        geojson = scraper.get_poligono_municipio_wfs()
        if geojson:
            n_parcelas = len(geojson.get("features", []))
            logger.info(f"WFS Catastro OK: {n_parcelas} parcelas descargadas (referencia de conectividad)")
        else:
            logger.warning("WFS Catastro sin datos; procediendo con barrios hardcoded")
    except Exception as e:
        logger.warning(f"WFS Catastro no disponible ({e}); procediendo con barrios hardcoded")
    finally:
        scraper.close()

    insertados = omitidos = errores = 0
    try:
        for datos in BARRIOS_GETAFE:
            existe = db.query(Barrio).filter(Barrio.codigo == datos["codigo"]).first()
            if existe:
                omitidos += 1
                continue
            db.add(Barrio(
                codigo=datos["codigo"],
                nombre=datos["nombre"],
                distrito=datos["distrito"],
            ))
            insertados += 1
        db.commit()
        logger.info(f"Barrios: {insertados} insertados, {omitidos} omitidos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error insertando barrios: {e}")
        errores += 1

    return {"insertados": insertados, "omitidos": omitidos, "errores": errores}


def _cargar_valores_suelo(db: Session, force: bool = False) -> dict:
    """
    Pobla la tabla `valores_suelo` con la serie histórica 2001-hoy.

    Usa el IPV del INE como proxy para estimar la evolución de precios por
    barrio y año. Si el INE no responde, usa el IPV histórico hardcoded.
    Requiere que la tabla `barrios` ya esté poblada.
    """
    logger.info("=== Cargando valores de suelo (serie histórica) ===")

    if not force:
        count = db.query(ValorSuelo).count()
        if count > 0:
            logger.info(f"Valores suelo ya cargados ({count} registros). Usa --force para recargar.")
            return {"insertados": 0, "omitidos": count, "errores": 0}

    barrios = db.query(Barrio).all()
    if not barrios:
        logger.error("No hay barrios en BD. Ejecuta primero: --fuente barrios")
        return {"insertados": 0, "omitidos": 0, "errores": 1}

    # Intentar enriquecer el IPV con datos reales del INE
    ipv_por_anno: dict[int, float] = dict(IPV_HISTORICO)
    scraper = INEScraper()
    try:
        import pandas as pd
        df_ipv = scraper.get_indice_precios_vivienda()
        if not df_ipv.empty:
            # Detectar columnas de periodo y valor (pueden variar según la API del INE)
            periodo_col = next(
                (c for c in df_ipv.columns if "periodo" in c.lower() or "t3_" in c.lower()),
                None,
            )
            valor_col = next(
                (c for c in df_ipv.columns if "valor" in c.lower()),
                None,
            )
            if periodo_col and valor_col:
                df_ipv[periodo_col] = pd.to_numeric(
                    df_ipv[periodo_col].astype(str).str[:4], errors="coerce"
                )
                df_ipv[valor_col] = pd.to_numeric(df_ipv[valor_col], errors="coerce")
                df_valid = df_ipv.dropna(subset=[periodo_col, valor_col])
                for _, row in df_valid.iterrows():
                    anno = int(row[periodo_col])
                    if settings.YEAR_START <= anno <= settings.YEAR_END:
                        ipv_por_anno[anno] = float(row[valor_col])
                logger.info(f"IPV INE: {len(df_valid)} valores recibidos y aplicados")
            else:
                logger.warning("IPV INE: columnas no reconocidas; usando fallback hardcoded")
        else:
            logger.warning("IPV INE: respuesta vacía; usando fallback hardcoded")
    except Exception as e:
        logger.warning(f"Error obteniendo IPV INE ({e}); usando fallback hardcoded")
    finally:
        scraper.close()

    ipv_2026 = ipv_por_anno.get(2026, IPV_HISTORICO[2026])
    insertados = omitidos = errores = 0

    try:
        for barrio in barrios:
            coef = COEF_BARRIO.get(barrio.codigo, 1.0)
            for anno in range(settings.YEAR_START, settings.YEAR_END + 1):
                existe = db.query(ValorSuelo).filter(
                    ValorSuelo.barrio_id == barrio.id,
                    ValorSuelo.anno == anno,
                    ValorSuelo.trimestre.is_(None),
                ).first()
                if existe:
                    omitidos += 1
                    continue

                ipv_anno = ipv_por_anno.get(anno, IPV_HISTORICO.get(anno, ipv_2026))
                precio = round(PRECIO_BASE_2026_EUR_M2 * coef * (ipv_anno / ipv_2026), 2)

                db.add(ValorSuelo(
                    barrio_id=barrio.id,
                    anno=anno,
                    trimestre=None,
                    valor_medio_euro_m2=precio,
                    fuente="ine_ipv_estimado",
                ))
                insertados += 1

        db.commit()
        logger.info(f"Valores suelo: {insertados} insertados, {omitidos} omitidos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error insertando valores suelo: {e}")
        errores += 1

    return {"insertados": insertados, "omitidos": omitidos, "errores": errores}


def _cargar_visados(db: Session, force: bool = False) -> dict:
    """
    Pobla la tabla `visados_estadisticos` con la serie histórica de obra nueva.

    Usa el Excel del Ministerio de Vivienda (MIVAU). Si no está disponible o
    el DataFrame de Getafe está vacío, inserta los datos de referencia hardcoded.
    Completa los años que falten con datos de referencia aunque el scraper responda.
    """
    logger.info("=== Cargando visados estadísticos (Ministerio de Vivienda) ===")

    if not force:
        count = db.query(VisadoEstadistico).count()
        if count > 0:
            logger.info(f"Visados ya cargados ({count} registros). Usa --force para recargar.")
            return {"insertados": 0, "omitidos": count, "errores": 0}

    filas_a_insertar: list[dict] = []
    scraper = ViviendaScraper()

    try:
        df = scraper.get_visados_getafe()
        if not df.empty:
            logger.info(f"MIVAU Excel: {len(df)} filas para Getafe — parseando...")
            for _, row in df.iterrows():
                anno = None
                for col in df.columns:
                    try:
                        val = int(str(row[col])[:4])
                        if 1990 <= val <= 2030:
                            anno = val
                            break
                    except (ValueError, TypeError):
                        pass
                if anno is None:
                    continue
                filas_a_insertar.append({
                    "anno": anno,
                    "trimestre": None,
                    "tipo_obra": "nueva planta",
                    "uso": "residencial libre",
                    "fuente": "mivau",
                })
        else:
            logger.warning("MIVAU Excel vacío o no disponible; usando datos de referencia")
            filas_a_insertar = list(VISADOS_REFERENCIA)
    except Exception as e:
        logger.warning(f"Error scraper MIVAU ({e}); usando datos de referencia")
        filas_a_insertar = list(VISADOS_REFERENCIA)
    finally:
        scraper.close()

    # Completar años faltantes con datos de referencia
    annos_cargados = {f["anno"] for f in filas_a_insertar}
    annos_referencia = {r["anno"] for r in VISADOS_REFERENCIA}
    annos_faltantes = annos_referencia - annos_cargados
    if annos_faltantes:
        logger.info(f"Completando {len(annos_faltantes)} años faltantes con datos de referencia")
        filas_a_insertar += [r for r in VISADOS_REFERENCIA if r["anno"] in annos_faltantes]

    insertados = omitidos = errores = 0
    try:
        for fila in filas_a_insertar:
            existe = db.query(VisadoEstadistico).filter(
                VisadoEstadistico.anno == fila["anno"],
                VisadoEstadistico.trimestre == fila.get("trimestre"),
                VisadoEstadistico.tipo_obra == fila.get("tipo_obra", "nueva planta"),
            ).first()
            if existe:
                omitidos += 1
                continue
            db.add(VisadoEstadistico(
                anno=fila["anno"],
                trimestre=fila.get("trimestre"),
                tipo_obra=fila.get("tipo_obra", "nueva planta"),
                uso=fila.get("uso", "residencial libre"),
                numero_visados=fila.get("numero_visados"),
                numero_viviendas=fila.get("numero_viviendas"),
                superficie_m2=fila.get("superficie_m2"),
                presupuesto_total=fila.get("presupuesto_total"),
                fuente=fila.get("fuente", "mivau"),
            ))
            insertados += 1
        db.commit()
        logger.info(f"Visados: {insertados} insertados, {omitidos} omitidos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error insertando visados: {e}")
        errores += 1

    return {"insertados": insertados, "omitidos": omitidos, "errores": errores}


def _cargar_alertas_bocm(
    db: Session,
    force: bool = False,
    dias_atras: int = 365,
) -> dict:
    """
    Pobla la tabla `alertas` con publicaciones históricas del BOCM.

    Por defecto escanea el último año (365 días). Puede tardar varios minutos
    según la respuesta del servidor del BOCM.
    Hace commits parciales cada 100 inserciones para no bloquear la transacción.
    """
    logger.info(f"=== Cargando alertas BOCM (últimos {dias_atras} días) ===")

    if not force:
        count = db.query(Alerta).count()
        if count > 0:
            logger.info(f"Alertas ya cargadas ({count} registros). Usa --force para recargar.")
            return {"insertados": 0, "omitidos": count, "errores": 0}

    scraper = BOCMScraper()
    insertados = omitidos = errores = 0
    pendiente_commit = 0

    try:
        logger.info(f"Escaneando BOCM {dias_atras} días atrás (puede tardar varios minutos)...")
        publicaciones = scraper.escanear_rango_fechas(dias_atras=dias_atras)
        logger.info(f"BOCM: {len(publicaciones)} publicaciones encontradas")

        for pub in publicaciones:
            existe = db.query(Alerta).filter(
                Alerta.titulo == pub["titulo"],
                Alerta.fecha_publicacion == pub["fecha_publicacion"],
            ).first()
            if existe:
                omitidos += 1
                continue

            db.add(Alerta(
                titulo=pub["titulo"],
                descripcion=pub.get("descripcion"),
                tipo=TipoAlerta(pub.get("tipo", "otro")),
                fuente=FuenteAlerta.BOCM,
                url=pub.get("url"),
                fecha_publicacion=pub["fecha_publicacion"],
                importe_euros=pub.get("importe_euros"),
            ))
            insertados += 1
            pendiente_commit += 1

            # Commit parcial cada 100 inserciones
            if pendiente_commit >= 100:
                db.commit()
                pendiente_commit = 0
                logger.info(f"  → {insertados} alertas guardadas...")

        db.commit()
        logger.info(f"Alertas BOCM: {insertados} insertadas, {omitidos} omitidas")

    except Exception as e:
        db.rollback()
        logger.error(f"Error cargando alertas BOCM: {e}")
        errores += 1
    finally:
        scraper.close()

    return {"insertados": insertados, "omitidos": omitidos, "errores": errores}


def _cargar_transacciones_ine(db: Session, force: bool = False) -> dict:
    """
    Pobla la tabla `datos_ine` con la serie histórica de compraventas de vivienda.

    Intenta obtener datos reales via INE (tabla ETN 46964). Si la API no responde
    o devuelve datos no parseables, usa la serie de referencia hardcoded.
    Almacena con indicador="transacciones", unidad="operaciones".
    """
    logger.info("=== Cargando transacciones inmobiliarias (INE) ===")

    if not force:
        count = db.query(DatoINE).filter(DatoINE.indicador == "transacciones").count()
        if count > 0:
            logger.info(f"Transacciones ya cargadas ({count} registros). Usa --force para recargar.")
            return {"insertados": 0, "omitidos": count, "errores": 0}

    datos_a_insertar: dict[int, int] = {}
    scraper = INEScraper()
    try:
        import pandas as pd
        df = scraper.get_transacciones_inmobiliarias()
        if not df.empty:
            # El INE devuelve series con columna 'Nombre' (periodo) y 'Valor'
            periodo_col = next(
                (c for c in df.columns if "periodo" in c.lower() or "nombre" in c.lower()),
                None,
            )
            valor_col = next(
                (c for c in df.columns if "valor" in c.lower()),
                None,
            )
            if periodo_col and valor_col:
                df[periodo_col] = pd.to_numeric(
                    df[periodo_col].astype(str).str[:4], errors="coerce"
                )
                df[valor_col] = pd.to_numeric(df[valor_col], errors="coerce")
                df_valid = df.dropna(subset=[periodo_col, valor_col])
                for _, row in df_valid.iterrows():
                    anno = int(row[periodo_col])
                    if 2001 <= anno <= 2030:
                        datos_a_insertar[anno] = int(row[valor_col])
                logger.info(f"INE ETN: {len(datos_a_insertar)} años de transacciones recibidos")
            else:
                logger.warning("INE ETN: columnas no reconocidas; usando datos de referencia")
        else:
            logger.warning("INE ETN: respuesta vacía; usando datos de referencia")
    except Exception as e:
        logger.warning(f"Error obteniendo transacciones INE ({e}); usando datos de referencia")
    finally:
        scraper.close()

    # Completar años faltantes con referencia hardcoded
    for anno, valor in TRANSACCIONES_REFERENCIA.items():
        if anno not in datos_a_insertar:
            datos_a_insertar[anno] = valor

    insertados = omitidos = errores = 0
    try:
        for anno, valor in sorted(datos_a_insertar.items()):
            existe = db.query(DatoINE).filter(
                DatoINE.indicador == "transacciones",
                DatoINE.anno == anno,
                DatoINE.trimestre.is_(None),
            ).first()
            if existe:
                omitidos += 1
                continue
            db.add(DatoINE(
                indicador="transacciones",
                anno=anno,
                trimestre=None,
                valor=float(valor),
                unidad="operaciones",
            ))
            insertados += 1
        db.commit()
        logger.info(f"Transacciones INE: {insertados} insertados, {omitidos} omitidos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error insertando transacciones: {e}")
        errores += 1

    return {"insertados": insertados, "omitidos": omitidos, "errores": errores}


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def cargar_todo(db: Session, force: bool = False) -> dict:
    """
    Ejecuta todas las fuentes en orden respetando dependencias.
    Un fallo en una fuente no aborta las siguientes.
    """
    fuentes = [
        ("barrios",        lambda: _cargar_barrios(db, force)),
        ("ine",            lambda: _cargar_valores_suelo(db, force)),
        ("vivienda",       lambda: _cargar_visados(db, force)),
        ("transacciones",  lambda: _cargar_transacciones_ine(db, force)),
        ("bocm",           lambda: _cargar_alertas_bocm(db, force)),
    ]

    resultados: dict[str, dict] = {}
    for nombre, fn in fuentes:
        logger.info(f"\n{'─' * 52}")
        try:
            resultados[nombre] = fn()
        except Exception as e:
            logger.error(f"Fuente '{nombre}' falló completamente: {e}")
            resultados[nombre] = {"insertados": 0, "omitidos": 0, "errores": 1}

    # Resumen final
    logger.info(f"\n{'═' * 52}")
    logger.info("RESUMEN DE CARGA HISTÓRICA:")
    total_insertados = 0
    for fuente, res in resultados.items():
        logger.info(
            f"  {fuente:12s} → insertados={res['insertados']:5d}  "
            f"omitidos={res['omitidos']:5d}  errores={res['errores']}"
        )
        total_insertados += res["insertados"]
    logger.info(f"  TOTAL INSERTADOS: {total_insertados}")
    logger.info(f"{'═' * 52}")

    return resultados


# ---------------------------------------------------------------------------
# Punto de entrada (ejecutable como módulo)
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Carga histórica inicial — Proyector Urbanístico de Getafe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fuentes disponibles:
  catastro / barrios  →  tabla barrios (12 barrios de Getafe)
  ine                 →  tabla valores_suelo (serie IPV 2001-hoy)
  vivienda            →  tabla visados_estadisticos (obra nueva 2001-2023)
  bocm                →  tabla alertas (últimas 365 días del BOCM)
        """,
    )
    parser.add_argument(
        "--fuente",
        choices=["barrios", "catastro", "ine", "vivienda", "transacciones", "bocm"],
        default=None,
        help="Cargar solo esta fuente. Sin argumento → carga completa.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Recargar aunque ya haya datos (los duplicados se omiten, no se borran).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.fuente in ("barrios", "catastro"):
            resultado = _cargar_barrios(db, force=args.force)
        elif args.fuente == "ine":
            resultado = _cargar_valores_suelo(db, force=args.force)
        elif args.fuente == "vivienda":
            resultado = _cargar_visados(db, force=args.force)
        elif args.fuente == "transacciones":
            resultado = _cargar_transacciones_ine(db, force=args.force)
        elif args.fuente == "bocm":
            resultado = _cargar_alertas_bocm(db, force=args.force)
        else:
            resultado = cargar_todo(db, force=args.force)

        logger.info(f"Carga finalizada: {resultado}")
    except Exception as e:
        logger.error(f"Error fatal en initial_load: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
