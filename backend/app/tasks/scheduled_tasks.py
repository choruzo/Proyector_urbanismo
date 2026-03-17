"""
Implementación de las tareas periódicas de ingesta de datos.
"""
from datetime import date, timedelta
from loguru import logger
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.scrapers.bocm import BOCMScraper, BOEScraper
from app.scrapers.catastro import CatastroScraper
from app.scrapers.ine import INEScraper
from app.scrapers.vivienda import ViviendaScraper
from app.models.alertas import Alerta, FuenteAlerta, TipoAlerta


@celery_app.task(name="app.tasks.scheduled_tasks.task_escanear_bocm", bind=True, max_retries=3)
def task_escanear_bocm(self):
    """Escanea el BOCM de los últimos 2 días y guarda las alertas nuevas."""
    logger.info("Iniciando tarea: escanear BOCM")
    scraper = BOCMScraper()
    db = SessionLocal()
    try:
        publicaciones = scraper.escanear_rango_fechas(dias_atras=2)
        nuevas = 0
        for pub in publicaciones:
            # Evitar duplicados por URL o título+fecha
            existe = db.query(Alerta).filter(
                Alerta.titulo == pub["titulo"],
                Alerta.fecha_publicacion == pub["fecha_publicacion"]
            ).first()
            if not existe:
                alerta = Alerta(
                    titulo=pub["titulo"],
                    descripcion=pub.get("descripcion"),
                    tipo=TipoAlerta(pub.get("tipo", "otro")),
                    fuente=FuenteAlerta.BOCM,
                    url=pub.get("url"),
                    fecha_publicacion=pub["fecha_publicacion"],
                    importe_euros=pub.get("importe_euros"),
                )
                db.add(alerta)
                nuevas += 1
        db.commit()
        logger.info(f"BOCM: {nuevas} nuevas alertas guardadas de {len(publicaciones)} encontradas")
        return {"nuevas": nuevas, "total_encontradas": len(publicaciones)}
    except Exception as exc:
        db.rollback()
        logger.error(f"Error en task_escanear_bocm: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)
    finally:
        db.close()
        scraper.close()


@celery_app.task(name="app.tasks.scheduled_tasks.task_escanear_boe", bind=True, max_retries=3)
def task_escanear_boe(self):
    """Escanea el BOE del día anterior buscando publicaciones de Getafe."""
    logger.info("Iniciando tarea: escanear BOE")
    scraper = BOEScraper()
    db = SessionLocal()
    try:
        ayer = date.today() - timedelta(days=1)
        publicaciones = scraper.buscar_por_fecha(ayer)
        nuevas = 0
        for pub in publicaciones:
            existe = db.query(Alerta).filter(
                Alerta.titulo == pub["titulo"],
                Alerta.fecha_publicacion == pub["fecha_publicacion"]
            ).first()
            if not existe:
                alerta = Alerta(
                    titulo=pub["titulo"],
                    tipo=TipoAlerta(pub.get("tipo", "otro")),
                    fuente=FuenteAlerta.BOE,
                    url=pub.get("url"),
                    fecha_publicacion=pub["fecha_publicacion"],
                )
                db.add(alerta)
                nuevas += 1
        db.commit()
        logger.info(f"BOE: {nuevas} nuevas alertas de Getafe guardadas")
        return {"nuevas": nuevas}
    except Exception as exc:
        db.rollback()
        logger.error(f"Error en task_escanear_boe: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)
    finally:
        db.close()
        scraper.close()


@celery_app.task(name="app.tasks.scheduled_tasks.task_actualizar_catastro")
def task_actualizar_catastro():
    """Actualiza datos geoespaciales del Catastro (parcelas de Getafe)."""
    logger.info("Iniciando tarea: actualizar Catastro")
    scraper = CatastroScraper()
    try:
        geojson = scraper.get_poligono_municipio_wfs()
        if geojson:
            logger.info(f"Catastro WFS: {len(geojson.get('features', []))} parcelas descargadas")
        return {"estado": "completado"}
    except Exception as e:
        logger.error(f"Error actualizando catastro: {e}")
        return {"estado": "error", "mensaje": str(e)}
    finally:
        scraper.close()


@celery_app.task(name="app.tasks.scheduled_tasks.task_actualizar_ine")
def task_actualizar_ine():
    """Actualiza estadísticas del INE para Getafe."""
    logger.info("Iniciando tarea: actualizar INE")
    scraper = INEScraper()
    try:
        df_poblacion = scraper.get_poblacion_getafe()
        df_transacciones = scraper.get_transacciones_inmobiliarias()
        logger.info(f"INE: {len(df_poblacion)} registros de población, {len(df_transacciones)} de transacciones")
        return {"poblacion": len(df_poblacion), "transacciones": len(df_transacciones)}
    except Exception as e:
        logger.error(f"Error actualizando INE: {e}")
        return {"estado": "error"}
    finally:
        scraper.close()


@celery_app.task(name="app.tasks.scheduled_tasks.task_actualizar_vivienda")
def task_actualizar_vivienda():
    """Actualiza estadísticas de vivienda del Ministerio."""
    logger.info("Iniciando tarea: actualizar Ministerio de Vivienda")
    scraper = ViviendaScraper()
    try:
        df_visados = scraper.get_visados_getafe()
        df_precios = scraper.get_precios_vivienda_getafe()
        logger.info(f"Vivienda: {len(df_visados)} visados, {len(df_precios)} registros de precios")
        return {"visados": len(df_visados), "precios": len(df_precios)}
    except Exception as e:
        logger.error(f"Error actualizando vivienda: {e}")
        return {"estado": "error"}
    finally:
        scraper.close()


@celery_app.task(name="app.tasks.scheduled_tasks.task_reentrenar_modelos")
def task_reentrenar_modelos():
    """Re-entrena los modelos de predicción con los datos más recientes."""
    logger.info("Iniciando tarea: re-entrenamiento de modelos ML")
    # TODO: implementar lógica de re-entrenamiento cuando haya datos suficientes
    return {"estado": "completado", "mensaje": "Re-entrenamiento pendiente de datos mínimos"}
