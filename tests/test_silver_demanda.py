"""Tests de Silver demanda con datos sintéticos (no requieren los archivos de INEGI)."""
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from tesela3b import config as cfg
from tesela3b.silver import censo as cs
from tesela3b.silver import demanda as dm
from tesela3b.silver.esquemas import AGEB_PERFIL, MANZANAS_DEMANDA, validar


def fila_censo(mun="007", loc="0001", ageb="0000", mza="000", **valores):
    base = {"ENTIDAD": "09", "NOM_ENT": "Ciudad de México", "MUN": mun, "NOM_MUN": "Iztapalapa",
            "LOC": loc, "NOM_LOC": "Iztapalapa", "AGEB": ageb, "MZA": mza}
    base.update({v: "0" for v in cs.VARIABLES})
    base.update({k: str(v) for k, v in valores.items()})
    return base


def censo_sintetico():
    return pd.DataFrame([
        fila_censo(mun="000", loc="0000", POBTOT=1000),                     # total entidad
        fila_censo(loc="0000", POBTOT=1000),                                 # total alcaldía
        fila_censo(ageb="123A", POBTOT=400, TOTHOG=100, POBHOG=400, TVIVPARHAB=100,
                   VPH_AUTOM=30, VPH_PC=50, VPH_INTER=60, PEA=200, POCUPADA=190, POB0_14=80),
        fila_censo(ageb="123A", mza="001", POBTOT=200, TOTHOG=50),
        fila_censo(ageb="123A", mza="002", POBTOT=120, TOTHOG="*"),          # confidencial
        fila_censo(ageb="123A", mza="003", POBTOT=0, TOTHOG=0),              # no habitada
        fila_censo(ageb="456B", POBTOT=600, TOTHOG=150, POBHOG=600, TVIVPARHAB="*"),
    ])


def test_separa_ageb_y_manzana():
    c = censo_sintetico()
    a, m = cs.tabla_ageb(c), cs.tabla_manzana(c)
    assert a["CVEGEO"].tolist() == ["090070001123A", "090070001456B"]
    assert m["CVEGEO"].str.len().eq(16).all() and len(m) == 3


def test_confidencial_se_vuelve_nulo():
    a = cs.tabla_ageb(censo_sintetico())
    assert np.isnan(a.loc[1, "TVIVPARHAB"])


def test_perfil_ageb():
    p = cs.perfil_ageb(cs.tabla_ageb(censo_sintetico())).set_index("CVEGEO")
    r = p.loc["090070001123A"]
    assert r.pct_sin_auto == 70.0 and r.pct_sin_computadora_censo == 50.0
    assert r.personas_por_hogar == 4.0 and r.pct_0_14 == 20.0 and r.pct_ocupados == 95.0
    assert np.isnan(p.loc["090070001456B", "pct_sin_auto"])   # denominador confidencial -> nulo


def test_hogares_imputados_con_personas_por_hogar_de_la_ageb():
    c = censo_sintetico()
    d = cs.demanda_manzana(cs.tabla_manzana(c), cs.tabla_ageb(c)).set_index("CVEGEO")
    assert d.loc["090070001123A002", "hogares"] == 30          # 120 personas / 4 por hogar
    assert d.loc["090070001123A002", "hogares_imputado"]
    assert not d.loc["090070001123A001", "hogares_imputado"]


def test_limpiar_coneval():
    crudo = pd.DataFrame([[None] * 28 for _ in range(3)])
    crudo[0] = ["09", "9", "15"]
    crudo[7] = ["090070001123A", "090070001456B", "150010001000A"]
    crudo[15] = ["12.5", "150", "1"]
    crudo[27] = ["bajo", "Muy bajo", "Alto"]
    c = dm.limpiar_coneval(crudo).set_index("CVEGEO")
    assert len(c) == 2                                         # solo CDMX (acepta "9" sin cero)
    assert c.loc["090070001456B", "pct_hacinamiento"] == 100   # acotado a 100
    assert c.loc["090070001123A", "grado_rezago"] == "Bajo"


def poligonos_ageb():
    # Dos cuadrados de 1 km x 1 km en EPSG:6369
    return gpd.GeoDataFrame({"CVEGEO": ["090070001123A", "090070001456B"]},
                            geometry=[box(480000, 2140000, 481000, 2141000), box(481000, 2140000, 482000, 2141000)],
                            crs=cfg.CRS_METRIC)


def test_construir_ageb_area_y_densidad():
    c = censo_sintetico()
    coneval = pd.DataFrame({"CVEGEO": ["090070001123A"], "pct_hacinamiento": [10.0], "grado_rezago": ["Bajo"],
                            "pct_sin_computadora": [50.0], "pct_sin_internet": [40.0],
                            "pct_sin_derechohabiencia": [30.0]})
    g = dm.construir_ageb(cs.tabla_ageb(c), poligonos_ageb(), coneval).set_index("CVEGEO")
    assert g.crs.to_string() == cfg.CRS_WEB
    assert abs(g.loc["090070001123A", "area_km2"] - 1) < 1e-6
    assert g.loc["090070001123A", "hogares_km2"] == 100
    assert pd.isna(g.loc["090070001456B", "grado_rezago"])      # sin CONEVAL -> nulo, no se pierde la AGEB
    validar(g.reset_index(), AGEB_PERFIL)


def test_construir_manzanas_puntos_dentro_y_solo_habitadas():
    c = censo_sintetico()
    pol = gpd.GeoDataFrame({"CVEGEO": ["090070001123A001", "090070001123A002", "090070001123A003"],
                            "TIPOMZA": ["Típica"] * 3},
                           geometry=[box(480000, 2140000, 480100, 2140100), box(480100, 2140000, 480200, 2140100),
                                     box(480200, 2140000, 480300, 2140100)], crs=cfg.CRS_METRIC)
    m = dm.construir_manzanas(cs.tabla_manzana(c), cs.tabla_ageb(c), pol)
    assert set(m["CVEGEO"]) == {"090070001123A001", "090070001123A002"}   # la de 0 habitantes se excluye
    puntos = m.to_crs(cfg.CRS_METRIC).set_index("CVEGEO").geometry
    poligono = pol.set_index("CVEGEO").geometry.buffer(0.01)
    assert all(poligono[k].contains(p) for k, p in puntos.items())
    assert m["area_m2"].eq(10000).all()
    validar(m, MANZANAS_DEMANDA)
