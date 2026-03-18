"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-03-18 00:00:00.000000

Crea el esquema completo inicial del Proyector Urbanístico de Getafe:
  - Extensión PostGIS
  - Enums: tipo_promotor, estado_obra, tipo_alerta, fuente_alerta
  - Tablas: barrios, parcelas, valores_suelo, obras_nueva,
            visados_estadisticos, alertas, inversiones_publicas, proyectos_emsv
  - Índices sobre columnas frecuentemente consultadas
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 0. Extensión PostGIS — debe existir antes de crear columnas Geometry
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ------------------------------------------------------------------
    # 1. Enums
    # ------------------------------------------------------------------
    tipo_promotor = sa.Enum(
        "publico", "privado", "emsv", "mixto",
        name="tipopromotor",
    )
    tipo_promotor.create(op.get_bind(), checkfirst=True)

    estado_obra = sa.Enum(
        "proyectada", "licencia_solicitada", "licencia_concedida",
        "en_construccion", "finalizada", "paralizada",
        name="estadoobra",
    )
    estado_obra.create(op.get_bind(), checkfirst=True)

    tipo_alerta = sa.Enum(
        "licitacion", "adjudicacion", "convenio", "planeamiento", "emsv", "otro",
        name="tipoalerta",
    )
    tipo_alerta.create(op.get_bind(), checkfirst=True)

    fuente_alerta = sa.Enum(
        "bocm", "boe", "ayuntamiento", "emsv",
        name="fuentealerta",
    )
    fuente_alerta.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # 2. Tabla: barrios
    # ------------------------------------------------------------------
    op.create_table(
        "barrios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=10), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("distrito", sa.String(length=100), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, nullable=True
            ),
            nullable=True,
        ),
        sa.Column("superficie_m2", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index("ix_barrios_codigo", "barrios", ["codigo"], unique=True)

    # ------------------------------------------------------------------
    # 3. Tabla: parcelas
    # ------------------------------------------------------------------
    op.create_table(
        "parcelas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referencia_catastral", sa.String(length=20), nullable=False),
        sa.Column("barrio_id", sa.Integer(), nullable=True),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column("uso_principal", sa.String(length=50), nullable=True),
        sa.Column("superficie_suelo_m2", sa.Float(), nullable=True),
        sa.Column("superficie_construida_m2", sa.Float(), nullable=True),
        sa.Column("anno_construccion", sa.Integer(), nullable=True),
        sa.Column("numero_plantas", sa.Integer(), nullable=True),
        sa.Column("numero_viviendas", sa.Integer(), nullable=True),
        sa.Column("valor_catastral_suelo", sa.Float(), nullable=True),
        sa.Column("valor_catastral_construccion", sa.Float(), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, nullable=True
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["barrio_id"], ["barrios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referencia_catastral"),
    )
    op.create_index(
        "ix_parcelas_referencia_catastral", "parcelas", ["referencia_catastral"], unique=True
    )

    # ------------------------------------------------------------------
    # 4. Tabla: valores_suelo
    # ------------------------------------------------------------------
    op.create_table(
        "valores_suelo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("barrio_id", sa.Integer(), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=True),
        sa.Column("valor_medio_euro_m2", sa.Float(), nullable=True),
        sa.Column("valor_catastral_medio", sa.Float(), nullable=True),
        sa.Column("fuente", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["barrio_id"], ["barrios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_valores_suelo_anno", "valores_suelo", ["anno"])

    # ------------------------------------------------------------------
    # 5. Tabla: obras_nueva
    # ------------------------------------------------------------------
    op.create_table(
        "obras_nueva",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expediente", sa.String(length=50), nullable=True),
        sa.Column("nombre_proyecto", sa.String(length=300), nullable=True),
        sa.Column("promotor", sa.String(length=200), nullable=True),
        sa.Column(
            "tipo_promotor",
            sa.Enum("publico", "privado", "emsv", "mixto", name="tipopromotor"),
            nullable=True,
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "proyectada", "licencia_solicitada", "licencia_concedida",
                "en_construccion", "finalizada", "paralizada",
                name="estadoobra",
            ),
            nullable=True,
        ),
        sa.Column("uso", sa.String(length=100), nullable=True),
        sa.Column("direccion", sa.String(length=300), nullable=True),
        sa.Column("barrio", sa.String(length=100), nullable=True),
        sa.Column("referencia_catastral", sa.String(length=20), nullable=True),
        sa.Column("numero_viviendas", sa.Integer(), nullable=True),
        sa.Column("superficie_total_m2", sa.Float(), nullable=True),
        sa.Column("numero_plantas", sa.Integer(), nullable=True),
        sa.Column("fecha_solicitud_licencia", sa.Date(), nullable=True),
        sa.Column("fecha_concesion_licencia", sa.Date(), nullable=True),
        sa.Column("fecha_inicio_obras", sa.Date(), nullable=True),
        sa.Column("fecha_fin_obras", sa.Date(), nullable=True),
        sa.Column("presupuesto_ejecucion", sa.Float(), nullable=True),
        sa.Column("fuente", sa.String(length=100), nullable=True),
        sa.Column("url_fuente", sa.Text(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, nullable=True
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expediente"),
    )
    op.create_index("ix_obras_nueva_expediente", "obras_nueva", ["expediente"], unique=True)

    # ------------------------------------------------------------------
    # 6. Tabla: visados_estadisticos
    # ------------------------------------------------------------------
    op.create_table(
        "visados_estadisticos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=True),
        sa.Column("tipo_obra", sa.String(length=100), nullable=True),
        sa.Column("uso", sa.String(length=100), nullable=True),
        sa.Column("numero_visados", sa.Integer(), nullable=True),
        sa.Column("numero_viviendas", sa.Integer(), nullable=True),
        sa.Column("superficie_m2", sa.Float(), nullable=True),
        sa.Column("presupuesto_total", sa.Float(), nullable=True),
        sa.Column("fuente", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visados_estadisticos_anno", "visados_estadisticos", ["anno"])

    # ------------------------------------------------------------------
    # 7. Tabla: alertas
    # ------------------------------------------------------------------
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "tipo",
            sa.Enum("licitacion", "adjudicacion", "convenio", "planeamiento", "emsv", "otro",
                    name="tipoalerta"),
            nullable=True,
        ),
        sa.Column(
            "fuente",
            sa.Enum("bocm", "boe", "ayuntamiento", "emsv", name="fuentealerta"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("fecha_publicacion", sa.Date(), nullable=False),
        sa.Column("fecha_deteccion", sa.DateTime(), nullable=True),
        sa.Column("importe_euros", sa.Float(), nullable=True),
        sa.Column("organismo_contratante", sa.String(length=300), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=True),
        sa.Column("relevancia_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alertas_fecha_publicacion", "alertas", ["fecha_publicacion"])

    # ------------------------------------------------------------------
    # 8. Tabla: inversiones_publicas
    # ------------------------------------------------------------------
    op.create_table(
        "inversiones_publicas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("nombre_proyecto", sa.String(length=400), nullable=False),
        sa.Column("organismo", sa.String(length=200), nullable=True),
        sa.Column("tipo_actuacion", sa.String(length=200), nullable=True),
        sa.Column("importe_presupuestado", sa.Float(), nullable=True),
        sa.Column("importe_adjudicado", sa.Float(), nullable=True),
        sa.Column("importe_ejecutado", sa.Float(), nullable=True),
        sa.Column("estado", sa.String(length=100), nullable=True),
        sa.Column("barrio", sa.String(length=100), nullable=True),
        sa.Column("expediente_contratacion", sa.String(length=100), nullable=True),
        sa.Column("url_contrato", sa.Text(), nullable=True),
        sa.Column("fuente", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inversiones_publicas_anno", "inversiones_publicas", ["anno"])

    # ------------------------------------------------------------------
    # 9. Tabla: proyectos_emsv
    # ------------------------------------------------------------------
    op.create_table(
        "proyectos_emsv",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=300), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
        sa.Column("barrio", sa.String(length=100), nullable=True),
        sa.Column("direccion", sa.String(length=300), nullable=True),
        sa.Column("numero_viviendas", sa.Integer(), nullable=True),
        sa.Column("superficie_total_m2", sa.Float(), nullable=True),
        sa.Column("importe_total", sa.Float(), nullable=True),
        sa.Column("anno_inicio", sa.Integer(), nullable=True),
        sa.Column("anno_fin_previsto", sa.Integer(), nullable=True),
        sa.Column("estado", sa.String(length=100), nullable=True),
        sa.Column("url_info", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Eliminar tablas en orden inverso (respetando foreign keys)
    op.drop_table("proyectos_emsv")
    op.drop_table("inversiones_publicas")
    op.drop_table("alertas")
    op.drop_table("visados_estadisticos")
    op.drop_table("obras_nueva")
    op.drop_table("valores_suelo")
    op.drop_table("parcelas")
    op.drop_table("barrios")

    # Eliminar enums
    sa.Enum(name="fuentealerta").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tipoalerta").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="estadoobra").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tipopromotor").drop(op.get_bind(), checkfirst=True)
