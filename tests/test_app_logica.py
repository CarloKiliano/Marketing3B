"""Tests de la lógica de la app con el paquete de datos real (src/tesela3b/app/datos)."""
import math

import numpy as np
import pytest

from tesela3b.app import logica as lg

pytestmark = pytest.mark.skipif(not (lg.DATOS / "hexagonos.parquet").exists(),
                                reason="falta el paquete de datos de la app (scripts/09_preparar_app.py)")


@pytest.fixture(scope="module")
def datos():
    return lg.cargar()


def test_estrategia_neutral_ordena_como_el_valor_esperado(datos):
    h = datos.hexs
    s = lg.puntaje(h, 0.5)
    ve = h["p_apertura"] * h["indice_final"].clip(lower=0)
    assert np.allclose(s.rank(), ve.clip(lower=0).rank()) or abs(s.corr(ve, method="spearman") - 1) < 1e-9


def test_extremos_de_la_estrategia(datos):
    h = datos.hexs
    assert lg.puntaje(h, 1.0).corr(h["p_apertura"], method="spearman") > 0.999
    assert lg.puntaje(h, 0.0).corr(h["indice_final"].clip(lower=0), method="spearman") > 0.999


def test_top_respeta_filtros_y_separacion(datos):
    h = datos.hexs
    top = lg.seleccionar_top(h, lg.puntaje(h), n=30, separacion_m=800, alcaldias=["Iztapalapa", "Tláhuac"],
                             max_canibalizacion=10)
    assert len(top) == 30 and top["alcaldia"].isin(["Iztapalapa", "Tláhuac"]).all()
    assert (top["pct_canibalizacion"] <= 10).all() and (top["n_3b"] == 0).all()
    xy = top[["x", "y"]].to_numpy()
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    assert d[np.triu_indices(len(top), 1)].min() >= 800


def test_simulador_reproduce_el_indice(datos):
    h = datos.hexs.sample(25, random_state=1)
    for fila in h.itertuples():
        r = lg.simular(datos, fila.h3)
        assert r["capturada"] == pytest.approx(fila.capturada, abs=0.11)
        assert r["canibalizacion"] == pytest.approx(fila.canibalizacion, abs=0.11)
        assert r["indice_final"] == pytest.approx(fila.indice_final, abs=0.2)
        assert r["hogares_10min_sin_3b"] <= r["hogares_10min"]


def test_explicacion_suma_la_probabilidad(datos):
    fila = datos.hexs.iloc[123]
    e = lg.explicar(fila, datos.modelo)
    logit = e["contribucion"].sum() + datos.modelo["intercepto"]
    assert 1 / (1 + math.exp(-logit)) == pytest.approx(fila["p_apertura"], rel=1e-6)


def test_enlaces_y_kpis(datos):
    assert "19.400000,-99.150000" in lg.enlaces_mapa(19.4, -99.15)["maps"]
    k = lg.kpis(datos, lg.seleccionar_top(datos.hexs, lg.puntaje(datos.hexs)))
    assert k["tiendas"] > k["tiendas_antes"] and 0 < k["cobertura_antes"] < k["cobertura"] < 1
