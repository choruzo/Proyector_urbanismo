# Importar todos los modelos para que Alembic los detecte en autogenerate
# y para que SQLAlchemy registre las tablas en Base.metadata
from app.models.catastral import Barrio, Parcela, ValorSuelo          # noqa: F401
from app.models.construccion import ObraNueva, VisadoEstadistico       # noqa: F401
from app.models.alertas import Alerta, InversionPublica, ProyectoEMSV  # noqa: F401
