"""
Punto de entrada principal de la aplicación FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import tendencias, alertas, predicciones, mapa


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicio y cierre de la aplicación."""
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    # Crear tablas si no existen (en producción usar Alembic)
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos lista")
    yield
    logger.info("Cerrando aplicación")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para el dashboard urbanístico de Getafe. Datos desde 2001.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permitir peticiones del frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "PATCH"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(tendencias.router, prefix=settings.API_PREFIX)
app.include_router(alertas.router, prefix=settings.API_PREFIX)
app.include_router(predicciones.router, prefix=settings.API_PREFIX)
app.include_router(mapa.router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["Sistema"])
def health_check():
    """Endpoint de comprobación de estado del servicio."""
    return {"status": "ok", "version": settings.APP_VERSION, "municipio": settings.MUNICIPIO_NOMBRE}
