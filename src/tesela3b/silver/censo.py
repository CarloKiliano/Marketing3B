"""Silver · Censo de Población y Vivienda 2020 (resultados por AGEB y manzana urbana).

El CSV de INEGI mezcla en un solo archivo totales de entidad, alcaldía, localidad, AGEB y manzana:
    AGEB != "0000" y MZA == "000"  -> fila de AGEB
    AGEB != "0000" y MZA != "000"  -> fila de manzana
Los valores protegidos por confidencialidad vienen como "*" (o "N/D") y se convierten a nulo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tesela3b import config as cfg

LLAVES = ["ENTIDAD", "NOM_ENT", "MUN", "NOM_MUN", "LOC", "NOM_LOC", "AGEB", "MZA"]
# Variables que usa el proyecto (nombres del descriptor de INEGI)
VARIABLES = [
    "POBTOT", "POB0_14", "POB15_64", "POB65_MAS",   # población y estructura de edad
    "TOTHOG", "POBHOG",                             # hogares censales
    "VIVTOT", "TVIVPARHAB", "PROM_OCUP",            # vivienda
    "VPH_AUTOM", "VPH_PC", "VPH_INTER", "VPH_REFRI", "VPH_LAVAD",  # bienes (proxy de ingreso)
    "GRAPROES", "PEA", "POCUPADA",                  # escolaridad y empleo
]
CONFIDENCIAL = ["*", "N/D"]


def leer_censo() -> pd.DataFrame:
    ruta = cfg.BRONZE / "censo2020" / "RESAGEBURB_09CSV20.csv"
    return pd.read_csv(ruta, dtype=str, encoding="utf-8-sig", usecols=LLAVES + VARIABLES)


def _numerico(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for v in VARIABLES:
        out[v] = pd.to_numeric(out[v].replace(CONFIDENCIAL, np.nan), errors="coerce")
    return out


def tabla_ageb(censo: pd.DataFrame) -> pd.DataFrame:
    """Una fila por AGEB urbana con CVEGEO de 13 caracteres."""
    a = censo[(censo["AGEB"] != "0000") & (censo["MZA"] == "000")]
    a = _numerico(a)
    a["CVEGEO"] = a["ENTIDAD"] + a["MUN"] + a["LOC"] + a["AGEB"]
    return a.reset_index(drop=True)


def tabla_manzana(censo: pd.DataFrame) -> pd.DataFrame:
    """Una fila por manzana con CVEGEO de 16 caracteres y su AGEB (13)."""
    m = censo[(censo["AGEB"] != "0000") & (censo["MZA"] != "000")]
    m = _numerico(m)
    m["cvegeo_ageb"] = m["ENTIDAD"] + m["MUN"] + m["LOC"] + m["AGEB"]
    m["CVEGEO"] = m["cvegeo_ageb"] + m["MZA"]
    return m.reset_index(drop=True)


def pct(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Porcentaje acotado a [0, 100]; nulo si el denominador es 0 o nulo."""
    d = denominador.where(denominador > 0)
    return (100 * numerador / d).clip(0, 100)


def perfil_ageb(a: pd.DataFrame) -> pd.DataFrame:
    """Indicadores derivados por AGEB. Los porcentajes 'sin X' son proxies de menor ingreso."""
    return pd.DataFrame({
        "CVEGEO": a["CVEGEO"],
        "cve_mun": a["MUN"],
        "alcaldia": a["NOM_MUN"],
        "poblacion": a["POBTOT"],
        "hogares": a["TOTHOG"],
        "viviendas_habitadas": a["TVIVPARHAB"],
        "personas_por_hogar": (a["POBHOG"] / a["TOTHOG"].where(a["TOTHOG"] > 0)).round(2),
        "escolaridad_promedio": a["GRAPROES"],
        "pct_0_14": pct(a["POB0_14"], a["POBTOT"]).round(1),
        "pct_65_mas": pct(a["POB65_MAS"], a["POBTOT"]).round(1),
        "pct_ocupados": pct(a["POCUPADA"], a["PEA"]).round(1),
        "pct_sin_auto": (100 - pct(a["VPH_AUTOM"], a["TVIVPARHAB"])).round(1),
        "pct_sin_computadora_censo": (100 - pct(a["VPH_PC"], a["TVIVPARHAB"])).round(1),
        "pct_sin_internet_censo": (100 - pct(a["VPH_INTER"], a["TVIVPARHAB"])).round(1),
    })


def demanda_manzana(m: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Hogares por manzana. Si el dato es confidencial se estima con las personas por hogar de su AGEB."""
    pph = (a["POBHOG"] / a["TOTHOG"].where(a["TOTHOG"] > 0)).set_axis(a["CVEGEO"])
    estimado = (m["POBTOT"] / m["cvegeo_ageb"].map(pph)).round()
    imputado = m["TOTHOG"].isna() & m["POBTOT"].gt(0) & estimado.notna()
    return pd.DataFrame({
        "CVEGEO": m["CVEGEO"],
        "cvegeo_ageb": m["cvegeo_ageb"],
        "poblacion": m["POBTOT"],
        "hogares": m["TOTHOG"].where(~imputado, estimado),
        "hogares_imputado": imputado,
    })
