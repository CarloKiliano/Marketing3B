"""Contratos de datos (pandera) de las tablas Silver. Si un dato rompe el contrato, el pipeline falla."""
try:
    import pandera.pandas as pa
except ImportError:  # versiones anteriores de pandera
    import pandera as pa

from tesela3b import config as cfg
from tesela3b.silver.denue import FORMATO

LON0, LAT0, LON1, LAT1 = cfg.BBOX_CDMX

ESTABLECIMIENTOS = pa.DataFrameSchema(
    {
        "id": pa.Column(str, unique=True),
        "corte": pa.Column(str, pa.Check.isin(cfg.CORTES)),
        "cadena": pa.Column(str, pa.Check.isin(list(FORMATO))),
        "formato": pa.Column(str, pa.Check.isin(sorted(set(FORMATO.values())))),
        "es_cadena": pa.Column(bool),
        "codigo_act": pa.Column(str, pa.Check.str_matches(r"^\d{6}$")),
        "cvegeo_ageb": pa.Column(str, pa.Check.str_length(13, 13), nullable=True),
        "latitud": pa.Column(float, pa.Check.in_range(LAT0, LAT1)),
        "longitud": pa.Column(float, pa.Check.in_range(LON0, LON1)),
        "n_registros": pa.Column(int, pa.Check.ge(1)),
    },
    strict=False, coerce=True,
)

TIENDAS_3B_ACTUAL = pa.DataFrameSchema(
    {
        "id": pa.Column(str, unique=True),
        "cadena": pa.Column(str, pa.Check.eq("3B")),
        "dist_3b_corte_anterior_m": pa.Column(float, pa.Check.ge(0)),
        "apertura": pa.Column(bool),
        "apertura_confirmada": pa.Column(bool),
    },
    checks=pa.Check(lambda d: (~d["apertura_confirmada"] | d["apertura"]).all(),
                    error="una apertura confirmada siempre debe ser apertura"),
    strict=False, coerce=True,
)


_PCT = pa.Check.in_range(0, 100)

AGEB_PERFIL = pa.DataFrameSchema(
    {
        "CVEGEO": pa.Column(str, [pa.Check.str_length(13, 13), pa.Check.str_startswith(cfg.CVE_ENT)], unique=True),
        "alcaldia": pa.Column(str),
        "poblacion": pa.Column(float, pa.Check.ge(0)),
        "hogares": pa.Column(float, pa.Check.ge(0), nullable=True),
        "area_km2": pa.Column(float, pa.Check.gt(0)),
        "hogares_km2": pa.Column(float, pa.Check.ge(0), nullable=True),
        "pct_sin_auto": pa.Column(float, _PCT, nullable=True),
        "pct_sin_computadora": pa.Column(float, _PCT, nullable=True),
        "pct_sin_internet": pa.Column(float, _PCT, nullable=True),
        "pct_hacinamiento": pa.Column(float, _PCT, nullable=True),
        "pct_sin_derechohabiencia": pa.Column(float, _PCT, nullable=True),
        "grado_rezago": pa.Column(str, pa.Check.isin(["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]), nullable=True),
    },
    strict=False, coerce=True,
)

MANZANAS_DEMANDA = pa.DataFrameSchema(
    {
        "CVEGEO": pa.Column(str, pa.Check.str_length(16, 16), unique=True),
        "cvegeo_ageb": pa.Column(str, pa.Check.str_length(13, 13)),
        "poblacion": pa.Column(float, pa.Check.gt(0)),
        "hogares": pa.Column(float, pa.Check.ge(0), nullable=True),
        "hogares_imputado": pa.Column(bool),
        "area_m2": pa.Column(float, pa.Check.gt(0)),
    },
    checks=pa.Check(lambda d: (d["hogares"].fillna(0) <= d["poblacion"]).all(),
                    error="una manzana no puede tener más hogares que habitantes"),
    strict=False, coerce=True,
)


def validar(df, esquema):
    """Valida sin la columna de geometría (pandera trabaja sobre pandas)."""
    return esquema.validate(df.drop(columns="geometry", errors="ignore"), lazy=True)
