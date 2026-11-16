"""Tests del índice de expansión (Huff anidado, canibalización, Top N, KDE) con datos sintéticos."""
import math

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from tesela3b import config as cfg
from tesela3b.gold import demanda as gd
from tesela3b.gold import indice_h3 as ih

CENTRO = h3.latlng_to_cell(19.40, -99.15, cfg.H3_RES)


def anillo(k):
    return sorted(h3.grid_ring(CENTRO, k))


def tienda(c, cadena="3B", formato="Hard discount"):
    lat, lon = h3.cell_to_latlng(c)
    return {"cadena": cadena, "formato": formato, "geometry": Point(lon, lat)}


def establecimientos(*filas):
    return gpd.GeoDataFrame(list(filas), geometry="geometry", crs=cfg.CRS_WEB)


def demanda_uniforme(celdas, d=100.0):
    return pd.DataFrame({"h3": list(celdas), "demanda_objetivo": d, "hogares": d})


@pytest.fixture
def zona():
    celdas = set(h3.grid_disk(CENTRO, 6))
    return celdas, ih.pares_cercanos(celdas)


# --- Pares y decaimiento -----------------------------------------------------
def test_pares_simetricos_e_incluyen_el_propio_hexagono(zona):
    _, pares = zona
    propio = pares[pares.origen == pares.destino]
    assert (propio.d == cfg.HUFF_DIST_MIN_M).all()
    ida = set(zip(pares.origen, pares.destino))
    assert all((b, a) in ida for a, b in ida)
    assert pares.d.max() <= cfg.HUFF_RADIO_MAX_M


def test_decaimiento():
    f = ih.decaimiento(np.array([0, cfg.HUFF_BETA_M, cfg.HUFF_RADIO_MAX_M + 1]))
    assert f[0] == 1 and math.isclose(f[1], math.exp(-1)) and f[2] == 0


# --- Huff -------------------------------------------------------------------------
def test_lambda_1_es_huff_clasico(zona):
    """Con λ = 1 y una sola celda de demanda, el resultado debe coincidir con la fórmula de Huff a mano."""
    celdas, pares = zona
    dem = demanda_uniforme([CENTRO], 1000.0)
    vecino = anillo(1)[0]
    of = ih.oferta_por_hexagono(establecimientos(tienda(vecino), tienda(vecino, "OXXO", "Conveniencia")))
    r = ih.calcular_indice(dem, of, pares, lam=1.0, alpha0=1.0).set_index("h3").loc[CENTRO]
    d = pares[(pares.origen == vecino) & (pares.destino == CENTRO)].d.iat[0]
    f = math.exp(-d / cfg.HUFF_BETA_M)
    g = math.exp(-cfg.HUFF_DIST_MIN_M / cfg.HUFF_BETA_M)   # la candidata está en el mismo hexágono
    s3b, sc = 1.0 * f, cfg.ATRACTIVO["Conveniencia"] * f
    den = 1.0 + s3b + sc
    assert r.capturada == pytest.approx(1000 * g / (den + g), abs=0.1)
    assert r.canibalizacion == pytest.approx(1000 * (s3b / den - s3b / (den + g)), abs=0.1)
    assert r.cuota_3b_actual == pytest.approx(s3b / den, abs=1e-3)


def test_canibalizacion_mayor_junto_a_una_3b(zona):
    celdas, pares = zona
    dem = demanda_uniforme(celdas)
    lejos = anillo(6)[0]
    of = ih.oferta_por_hexagono(establecimientos(tienda(CENTRO)))
    r = ih.calcular_indice(dem, of, pares).set_index("h3")
    assert r.loc[CENTRO, "pct_canibalizacion"] > 3 * r.loc[lejos, "pct_canibalizacion"]
    assert r.loc[lejos, "indice"] > r.loc[CENTRO, "indice"]


def test_nido_hace_mas_realista_la_canibalizacion(zona):
    celdas, pares = zona
    dem = demanda_uniforme(celdas)
    vecino = anillo(1)[0]
    filas = [tienda(CENTRO)] + [tienda(c, "Abarrotes", "Tradicional") for c in celdas for _ in range(5)]
    of = ih.oferta_por_hexagono(establecimientos(*filas))
    simple = ih.calcular_indice(dem, of, pares, lam=1.0).set_index("h3").loc[vecino, "pct_canibalizacion"]
    anidado = ih.calcular_indice(dem, of, pares, lam=0.5).set_index("h3").loc[vecino, "pct_canibalizacion"]
    assert anidado > simple


def test_indice_no_negativo_y_sin_oferta_no_hay_canibalizacion(zona):
    celdas, pares = zona
    dem = demanda_uniforme(celdas)
    vacia = ih.oferta_por_hexagono(establecimientos(tienda(anillo(6)[0], "OXXO", "Conveniencia")))
    r = ih.calcular_indice(dem, vacia, pares)
    assert (r.indice >= 0).all() and (r.canibalizacion.abs() < 1e-9).all()


# --- Red operativa y Top N -------------------------------------------------------
def test_factor_red():
    f = ih.factor_red(pd.Series([0, cfg.RADIO_OPERATIVO_M, cfg.RADIO_OPERATIVO_M + cfg.DECAIMIENTO_FUERA_RED_M, np.nan]))
    assert f.iloc[0] == 1 and f.iloc[1] == 1
    assert f.iloc[2] == pytest.approx(math.exp(-1), abs=1e-3) and f.iloc[3] == 0


def test_top_respeta_separacion_y_excluye_hexagonos_con_3b():
    celdas = list(h3.grid_disk(CENTRO, 8))
    idx = pd.DataFrame({"h3": celdas, "indice_final": np.arange(len(celdas), 0, -1, dtype=float),
                        "n_3b": [1] + [0] * (len(celdas) - 1)})   # el mejor tiene una 3B
    top = ih.seleccionar_top(idx, n=5, min_dist_m=900)
    assert celdas[0] not in set(top.h3)
    c = gd.centros_metricos(top.h3)
    for i in range(len(c)):
        for j in range(i + 1, len(c)):
            assert math.hypot(c.x[i] - c.x[j], c.y[i] - c.y[j]) >= 900
    assert top.posicion.tolist() == [1, 2, 3, 4, 5]


# --- Demanda y KDE ---------------------------------------------------------------
def test_demanda_por_hexagono_suma_y_pondera():
    lat, lon = h3.cell_to_latlng(CENTRO)
    m = gpd.GeoDataFrame({
        "CVEGEO": ["0900700011230001", "0900700011230002"], "cvegeo_ageb": ["0900700011230"] * 2,
        "poblacion": [40.0, 40.0], "hogares": [10.0, 30.0],
        "pct_sin_auto": [100.0, 0.0], **{v: [1.0, 1.0] for v in gd.PERFIL if v != "pct_sin_auto"},
    }, geometry=[Point(lon, lat), Point(lon + 1e-5, lat)], crs=cfg.CRS_WEB)
    m["h3"] = CENTRO
    m["hogares_sin_auto"] = m.hogares * m.pct_sin_auto / 100
    m["demanda_objetivo"] = m["hogares_sin_auto"]
    m["cve_mun"] = "007"
    h = gd.demanda_por_hexagono(m).iloc[0]
    assert h.hogares == 40 and h.hogares_sin_auto == 10
    assert h.pct_sin_auto == 25.0          # promedio ponderado por hogares: (10·100 + 30·0) / 40


def test_kde_un_punto():
    bw = 500.0
    dens = gd.kde_en_puntos(np.array([[0.0, 0.0]]), np.array([10.0]), np.array([[0.0, 0.0], [5000.0, 0]]), bw)
    assert dens[0] == pytest.approx(10 / (2 * math.pi * bw**2) * 1e6)
    assert dens[1] == 0
