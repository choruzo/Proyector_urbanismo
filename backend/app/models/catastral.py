"""
Modelos SQLAlchemy para datos catastrales y valor del suelo.
Fuente principal: Dirección General del Catastro (sede.catastro.meh.es)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base


class Barrio(Base):
    """Barrios y distritos de Getafe con geometría geoespacial."""
    __tablename__ = "barrios"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(10), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    distrito = Column(String(100))
    # Geometría del polígono del barrio (EPSG:4326 — WGS84)
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    superficie_m2 = Column(Float)

    parcelas = relationship("Parcela", back_populates="barrio")
    valores_suelo = relationship("ValorSuelo", back_populates="barrio")


class Parcela(Base):
    """Datos de parcelas catastrales de Getafe."""
    __tablename__ = "parcelas"

    id = Column(Integer, primary_key=True)
    referencia_catastral = Column(String(20), unique=True, nullable=False, index=True)
    barrio_id = Column(Integer, ForeignKey("barrios.id"), nullable=True)
    direccion = Column(String(200))
    uso_principal = Column(String(50))      # residencial, comercial, industrial, etc.
    superficie_suelo_m2 = Column(Float)
    superficie_construida_m2 = Column(Float)
    anno_construccion = Column(Integer)
    numero_plantas = Column(Integer)
    numero_viviendas = Column(Integer)
    valor_catastral_suelo = Column(Float)
    valor_catastral_construccion = Column(Float)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)
    # Punto central de la parcela
    geom = Column(Geometry(geometry_type="POINT", srid=4326))

    barrio = relationship("Barrio", back_populates="parcelas")


class ValorSuelo(Base):
    """Serie histórica de valor medio del suelo por barrio y año."""
    __tablename__ = "valores_suelo"

    id = Column(Integer, primary_key=True)
    barrio_id = Column(Integer, ForeignKey("barrios.id"), nullable=False)
    anno = Column(Integer, nullable=False, index=True)
    trimestre = Column(Integer, nullable=True)   # 1-4, null = valor anual
    valor_medio_euro_m2 = Column(Float)          # €/m²
    valor_catastral_medio = Column(Float)
    fuente = Column(String(50))                  # catastro, ine, estimado
    created_at = Column(DateTime, default=datetime.utcnow)

    barrio = relationship("Barrio", back_populates="valores_suelo")
