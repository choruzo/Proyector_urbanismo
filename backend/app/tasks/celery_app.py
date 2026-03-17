"""
Tareas periódicas con Celery.
Se ejecutan automáticamente según el schedule configurado.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from loguru import logger

celery_app = Celery(
    "proyector_urbanismo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scheduled_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Madrid",
    enable_utc=True,
    # Schedule de tareas periódicas
    beat_schedule={
        # Escaneo diario del BOCM (días laborables a las 10:00)
        "escanear-bocm-diario": {
            "task": "app.tasks.scheduled_tasks.task_escanear_bocm",
            "schedule": crontab(hour=10, minute=0, day_of_week="1-5"),
        },
        # Escaneo diario del BOE
        "escanear-boe-diario": {
            "task": "app.tasks.scheduled_tasks.task_escanear_boe",
            "schedule": crontab(hour=10, minute=30, day_of_week="1-5"),
        },
        # Actualización semanal de datos del Catastro (domingos 03:00)
        "actualizar-catastro-semanal": {
            "task": "app.tasks.scheduled_tasks.task_actualizar_catastro",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
        },
        # Actualización mensual de estadísticas INE (día 15 de cada mes)
        "actualizar-ine-mensual": {
            "task": "app.tasks.scheduled_tasks.task_actualizar_ine",
            "schedule": crontab(hour=2, minute=0, day_of_month=15),
        },
        # Actualización trimestral de datos de vivienda del Ministerio
        "actualizar-vivienda-trimestral": {
            "task": "app.tasks.scheduled_tasks.task_actualizar_vivienda",
            "schedule": crontab(hour=4, minute=0, day_of_month=1, month_of_year="1,4,7,10"),
        },
        # Re-entrenamiento mensual de modelos de predicción
        "reentrenar-modelos-mensual": {
            "task": "app.tasks.scheduled_tasks.task_reentrenar_modelos",
            "schedule": crontab(hour=5, minute=0, day_of_month=20),
        },
    },
)
