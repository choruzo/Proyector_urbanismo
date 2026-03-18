"""
Modelos SQLAlchemy para obra nueva y licencias de edificación.
Fuentes: Ministerio de Vivienda (visados), Ayuntamiento de Getafe (licencias)
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Enum, Index
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base
import enum


class TipoPromotor(str, enum.Enum):
    PUBLICO = "publico"
    PRIVADO = "privado"
    EMSV = "emsv"
    MIXTO = "mixto"


class EstadoObra(str, enum.Enum):
    PROYECTADA = "proyectada"
    LICENCIA_SOLICITADA = "licencia_solicitada"
    LICENCIA_CONCEDIDA = "licencia_concedida"
    EN_CONSTRUCCION = "en_construccion"
    FINALIZADA = "finalizada"
    PARALIZADA = "paralizada"


class ObraNueva(Base):
    """Registro de proyectos de obra nueva de edificación en Getafe."""
    __tablename__ = "obras_nueva"

    id = Column(Integer, primary_key=True)
    expediente = Column(String(50), unique=True, nullable=True, index=True)
    nombre_proyecto = Column(String(300))
    promotor = Column(String(200))
    tipo_promotor = Column(Enum(TipoPromotor), default=TipoPromotor.PRIVADO)
    estado = Column(Enum(EstadoObra), default=EstadoObra.PROYECTADA)
    uso = Column(String(100))               # residencial libre, VPO, VP, comercial...
    direccion = Column(String(300))
    barrio = Column(String(100))
    referencia_catastral = Column(String(20), nullable=True)
    numero_viviendas = Column(Integer, nullable=True)
    superficie_total_m2 = Column(Float, nullable=True)
    numero_plantas = Column(Integer, nullable=True)
    fecha_solicitud_licencia = Column(Date, nullable=True)
    fecha_concesion_licencia = Column(Date, nullable=True)
    fecha_inicio_obras = Column(Date, nullable=True)
    fecha_fin_obras = Column(Date, nullable=True)
    presupuesto_ejecucion = Column(Float, nullable=True)  # €
    fuente = Column(String(100))
    url_fuente = Column(Text, nullable=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VisadoEstadistico(Base):
    """
    Datos estadísticos de visados de obra nueva del Colegio de Arquitectos.
    Serie histórica anual/trimestral para Getafe.
    Fuente: Ministerio de Vivienda y Agenda Urbana.
    """
    __tablename__ = "visados_estadisticos"

    id = Column(Integer, primary_key=True)
    anno = Column(Integer, nullable=False, index=True)
    trimestre = Column(Integer, nullable=True)
    tipo_obra = Column(String(100))         # nueva planta, ampliación, rehabilitación
    uso = Column(String(100))
    numero_visados = Column(Integer)
    numero_viviendas = Column(Integer)
    superficie_m2 = Column(Float)
    presupuesto_total = Column(Float)
    fuente = Column(String(100), default="mivau")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_visados_fuente", "fuente"),
        Index("ix_visados_anno_fuente", "anno", "fuente"),
        Index("ix_visados_anno_tipo", "anno", "tipo_obra"),
    )
