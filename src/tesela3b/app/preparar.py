"""Prepara el paquete de datos ligero que usa la app (src/tesela3b/app/datos/).

La app publicada no tiene acceso a data/ (no se sube a GitHub): todo lo que necesita se exporta aquí en
archivos pequeños (parquet / JSON / GeoJSON), sin geometrías pesadas: los hexágonos se dibujan a partir de su
código H3. Se corre con `python scripts/09_preparar_app.py` después de 06 y 08.
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd

from tesela3b import config as cfg
from tesela3b.gold import backtest as bt
from tesela3b.gold import demanda as gd
from tesela3b.gold import indice_h3 as ih
from tesela3b.gold import influencia as inf

SALIDA = cfg.ROOT / "src" / "tesela3b" / "app" / "datos"

COLS_HEX = ["h3", "alcaldia", "lat", "lon", "hogares", "hogares_sin_auto", "poblacion", "pct_sin_auto",
            "escolaridad_promedio", "pct_sin_internet", "comercio_500", "hd_competencia_500", "n_3b",
            "n_hard_discount", "n_conveniencia", "n_supermercado", "n_tradicional", "dist_3b_m", "factor_red",
            "capturada", "canibalizacion", "pct_canibalizacion", "indice", "indice_final", "cuota_3b_actual",
            "p_apertura", "valor_esperado", "prioridad", "kde_500", "voronoi", "isocrona_10", "cubierto_10"]


def _guardar_json(obj, nombre):
    (SALIDA / nombre).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


def _puntos(gdf: gpd.GeoDataFrame, cols) -> pd.DataFrame:
    g = gdf.to_crs(cfg.CRS_WEB)
    return pd.DataFrame({**{c: g[c].to_numpy() for c in cols}, "lat": g.geometry.y.round(6), "lon": g.geometry.x.round(6)})


def _geojson(gdf: gpd.GeoDataFrame, nombre: str, tolerancia_m: float = 15) -> None:
    g = gdf.to_crs(cfg.CRS_METRIC)
    g["geometry"] = g.geometry.simplify(tolerancia_m)
    g = g.to_crs(cfg.CRS_WEB)
    (SALIDA / nombre).write_text(g.to_json(drop_id=True, ensure_ascii=False), encoding="utf-8")


def ejecutar() -> dict:
    SALIDA.mkdir(parents=True, exist_ok=True)
    r = bt.ejecutar(escribir=False, n_boot=1000)
    t26 = r["tabla_2026"].copy()
    est26 = gpd.read_parquet(cfg.SILVER / f"establecimientos_{cfg.CORTE_ACTUAL}.parquet")
    est21 = gpd.read_parquet(cfg.SILVER / f"establecimientos_{cfg.CORTE_BACKTEST}.parquet")
    tiendas26 = est26[est26["cadena"].eq("3B")]

    # --- Hexágonos 2026 --------------------------------------------------------------------------
    of26 = ih.oferta_por_hexagono(est26)
    pares = ih.pares_cercanos(set(t26["h3"]) | set(of26["h3"]))
    red = inf.RedPeatonal.cargar()
    lim10 = inf.limite_caminando_m(10)
    pares_red = red.pares_alcance(t26["h3"], lim10) if red is not None else None
    t26["voronoi"] = inf.score_voronoi(t26, est26, pares).to_numpy()
    t26["isocrona_10"], metodo = inf.score_isocrona(t26, est26, pares, 10, red, pares_red)
    centros = gd.centros_metricos(t26["h3"])
    t26["lat"], t26["lon"] = centros["lat"].round(6).to_numpy(), centros["lon"].round(6).to_numpy()
    if red is not None:
        d = red.distancia_minima(inf._xy(tiendas26), centros[["x", "y"]].to_numpy(), lim10)
    else:
        from scipy.spatial import cKDTree
        d = cKDTree(inf._xy(tiendas26)).query(centros[["x", "y"]].to_numpy())[0] * cfg.FACTOR_RODEO
    t26["cubierto_10"] = d <= lim10
    # Nombre de referencia: la colonia y el CP más frecuentes entre los negocios del DENUE en el hexágono
    e = est26.to_crs(cfg.CRS_WEB)
    e = e.assign(h3=gd.celda(e.geometry.y.values, e.geometry.x.values))
    moda = lambda s_: s_.dropna().mode().iat[0] if s_.notna().any() else None
    ref = e.groupby("h3").agg(colonia=("nomb_asent", moda), cp=("cod_postal", moda))
    t26 = t26.join(ref, on="h3")
    t26["colonia"] = t26["colonia"].fillna("").str.title()
    hexs = pd.DataFrame(t26[COLS_HEX + ["colonia", "cp"] + list(bt.VARIABLES)].loc[:, lambda x: ~x.columns.duplicated()])
    hexs.to_parquet(SALIDA / "hexagonos.parquet", index=False)

    # --- Simulador: estado del Huff (2026) y pares --------------------------------------------------
    est, p = ih.estado_huff(t26[["h3", "demanda_objetivo"]], of26, pares)
    est[["D", "s3b", "i_hd", "den_sin_hd", "p3b"]].reset_index().rename(columns={"index": "h3"}) \
        .to_parquet(SALIDA / "estado_huff.parquet", index=False)
    p = p[p["origen"].isin(est.index) & p["destino"].isin(est.index)]
    p[["origen", "destino", "d"]].astype({"d": "float32"}).to_parquet(SALIDA / "pares_1km.parquet", index=False)
    if pares_red is not None:
        pr = pares_red[pares_red["d"] <= lim10]
        pr[["origen", "destino"]].to_parquet(SALIDA / "alcance_10min.parquet", index=False)

    # --- Tiendas y aperturas ------------------------------------------------------------------------
    hd26 = est26[est26["formato"].eq("Hard discount")]
    tiendas = pd.concat([
        _puntos(hd26, ["cadena", "nom_estab"]).assign(corte=cfg.CORTE_ACTUAL),
        _puntos(est21[est21["cadena"].eq("3B")], ["cadena", "nom_estab"]).assign(corte=cfg.CORTE_BACKTEST)])
    tiendas.to_parquet(SALIDA / "tiendas.parquet", index=False)

    u = r["universo"]
    umbral = u["p_apertura_oob"].quantile(0.90)
    alto = set(u.loc[u["p_apertura_oob"] >= umbral, "h3"])
    import h3
    vecinos_alto = {v for c in alto for v in h3.grid_disk(c, 1)}
    ap = r["aperturas"]
    ap_df = _puntos(ap, ["h3", "municipio", "fecha_alta"])
    ap_df["resultado"] = np.select([ap_df["h3"].isin(alto), ap_df["h3"].isin(vecinos_alto)],
                                   ["En zona marcada", "Junto a zona marcada"], "No anticipada")
    ap_df.to_parquet(SALIDA / "aperturas.parquet", index=False)
    bt_hex = u[["h3", "y", "p_apertura_oob"]].assign(top10=u["p_apertura_oob"] >= umbral)
    bt_hex.to_parquet(SALIDA / "backtest_hex.parquet", index=False)

    # --- Capas de territorio (Métodos) --------------------------------------------------------------
    limite = gpd.read_parquet(cfg.SILVER / "limite_cdmx.parquet")
    vor = inf.poligonos_voronoi(tiendas26, limite)
    _geojson(vor, "voronoi_3b.geojson", 20)
    if red is not None:
        xy = inf._xy(tiendas26)
        iso = gpd.GeoDataFrame(geometry=[red.isocrona(p_, lim10) for p_ in xy], crs=cfg.CRS_METRIC)
    else:
        iso = gpd.GeoDataFrame(geometry=tiendas26.to_crs(cfg.CRS_METRIC).buffer(lim10 / cfg.FACTOR_RODEO), crs=cfg.CRS_METRIC)
    _geojson(iso, "isocronas_3b.geojson", 25)
    alc = gpd.read_parquet(cfg.SILVER / "alcaldias.parquet")[["alcaldia", "geometry"]]
    _geojson(alc, "alcaldias.geojson", 40)

    # --- Métricas del backtest ------------------------------------------------------------------------
    ganancia = {}
    for n, g in r["ganancia"].items():
        idx = np.unique(np.linspace(0, len(g) - 1, 201).astype(int))
        ganancia[n] = {"x": g["pct_hexagonos"].iloc[idx].round(4).tolist(), "y": g["pct_aperturas"].iloc[idx].round(4).tolist()}
    metricas = {
        "universo": int(len(u)), "positivos": int(u["y"].sum()), "cobertura_etiqueta": r["cobertura"],
        "comparacion": r["comparacion"].round(4).to_dict(orient="records"),
        "pruebas": {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in r["pruebas"].items()},
        "coeficientes": r["coeficientes"].round(3).to_dict(orient="records"),
        "tops_2021": {n: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in a.items()
                          if k not in ("acierto", "dist_apertura_m")} for n, (_, a) in r["tops_2021"].items()},
        "huff_cv": {"auc_fuera_de_bloque": r["cv_huff"]["auc_fuera_de_bloque"], "elegidas": r["cv_huff"]["elegidas"]},
        "rejilla_huff": r["rejilla_huff"].astype({"radio_red_m": str}).round(4).to_dict(orient="records"),
        "cobertura_10min": r["cobertura_iso"], "metodo_isocrona": metodo, "ganancia": ganancia,
        "tiendas_3b": {cfg.CORTE_BACKTEST: int(est21["cadena"].eq("3B").sum()), cfg.CORTE_ACTUAL: int(len(tiendas26))},
        "parametros": ih.parametros(), "cortes": list(cfg.CORTES),
    }
    _guardar_json(metricas, "metricas.json")
    _guardar_json(r["modelo"], "modelo_preferencia.json")
    tam = {f.name: round(f.stat().st_size / 1e6, 2) for f in sorted(SALIDA.iterdir())}
    return {"archivos_mb": tam, "total_mb": round(sum(tam.values()), 2), "metodo_isocrona": metodo}
