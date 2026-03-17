"""
Modelos SQLAlchemy para inversión pública/privada y alertas.
Fuentes: BOCM, BOE, EMSV, Ayuntamiento de Getafe
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Enum
from app.core.database import Base
import enum


class TipoAlerta(str, enum.Enum):
    LICITACION = "licitacion"
    ADJUDICACION = "adjudicacion"
    CONVENIO = "convenio"
    PLANEAMIENTO = "planeamiento"
    EMSV = "emsv"
    OTRO = "otro"


class FuenteAlerta(str, enum.Enum):
    BOCM = "bocm"
    BOE = "boe"
    AYUNTAMIENTO = "ayuntamiento"
    EMSV = "emsv"


class Alerta(Base):
    """
    Alertas automáticas de publicaciones urbanísticas relevantes para Getafe.
    Se ingieren diariamente desde BOCM, BOE y fuentes municipales.
    """
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True)
    titulo = Column(String(500), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(Enum(TipoAlerta), default=TipoAlerta.OTRO)
    fuente = Column(Enum(FuenteAlerta), nullable=False)
    url = Column(Text, nullable=True)
    fecha_publicacion = Column(Date, nullable=False, index=True)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow)
    importe_euros = Column(Float, nullable=True)
    organismo_contratante = Column(String(300), nullable=True)
    leida = Column(Boolean, default=False)
    relevancia_score = Column(Float, default=0.5)   # 0-1, calculado por keywords
    created_at = Column(DateTime, default=datetime.utcnow)


class InversionPublica(Base):
    """
    Registro de partidas e inversiones públicas en urbanismo de Getafe.
    Fuentes: Presupuestos municipales, EMSV, Comunidad de Madrid, contratos públicos.
    """
    __tablename__ = "inversiones_publicas"

    id = Column(Integer, primary_key=True)
    anno = Column(Integer, nullable=False, index=True)
    nombre_proyecto = Column(String(400), nullable=False)
    organismo = Column(String(200))         # Ayto. Getafe, EMSV, CAM, Estado
    tipo_actuacion = Column(String(200))    # urbanización, vivienda pública, zonas verdes...
    importe_presupuestado = Column(Float, nullable=True)
    importe_adjudicado = Column(Float, nullable=True)
    importe_ejecutado = Column(Float, nullable=True)
    estado = Column(String(100))
    barrio = Column(String(100), nullable=True)
    expediente_contratacion = Column(String(100), nullable=True)
    url_contrato = Column(Text, nullable=True)
    fuente = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProyectoEMSV(Base):
    """
    Proyectos de la Empresa Municipal de Suelo y Vivienda de Getafe (EMSV).
    Vivienda pública, suelo municipal, promociones de VPO/VP.
    """
    __tablename__ = "proyectos_emsv"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(300), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(100))              # VPO, VP, alquiler social, suelo, etc.
    barrio = Column(String(100), nullable=True)
    direccion = Column(String(300), nullable=True)
    numero_viviendas = Column(Integer, nullable=True)
    superficie_total_m2 = Column(Float, nullable=True)
    importe_total = Column(Float, nullable=True)
    anno_inicio = Column(Integer, nullable=True)
    anno_fin_previsto = Column(Integer, nullable=True)
    estado = Column(String(100))
    url_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
