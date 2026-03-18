"""
Modelos SQLAlchemy para indicadores estadísticos del INE.
Fuente: Instituto Nacional de Estadística (servicios.ine.es/wstempus/js)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from app.core.database import Base


class DatoINE(Base):
    """
    Serie histórica de indicadores estadísticos del INE para Getafe.
    Almacena datos en bruto (sin derivar) de las principales series:
      - 'ipv'          : Índice de Precios de Vivienda (base 2015=100)
      - 'transacciones': Número de compraventas de vivienda anuales/trimestrales
      - 'poblacion'    : Padrón municipal (habitantes)
    """
    __tablename__ = "datos_ine"

    id         = Column(Integer, primary_key=True)
    indicador  = Column(String(50), nullable=False)   # "ipv", "transacciones", "poblacion"
    anno       = Column(Integer, nullable=False, index=True)
    trimestre  = Column(Integer, nullable=True)        # 1-4; NULL = dato anual
    valor      = Column(Float, nullable=False)
    unidad     = Column(String(50))                    # "indice", "operaciones", "habitantes"
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_datos_ine_indicador_anno", "indicador", "anno"),
        UniqueConstraint("indicador", "anno", "trimestre", name="uq_dato_ine"),
    )
