"""Gold · Demanda por hexágono H3 (Fase 3).

Asignación dasimétrica: cada manzana habitada (punto) cae en un hexágono H3 res 9 y aporta sus
hogares; el perfil socioeconómico viene de su AGEB y se promedia ponderado por hogares.

También calcula la superficie KDE clásica (vista en clase) para compararla con el enfoque H3.
"""
from __future__ import annotations

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import Polygon

from tesela3b import config as cfg

PERFIL = ["pct_sin_auto", "pct_sin_computadora", "pct_sin_internet", "pct_hacinamiento",
          "pct_sin_derechohabiencia", "escolaridad_promedio", "personas_por_hogar"]
_A_METROS = Transformer.from_crs(cfg.CRS_WEB, cfg.CRS_METRIC, always_xy=True)


# ---------------------------------------------------------------------------
# Utilidades H3
# ---------------------------------------------------------------------------
def celda(lat: np.ndarray, lon: np.ndarray, res: int = cfg.H3_RES) -> list[str]:
    return [h3.latlng_to_cell(a, o, res) for a, o in zip(lat, lon)]


def centros_metricos(celdas) -> pd.DataFrame:
    """Centro de cada hexágono en EPSG:6369 (metros)."""
    latlon = np.array([h3.cell_to_latlng(c) for c in celdas])
    x, y = _A_METROS.transform(latlon[:, 1], latlon[:, 0])
    return pd.DataFrame({"h3": list(celdas), "x": x, "y": y, "lat": latlon[:, 0], "lon": latlon[:, 1]})


def poligono(c: str) -> Polygon:
    return Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(c)])


def a_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(df, geometry=[poligono(c) for c in df["h3"]], crs=cfg.CRS_WEB)


# ---------------------------------------------------------------------------
# Demanda por hexágono
# ---------------------------------------------------------------------------
def preparar_manzanas(manzanas: gpd.GeoDataFrame, ageb: pd.DataFrame) -> gpd.GeoDataFrame:
    """Cada manzana (punto) recibe su hexágono, el perfil de su AGEB y su demanda objetivo."""
    m = manzanas.copy()
    m["h3"] = celda(m.geometry.y.values, m.geometry.x.values)
    perfil = ageb.set_index("CVEGEO")[PERFIL]
    m = m.join(perfil, on="cvegeo_ageb")
    for v in PERFIL:  # AGEB sin dato -> mediana de la ciudad
        m[v] = m[v].fillna(perfil[v].median())
    m["hogares"] = m["hogares"].fillna(0)
    m["hogares_sin_auto"] = m["hogares"] * m["pct_sin_auto"] / 100
    m["demanda_objetivo"] = m[cfg.DEMANDA_OBJETIVO]
    m["cve_mun"] = m["CVEGEO"].str[2:5]
    return m


def demanda_por_hexagono(m: gpd.GeoDataFrame, alcaldias: pd.DataFrame | None = None) -> pd.DataFrame:
    """Suma hogares y demanda por hexágono; perfil = promedio ponderado por hogares."""
    g = m.groupby("h3")
    hex_ = g.agg(hogares=("hogares", "sum"), hogares_sin_auto=("hogares_sin_auto", "sum"),
                 demanda_objetivo=("demanda_objetivo", "sum"), poblacion=("poblacion", "sum"),
                 manzanas=("CVEGEO", "size"), cve_mun=("cve_mun", lambda s: s.mode().iat[0]))
    pesos = m["hogares"].where(m["hogares"] > 0, 1e-9)
    for v in PERFIL:
        hex_[v] = (m[v] * pesos).groupby(m["h3"]).sum() / pesos.groupby(m["h3"]).sum()
    hex_ = hex_.reset_index()
    if alcaldias is not None:
        hex_["alcaldia"] = hex_["cve_mun"].map(alcaldias.set_index("cve_mun")["alcaldia"])
    return hex_.round({v: 2 for v in PERFIL + ["hogares_sin_auto", "demanda_objetivo"]})


# ---------------------------------------------------------------------------
# KDE clásico (para la comparación metodológica)
# ---------------------------------------------------------------------------
def kde_en_puntos(origen_xy: np.ndarray, pesos: np.ndarray, destino_xy: np.ndarray, bw_m: float) -> np.ndarray:
    """Densidad kernel gaussiana ponderada evaluada en `destino_xy` (unidades de peso por km²).

    Se truncan los vecinos a 3 anchos de banda (más allá el kernel aporta < 1.1%).
    """
    arbol = cKDTree(origen_xy)
    vecinos = arbol.query_ball_point(destino_xy, r=3 * bw_m)
    k = 1 / (2 * np.pi * bw_m**2) * 1e6
    out = np.zeros(len(destino_xy))
    for i, idx in enumerate(vecinos):
        if idx:
            d2 = ((origen_xy[idx] - destino_xy[i]) ** 2).sum(axis=1)
            out[i] = (pesos[idx] * np.exp(-d2 / (2 * bw_m**2))).sum() * k
    return out


def agregar_kde(hex_: pd.DataFrame, m: gpd.GeoDataFrame, anchos=cfg.KDE_BANDWIDTHS_M) -> pd.DataFrame:
    """Agrega columnas kde_{bw}: densidad de la MISMA demanda objetivo, para comparar con H3."""
    mm = m.to_crs(cfg.CRS_METRIC)
    xy = np.c_[mm.geometry.x, mm.geometry.y]
    peso = np.nan_to_num(mm["demanda_objetivo"].to_numpy())
    centros = centros_metricos(hex_["h3"])[["x", "y"]].to_numpy()
    out = hex_.copy()
    for bw in anchos:
        out[f"kde_{bw}"] = kde_en_puntos(xy, peso, centros, bw).round(1)
    return out
