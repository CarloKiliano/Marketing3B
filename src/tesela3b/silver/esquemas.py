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


def validar(df, esquema):
    """Valida sin la columna de geometría (pandera trabaja sobre pandas)."""
    return esquema.validate(df.drop(columns="geometry", errors="ignore"), lazy=True)
