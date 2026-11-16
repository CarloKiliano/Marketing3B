"""Tests del backtest (métricas, bloques, validación cruzada) y de los territorios (Voronoi, isócronas)."""
import math

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from tesela3b import config as cfg
from tesela3b.gold import backtest as bt
from tesela3b.gold import indice_h3 as ih
from tesela3b.gold import influencia as inf

CENTRO = h3.latlng_to_cell(19.40, -99.15, cfg.H3_RES)


# --- Métricas -----------------------------------------------------------------------
def test_auc_casos_conocidos():
    y = [0, 0, 1, 1]
    assert bt.auc([1, 2, 3, 4], y) == 1.0
    assert bt.auc([4, 3, 2, 1], y) == 0.0
    assert bt.auc([1, 1, 1, 1], y) == 0.5          # empates = azar
    assert bt.auc([1, 3, 2, 4], y) == 0.75
    assert math.isnan(bt.auc([1, 2], [0, 0]))


def test_curva_ganancia_y_captura():
    score, y = np.arange(10, 0, -1), np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 1])
    g = bt.curva_ganancia(score, y)
    assert g["pct_aperturas"].iloc[-1] == 1.0 and g["pct_aperturas"].is_monotonic_increasing
    assert bt.captura_at(score, y, 0.2) == pytest.approx(2 / 3)
    m = bt.metricas(score, y, ks=(0.2,))
    assert m["lift_20"] == pytest.approx((2 / 3) / 0.2)


def test_wilson():
    lo, hi = bt.wilson(10, 20)
    assert lo == pytest.approx(0.299, abs=1e-3) and hi == pytest.approx(0.701, abs=1e-3)


# --- Bloques y validación cruzada ---------------------------------------------------------
def test_folds_no_parten_bloques_y_equilibran_aperturas():
    celdas = list(h3.grid_disk(CENTRO, 40))
    rng = np.random.default_rng(0)
    y = pd.Series((rng.random(len(celdas)) < 0.05).astype(int))
    blq = bt.bloques(pd.Series(celdas))
    fold = bt.asignar_folds(blq, y, k=3)
    assert (pd.DataFrame({"b": blq, "f": fold}).groupby("b")["f"].nunique() == 1).all()
    pos = y.groupby(fold).sum()
    assert pos.max() - pos.min() <= y.groupby(blq).sum().max()


def test_validacion_cruzada_elige_la_columna_informativa():
    rng = np.random.default_rng(1)
    n = 2000
    y = pd.Series((rng.random(n) < 0.1).astype(int))
    scores = pd.DataFrame({"bueno": y + rng.normal(0, 0.5, n), "ruido": rng.random(n)})
    fold = pd.Series(np.arange(n) % 4)
    cv = bt.validacion_cruzada(scores, y, fold)
    assert set(cv["elegidas"]) == {"bueno"} and cv["auc_fuera_de_bloque"] > 0.8


def test_bootstrap_y_diferencia_pareada():
    rng = np.random.default_rng(2)
    n = 3000
    y = (rng.random(n) < 0.1).astype(int)
    bueno, malo = y + rng.normal(0, 0.7, n), rng.random(n)
    blq = np.arange(n) % 30
    lo, hi = bt.bootstrap_bloques(bueno, y, blq, n=200)
    assert 0.5 < lo < hi <= 1
    d = bt.diferencia_auc(bueno, malo, y, blq, n=200)
    assert d["ic_inf"] > 0 and d["p_mejor"] == 1.0


def test_valor_esperado_no_negativo():
    v = bt.valor_esperado(pd.Series([0.5, 0.2]), pd.Series([100.0, -10.0]))
    assert v.tolist() == [50.0, 0.0]


def test_predecir_igual_a_sklearn():
    rng = np.random.default_rng(3)
    X = pd.DataFrame(rng.normal(size=(500, 3)), columns=["a", "b", "c"])
    y = (X["a"] + rng.normal(0, 1, 500) > 1).astype(int)
    mod = bt.modelo_preferencia().fit(X, y)
    assert np.allclose(bt.predecir(bt.exportar_modelo(mod, X.columns), X), mod.predict_proba(X)[:, 1])


# --- Territorios ----------------------------------------------------------------------------
def _tienda(c, cadena, formato="Hard discount"):
    lat, lon = h3.cell_to_latlng(c)
    return {"cadena": cadena, "formato": formato, "geometry": Point(lon, lat)}


@pytest.fixture
def mini():
    celdas = sorted(h3.grid_disk(CENTRO, 6))
    dem = pd.DataFrame({"h3": celdas, "demanda_objetivo": 10.0})
    return dem, ih.pares_cercanos(celdas)


def test_voronoi_no_suma_lo_que_ya_es_de_3b(mini):
    dem, pares = mini
    lejos = sorted(h3.grid_ring(CENTRO, 6))[0]
    est = gpd.GeoDataFrame([_tienda(CENTRO, "3B"), _tienda(lejos, "Neto")], geometry="geometry", crs=cfg.CRS_WEB)
    s = inf.score_voronoi(dem, est, pares).set_axis(dem["h3"])
    assert s[CENTRO] == 0                 # abrir junto a la propia 3B no gana nada (todo es canibalización)
    assert s[lejos] > 0                   # abrir junto a un Neto sí le quita hogares


def test_isocrona_solo_cuenta_hogares_sin_cobertura(mini):
    dem, pares = mini
    est = gpd.GeoDataFrame([_tienda(CENTRO, "3B")], geometry="geometry", crs=cfg.CRS_WEB)
    s, metodo = inf.score_isocrona(dem, est, pares, minutos=10)
    s = s.set_axis(dem["h3"])
    assert "rodeo" in metodo
    lejos = sorted(h3.grid_ring(CENTRO, 6))[0]
    assert s[CENTRO] == 0 and s[lejos] > 0
    assert 0 < inf.cobertura_isocrona(dem, est, 10) < 1


def test_poligonos_voronoi_una_celda_por_tienda():
    celdas = sorted(h3.grid_ring(CENTRO, 4))[::6]
    tiendas = gpd.GeoDataFrame([_tienda(c, "3B") for c in celdas], geometry="geometry", crs=cfg.CRS_WEB)
    recorte = gpd.GeoDataFrame(geometry=[gd_poligono_grande()], crs=cfg.CRS_WEB)
    v = inf.poligonos_voronoi(tiendas, recorte)
    assert len(v) == len(tiendas)
    for p in tiendas.geometry:
        assert v.contains(p).sum() == 1


def gd_poligono_grande():
    from shapely.geometry import box
    return box(-99.25, 19.30, -99.05, 19.50)


def test_red_peatonal_distancias():
    """Malla de 3x3 nodos separados ~100 m: la distancia por la red respeta las calles."""
    lat0, lon0, paso = 19.40, -99.15, 0.0009
    nodos = pd.DataFrame([{"osmid": 10 * i + j, "x": lon0 + j * paso, "y": lat0 + i * paso}
                          for i in range(3) for j in range(3)])
    aristas = []
    for i in range(3):
        for j in range(3):
            if j < 2:
                aristas.append((10 * i + j, 10 * i + j + 1))
            if i < 2:
                aristas.append((10 * i + j, 10 * (i + 1) + j))
    red = inf.RedPeatonal(nodos, pd.DataFrame(aristas, columns=["u", "v"]).assign(length=100.0))
    d = red.distancia_minima(red.xy[[0]], red.xy[[8]], limite=1000)   # esquina a esquina: 4 cuadras
    assert d[0] == pytest.approx(400, abs=1)
    assert np.isinf(red.distancia_minima(red.xy[[0]], red.xy[[8]], limite=300)[0])
    iso = red.isocrona(red.xy[0], 250)
    assert iso.contains(Point(*red.xy[1])) and not iso.contains(Point(*red.xy[8]))


def test_limite_caminando():
    assert inf.limite_caminando_m(10) == pytest.approx(750)
