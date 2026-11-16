"""Gold · Backtest temporal (Fase 4).

Pregunta: si en noviembre de 2021 3B hubiera usado este índice, ¿habría señalado los lugares donde
realmente abrió entre 2021 y 2026?

Diseño (sin fuga de información):
- Los scores se calculan SOLO con la oferta del DENUE 2021_11 (y la demanda del Censo 2020).
- Etiqueta: hexágono con al menos una apertura 3B confirmada (fecha de alta ≥ 2021-11) en el corte 2026_05.
- Universo: hexágonos con demanda que NO tenían una 3B en 2021 (los únicos donde se puede "abrir").
- Métricas: AUC (¿el hexágono con apertura queda arriba de uno sin apertura?), captura@k% (qué % de
  aperturas cae en el k% mejor rankeado), lift@k% (captura / k), precisión del Top 20 con separación.
- Incertidumbre: bootstrap por BLOQUES espaciales (las aperturas vecinas no son independientes).
- Calibración: validación cruzada por bloques espaciales (H3 res 6, ~36 km²): los parámetros se eligen
  en unos bloques y se evalúan en otros, para no premiar un modelo que solo memoriza Iztapalapa.
"""
from __future__ import annotations

import itertools
import math

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from tesela3b import config as cfg
from tesela3b.gold import demanda as gd

# ---------------------------------------------------------------------------
# Etiqueta
# ---------------------------------------------------------------------------
def aperturas(confirmadas: bool = True) -> gpd.GeoDataFrame:
    a = gpd.read_parquet(cfg.SILVER / "aperturas_3b.parquet")
    a = a[a["apertura_confirmada"] if confirmadas else a["apertura"]].to_crs(cfg.CRS_WEB)
    return a.assign(h3=gd.celda(a.geometry.y.values, a.geometry.x.values))


def etiquetar(indice: pd.DataFrame, ap: pd.DataFrame) -> pd.DataFrame:
    """Agrega y (apertura en el hexágono), y_vecindad (en el hexágono o un vecino) y la marca de universo."""
    out = indice.copy()
    con = ap["h3"].value_counts()
    out["n_aperturas"] = out["h3"].map(con).fillna(0).astype(int)
    out["y"] = (out["n_aperturas"] > 0).astype(int)
    vecindad = {v for c in con.index for v in h3.grid_disk(c, 1)}
    out["y_vecindad"] = out["h3"].isin(vecindad).astype(int)
    out["universo"] = out["n_3b"].fillna(0).eq(0)
    return out


def cobertura_etiqueta(indice: pd.DataFrame, ap: pd.DataFrame) -> dict:
    """¿Cuántas aperturas caen en el universo evaluable? (las demás se reportan, no se esconden)."""
    univ = set(indice.loc[indice["n_3b"].fillna(0).eq(0), "h3"])
    con_3b = set(indice.loc[indice["n_3b"].fillna(0).gt(0), "h3"])
    todos = set(indice["h3"])
    return {"aperturas": len(ap), "en_universo": int(ap["h3"].isin(univ).sum()),
            "en_hexagono_con_3b_2021": int(ap["h3"].isin(con_3b).sum()),
            "en_hexagono_sin_vivienda": int((~ap["h3"].isin(todos)).sum())}


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def auc(score, y) -> float:
    """AUC ROC = P(score de un positivo > score de un negativo); empates cuentan 1/2 (Mann-Whitney)."""
    score, y = np.asarray(score, float), np.asarray(y, int)
    n1, n0 = y.sum(), len(y) - y.sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(score)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _orden(score, semilla: int = cfg.SEMILLA) -> np.ndarray:
    """Orden descendente; los empates se rompen al azar (no a favor del modelo)."""
    rng = np.random.default_rng(semilla)
    return np.lexsort((rng.random(len(score)), -np.asarray(score, float)))


def curva_ganancia(score, y, pesos=None) -> pd.DataFrame:
    """% de hexágonos revisados (de mejor a peor) vs % de aperturas capturadas."""
    y = np.asarray(y, float) if pesos is None else np.asarray(y, float) * np.asarray(pesos, float)
    o = _orden(score)
    cap = np.cumsum(y[o]) / y.sum()
    return pd.DataFrame({"pct_hexagonos": np.arange(1, len(o) + 1) / len(o), "pct_aperturas": cap})


def captura_at(score, y, k: float, pesos=None) -> float:
    g = curva_ganancia(score, y, pesos)
    return float(g["pct_aperturas"].iloc[max(int(math.ceil(k * len(g))) - 1, 0)])


def metricas(score, y, ks=(0.05, 0.10, 0.20), pesos=None) -> dict:
    out = {"auc": auc(score, y)}
    for k in ks:
        c = captura_at(score, y, k, pesos)
        out[f"captura_{int(k * 100)}"] = c
        out[f"lift_{int(k * 100)}"] = c / k
    return out


# ---------------------------------------------------------------------------
# Bloques espaciales
# ---------------------------------------------------------------------------
RES_BLOQUE = 6   # ~36 km² por bloque: más grande que el área de influencia de una tienda (≤ 1 km)
N_FOLDS = 5


def bloques(celdas, res: int = RES_BLOQUE) -> pd.Series:
    return pd.Series([h3.cell_to_parent(c, res) for c in celdas], index=getattr(celdas, "index", None))


def asignar_folds(bloque: pd.Series, y: pd.Series, k: int = N_FOLDS) -> pd.Series:
    """Asigna bloques completos a k folds equilibrando el número de aperturas (voraz, determinista)."""
    pos = y.groupby(bloque.values).sum().sort_values(ascending=False, kind="stable")
    tam = bloque.value_counts()
    carga, hexs, fold_de = np.zeros(k), np.zeros(k), {}
    for b, p in pos.items():
        f = int(np.lexsort((hexs, carga))[0])     # menos aperturas; desempata con menos hexágonos
        fold_de[b] = f
        carga[f] += p
        hexs[f] += tam[b]
    return bloque.map(fold_de).astype(int)


def bootstrap_bloques(score, y, bloque, n: int = 1000, semilla: int = cfg.SEMILLA,
                      metrica=auc) -> tuple[float, float]:
    """IC 95% re-muestreando BLOQUES completos (respeta la dependencia espacial)."""
    rng = np.random.default_rng(semilla)
    score, y, bloque = np.asarray(score, float), np.asarray(y, int), np.asarray(bloque)
    ub, inv = np.unique(bloque, return_inverse=True)
    miembros = [np.flatnonzero(inv == i) for i in range(len(ub))]
    vals = []
    for _ in range(n):
        idx = np.concatenate([miembros[i] for i in rng.integers(0, len(ub), len(ub))])
        v = metrica(score[idx], y[idx])
        if not np.isnan(v):
            vals.append(v)
    return tuple(np.percentile(vals, [2.5, 97.5]).round(3))


def diferencia_auc(score_a, score_b, y, bloque, n: int = 1000, semilla: int = cfg.SEMILLA) -> dict:
    """AUC(a) − AUC(b) con bootstrap PAREADO por bloques: ¿a le gana a b de forma consistente?"""
    rng = np.random.default_rng(semilla)
    a, b, y, bloque = (np.asarray(v) for v in (score_a, score_b, y, bloque))
    ub, inv = np.unique(bloque, return_inverse=True)
    miembros = [np.flatnonzero(inv == i) for i in range(len(ub))]
    difs = []
    for _ in range(n):
        idx = np.concatenate([miembros[i] for i in rng.integers(0, len(ub), len(ub))])
        if y[idx].sum() > 0:
            difs.append(auc(a[idx], y[idx]) - auc(b[idx], y[idx]))
    difs = np.array(difs)
    return {"diferencia": auc(a, y) - auc(b, y), "ic_inf": float(np.percentile(difs, 2.5)),
            "ic_sup": float(np.percentile(difs, 97.5)), "p_mejor": float((difs > 0).mean())}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    c = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    m = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return c - m, c + m


def comparar(tabla: pd.DataFrame, scores: dict[str, str], bloque: pd.Series, n_boot: int = 1000) -> pd.DataFrame:
    """Métricas + IC por bloques para varios scores (columnas de `tabla`) sobre el mismo universo."""
    filas = []
    for nombre, col in scores.items():
        m = metricas(tabla[col], tabla["y"])
        lo, hi = bootstrap_bloques(tabla[col], tabla["y"], bloque, n=n_boot)
        filas.append({"modelo": nombre, **m, "auc_ic_inf": lo, "auc_ic_sup": hi,
                      "auc_vecindad": auc(tabla[col], tabla["y_vecindad"])})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Top N con separación: ¿cuántas zonas recomendadas en 2021 recibieron una 3B?
# ---------------------------------------------------------------------------
def aciertos_top(top: pd.DataFrame, ap: gpd.GeoDataFrame, universo: pd.DataFrame,
                 radio_m: float = cfg.MIN_DIST_CANDIDATAS_M) -> dict:
    """Zona acertada = hubo una apertura confirmada a ≤ radio_m de su centro.

    Línea base = la misma probabilidad para un hexágono elegible tomado al azar.
    """
    from scipy.spatial import cKDTree
    xy_ap = np.c_[ap.to_crs(cfg.CRS_METRIC).geometry.x, ap.to_crs(cfg.CRS_METRIC).geometry.y]
    arbol = cKDTree(xy_ap)

    def tasa(celdas):
        c = gd.centros_metricos(list(celdas))[["x", "y"]].to_numpy()
        d, _ = arbol.query(c)
        return d <= radio_m, d

    hit, d = tasa(top["h3"])
    base, _ = tasa(universo["h3"])
    return {"zonas": len(top), "aciertos": int(hit.sum()), "precision": float(hit.mean()),
            "ic": wilson(int(hit.sum()), len(top)),
            "tasa_azar": float(base.mean()), "lift": float(hit.mean() / base.mean()) if base.mean() else np.nan,
            "dist_mediana_apertura_m": float(np.median(d)), "acierto": hit, "dist_apertura_m": d}


# ---------------------------------------------------------------------------
# Validación cruzada espacial (calibración)
# ---------------------------------------------------------------------------
def rejilla(**ejes) -> list[dict]:
    claves = list(ejes)
    return [dict(zip(claves, v)) for v in itertools.product(*ejes.values())]


def validacion_cruzada(scores: pd.DataFrame, y: pd.Series, fold: pd.Series) -> dict:
    """`scores`: una columna por combinación de parámetros (mismo índice que y y fold).

    Para cada fold: se elige la combinación con mejor AUC en los OTROS folds y se mide en éste.
    Devuelve el AUC fuera de bloque (estimación honesta) y la combinación elegida en cada fold.
    """
    y, fold = np.asarray(y), np.asarray(fold)
    auc_por_fold, elegidas = [], []
    for f in np.unique(fold):
        entr, prueba = fold != f, fold == f
        aucs = {c: auc(scores[c].to_numpy()[entr], y[entr]) for c in scores.columns}
        mejor = max(aucs, key=aucs.get)
        elegidas.append(mejor)
        auc_por_fold.append(auc(scores[mejor].to_numpy()[prueba], y[prueba]))
    global_ = {c: auc(scores[c], y) for c in scores.columns}
    return {"auc_fuera_de_bloque": float(np.nanmean(auc_por_fold)), "auc_por_fold": auc_por_fold,
            "elegidas": elegidas, "auc_global": global_, "mejor_global": max(global_, key=global_.get)}


# ---------------------------------------------------------------------------
# Modelo de preferencia revelada (¿qué hace que 3B abra en un lugar?)
# ---------------------------------------------------------------------------
# Regresión logística regularizada sobre variables interpretables; se evalúa SIEMPRE fuera de bloque.
VARIABLES = {
    "log_indice": "Índice Huff (hogares nuevos, Fase 3)",
    "cuota_3b": "Cuota 3B actual (exposición a canibalización)",
    "log_comercio_500": "Comercio de barrio a ≤ 500 m (tienditas + OXXO)",
    "log_hd_competencia_500": "Neto/Bodega Aurrera a ≤ 500 m",
    "fuera_red": "Fuera del radio operativo (> 2.5 km de una 3B)",
    "pct_sin_auto": "% hogares sin auto",
    "escolaridad_promedio": "Escolaridad promedio (años)",
}
C_LOGIT = 0.5   # regularización L2 moderada (resultados estables entre 0.1 y 1)


def suma_vecinos(tabla: pd.DataFrame, pares: pd.DataFrame, columna: str, radio_m: float) -> pd.Series:
    """Suma de `columna` en los hexágonos a ≤ radio_m de cada hexágono (incluido él mismo)."""
    p = pares[pares["d"] <= radio_m]
    v = p["origen"].map(tabla.set_index("h3")[columna]).fillna(0)
    return tabla["h3"].map(v.groupby(p["destino"]).sum()).fillna(0)


def agregar_variables(tabla: pd.DataFrame, pares: pd.DataFrame) -> pd.DataFrame:
    t = tabla.copy()
    t["comercio_500"] = (suma_vecinos(t, pares, "n_tradicional", 500)
                         + suma_vecinos(t, pares, "n_conveniencia", 500))
    t["hd_competencia_500"] = suma_vecinos(t, pares, "n_hard_discount", 500)
    t["log_indice"] = np.log1p(t["indice"].clip(lower=0))
    t["cuota_3b"] = t["cuota_3b_actual"]
    t["log_comercio_500"] = np.log1p(t["comercio_500"])
    t["log_hd_competencia_500"] = np.log1p(t["hd_competencia_500"])
    t["fuera_red"] = (t["dist_3b_m"].fillna(np.inf) > cfg.RADIO_OPERATIVO_M).astype(int)
    return t


def modelo_preferencia():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), LogisticRegression(C=C_LOGIT, max_iter=5000))


def predicciones_fuera_de_bloque(X: pd.DataFrame, y: pd.Series, fold: pd.Series) -> tuple[np.ndarray, list]:
    """Probabilidad de cada hexágono predicha por un modelo que NO vio su bloque."""
    oof, coefs = np.zeros(len(X)), []
    for f in sorted(np.unique(fold)):
        entr, prueba = (fold != f).to_numpy(), (fold == f).to_numpy()
        mod = modelo_preferencia().fit(X[entr], y[entr])
        oof[prueba] = mod.predict_proba(X[prueba])[:, 1]
        coefs.append(mod[-1].coef_[0])
    return oof, coefs


def exportar_modelo(mod, columnas) -> dict:
    """Coeficientes en JSON: la app puede calcular la probabilidad sin scikit-learn."""
    esc, lr = mod[0], mod[-1]
    return {"variables": list(columnas), "media": esc.mean_.tolist(), "escala": esc.scale_.tolist(),
            "coef": lr.coef_[0].tolist(), "intercepto": float(lr.intercept_[0]), "C": C_LOGIT}


def predecir(modelo_json: dict, X: pd.DataFrame) -> np.ndarray:
    z = (X[modelo_json["variables"]].to_numpy() - np.array(modelo_json["media"])) / np.array(modelo_json["escala"])
    return 1 / (1 + np.exp(-(z @ np.array(modelo_json["coef"]) + modelo_json["intercepto"])))


def valor_esperado(p_apertura, indice_final) -> pd.Series:
    """Regla de decisión final: hogares nuevos esperados = P(zona tipo 3B) × hogares nuevos (índice Huff).

    El modelo de preferencia dice si la zona se parece a donde 3B tiene éxito; el índice dice cuánto vale.
    """
    return pd.Series(np.asarray(p_apertura) * np.clip(np.asarray(indice_final, float), 0, None),
                     index=getattr(indice_final, "index", None))


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------
LAMBDAS, BETAS, RADIOS_RED = (0.25, 0.5, 0.75, 1.0), (200, 350, 500), (1500, 2000, 2500, 3000, None)


def tabla_corte(corte: str, m, dem):
    """Índice de la Fase 3 + variables del modelo para un corte; devuelve (tabla, oferta, pares, establecimientos)."""
    from tesela3b.gold import indice_h3 as ih
    est = gpd.read_parquet(cfg.SILVER / f"establecimientos_{corte}.parquet")
    oferta = ih.oferta_por_hexagono(est)
    pares = ih.pares_cercanos(set(dem["h3"]) | set(oferta["h3"]))
    idx = ih.construir_indice(corte, m, dem)
    return agregar_variables(idx, pares), oferta, pares, est


def calibrar_huff(tabla: pd.DataFrame, dem, oferta, pares, fold) -> tuple[pd.DataFrame, dict]:
    """Rejilla λ × β × radio de red, evaluada con validación cruzada por bloques."""
    from tesela3b.gold import indice_h3 as ih
    cols = {}
    for lam, beta in itertools.product(LAMBDAS, BETAS):
        r = ih.calcular_indice(dem, oferta, pares, lam=lam, beta=beta).set_index("h3")
        ind = tabla["h3"].map(r["indice"]).to_numpy()
        for R in RADIOS_RED:
            fr = 1.0 if R is None else ih.factor_red(tabla["dist_3b_m"], radio=R).to_numpy()
            cols[(lam, beta, R)] = ind * fr
    S = pd.DataFrame({str(k): v for k, v in cols.items()})
    cv = validacion_cruzada(S, tabla["y"], fold)
    rej = pd.DataFrame([{"lambda": k[0], "beta_m": k[1], "radio_red_m": k[2] if k[2] else "sin límite",
                         "auc": cv["auc_global"][str(k)]} for k in cols]).sort_values("auc", ascending=False)
    return rej, cv


def ejecutar(escribir: bool = True, n_boot: int = 1000) -> dict:
    import json

    from tesela3b.gold import indice_h3 as ih
    from tesela3b.gold import influencia as inf

    m, dem = ih.preparar_demanda()
    t21, of21, pares21, est21 = tabla_corte(cfg.CORTE_BACKTEST, m, dem)
    ap = aperturas()
    cob = cobertura_etiqueta(t21, ap)
    t21 = etiquetar(t21, ap)

    # --- Territorio: Voronoi e isócronas (con la oferta de 2021) ----------------------------
    red = inf.RedPeatonal.cargar()
    t21["voronoi"] = inf.score_voronoi(t21, est21, pares21).to_numpy()
    pares_red = red.pares_alcance(t21["h3"], inf.limite_caminando_m(10)) if red is not None else None
    t21["isocrona_10"], metodo_iso = inf.score_isocrona(t21, est21, pares21, 10, red, pares_red)
    huff_simple = ih.calcular_indice(dem, of21, pares21, lam=1.0).set_index("h3")
    t21["huff_simple"] = t21["h3"].map(huff_simple["indice"]).to_numpy()

    u = t21[t21["universo"]].reset_index(drop=True)
    u["bloque"] = bloques(u["h3"]).to_numpy()
    u["fold"] = asignar_folds(u["bloque"], u["y"]).to_numpy()

    # --- Modelo de preferencia revelada (fuera de bloque) -----------------------------------
    X = u[list(VARIABLES)]
    u["p_apertura_oob"], coefs_fold = predicciones_fuera_de_bloque(X, u["y"], u["fold"])
    u["valor_esperado_oob"] = valor_esperado(u["p_apertura_oob"], u["indice_final"])
    mod = modelo_preferencia().fit(X, u["y"])
    modelo_json = exportar_modelo(mod, VARIABLES)
    coefs = pd.DataFrame({"variable": list(VARIABLES), "descripcion": list(VARIABLES.values()),
                          "coef": modelo_json["coef"], "coef_min_fold": np.min(coefs_fold, axis=0),
                          "coef_max_fold": np.max(coefs_fold, axis=0)})

    # --- Comparación de métodos -------------------------------------------------------------
    scores = {"Hogares en el hexágono": "hogares", "Hogares sin auto en el hexágono": "demanda_objetivo",
              "KDE 500 m (clásico)": "kde_500", "Voronoi (tienda más cercana)": "voronoi",
              "Isócrona 10 min (cobertura)": "isocrona_10", "Huff simple (λ = 1)": "huff_simple",
              "Índice H3 Fase 3 (Huff anidado + red)": "indice_final",
              "Modelo de preferencia revelada": "p_apertura_oob",
              "Valor esperado (preferencia × índice)": "valor_esperado_oob"}
    comp = comparar(u, scores, u["bloque"], n_boot=n_boot)
    comp["auc_promedio_folds"] = [np.mean([auc(u.loc[u.fold == f, c], u.loc[u.fold == f, "y"])
                                           for f in sorted(u.fold.unique())]) for c in scores.values()]
    ganancia = {n: curva_ganancia(u[c], u["y"]) for n, c in scores.items()}
    pruebas = {f"{a} vs {b}": diferencia_auc(u[scores[a]], u[scores[b]], u["y"], u["bloque"], n=n_boot)
               for a, b in [("Modelo de preferencia revelada", "KDE 500 m (clásico)"),
                            ("Valor esperado (preferencia × índice)", "KDE 500 m (clásico)"),
                            ("Huff simple (λ = 1)", "Voronoi (tienda más cercana)"),
                            ("Isócrona 10 min (cobertura)", "Voronoi (tienda más cercana)")]}

    # --- Calibración del Huff -----------------------------------------------------------------
    rej, cv_huff = calibrar_huff(u, dem, of21, pares21, u["fold"])

    # --- Top 20 que se habría recomendado en 2021 -----------------------------------------------
    tops = {}
    for nombre, col in {"Valor esperado (recomendación)": "valor_esperado_oob",
                        "Modelo de preferencia revelada": "p_apertura_oob",
                        "Índice H3 Fase 3": "indice_final", "KDE 500 m": "kde_500"}.items():
        top = ih.seleccionar_top(u, columna=col)
        tops[nombre] = (top, aciertos_top(top, ap, u))

    # --- Recomendación final 2026 (modelo entrenado con todo 2021 -> 2026) -----------------------
    t26, _, _, _ = tabla_corte(cfg.CORTE_ACTUAL, m, dem)
    t26["p_apertura"] = predecir(modelo_json, t26)
    t26["valor_esperado"] = valor_esperado(t26["p_apertura"], t26["indice_final"])
    t26["prioridad"] = (100 * t26["valor_esperado"].rank(pct=True)).round(1)
    top26 = gpd.GeoDataFrame(ih.seleccionar_top(t26, columna="valor_esperado"), geometry="geometry", crs=cfg.CRS_WEB)

    res = {"cobertura": cob, "universo": u, "comparacion": comp, "ganancia": ganancia, "pruebas": pruebas, "coeficientes": coefs,
           "modelo": modelo_json, "rejilla_huff": rej, "cv_huff": cv_huff, "tops_2021": tops,
           "metodo_isocrona": metodo_iso, "tabla_2026": t26, "top_2026": top26, "aperturas": ap,
           "cobertura_iso": {c: inf.cobertura_isocrona(dem, e, 10, red) for c, e in
                             {cfg.CORTE_BACKTEST: est21,
                              cfg.CORTE_ACTUAL: gpd.read_parquet(cfg.SILVER / f"establecimientos_{cfg.CORTE_ACTUAL}.parquet")}.items()}}
    if escribir:
        cfg.GOLD.mkdir(parents=True, exist_ok=True)
        u.to_parquet(cfg.GOLD / f"backtest_{cfg.CORTE_BACKTEST}.parquet", index=False)
        t26.to_parquet(cfg.GOLD / f"prioridad_{cfg.CORTE_ACTUAL}.parquet", index=False)
        (cfg.GOLD / "modelo_preferencia.json").write_text(json.dumps(modelo_json, indent=2), encoding="utf-8")
        exportar_top_final(top26, cfg.OUTPUTS / f"top{cfg.TOP_N}_zonas_3b.geojson")
        rep = cfg.ROOT / "reports" / "backtest.md"
        rep.write_text(reporte(res), encoding="utf-8")
    return res


COLUMNAS_TOP_FINAL = ["posicion", "h3", "alcaldia", "valor_esperado", "prioridad", "p_apertura", "indice_final",
                      "indice", "capturada",
                      "canibalizacion", "pct_canibalizacion", "hogares", "hogares_sin_auto", "pct_sin_auto",
                      "escolaridad_promedio", "comercio_500", "hd_competencia_500", "dist_3b_m", "lat", "lon"]


def exportar_top_final(top: gpd.GeoDataFrame, ruta) -> None:
    t = top.copy()
    c = gd.centros_metricos(t["h3"]).set_index("h3")
    t["lat"], t["lon"] = t["h3"].map(c["lat"]).round(6), t["h3"].map(c["lon"]).round(6)
    t["p_apertura"] = t["p_apertura"].round(4)
    t["valor_esperado"] = t["valor_esperado"].round(1)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    g = gpd.GeoDataFrame(t[COLUMNAS_TOP_FINAL], geometry=t.geometry.values, crs=cfg.CRS_WEB)
    # Se escribe el texto directamente (GDAL borra el archivo antes de reescribirlo, lo que falla en carpetas
    # sincronizadas o sin permiso de borrado).
    ruta.write_text(g.to_json(drop_id=True, ensure_ascii=False), encoding="utf-8")


def reporte(r: dict) -> str:
    comp, cob, u = r["comparacion"], r["cobertura"], r["universo"]
    filas_comp = "\n".join(
        f"| {x.modelo} | {x.auc:.3f} ({x.auc_ic_inf:.2f}–{x.auc_ic_sup:.2f}) | {x.auc_promedio_folds:.3f} | "
        f"{x.captura_10:.0%} | {x.lift_10:.1f}× | {x.captura_20:.0%} | {x.auc_vecindad:.3f} |"
        for x in comp.sort_values("auc", ascending=False).itertuples())
    filas_pr = "\n".join(f"| {n} | {d['diferencia']:+.3f} | {d['ic_inf']:+.3f} a {d['ic_sup']:+.3f} | {d['p_mejor']:.0%} |"
                         for n, d in r["pruebas"].items())
    filas_top = "\n".join(f"| {n} | {a['aciertos']} de {a['zonas']} ({a['precision']:.0%}; IC {a['ic'][0]:.0%}–{a['ic'][1]:.0%}) | {a['tasa_azar']:.0%} | "
                          f"{a['lift']:.1f}× | {a['dist_mediana_apertura_m']:,.0f} m |" for n, (_, a) in r["tops_2021"].items())
    filas_coef = "\n".join(f"| {x.descripcion} | {x.coef:+.2f} | {x.coef_min_fold:+.2f} a {x.coef_max_fold:+.2f} |"
                           for x in r["coeficientes"].sort_values("coef", ascending=False).itertuples())
    rej = r["rejilla_huff"]
    filas_rej = "\n".join(f"| {x.Index + 1} | {x._1} | {x.beta_m} | {x.radio_red_m} | {x.auc:.3f} |"
                          for x in rej.head(8).reset_index(drop=True).itertuples())
    cv = r["cv_huff"]
    top = r["top_2026"]
    filas_t26 = "\n".join(f"| {x.posicion} | {x.alcaldia} | {x.valor_esperado:,.0f} | {x.p_apertura:.1%} | {x.indice_final:,.0f} | "
                          f"{x.pct_canibalizacion:.0f}% | {x.comercio_500:,.0f} | {x.dist_3b_m:,.0f} m | `{x.h3}` |"
                          for x in top.itertuples())
    alc = top["alcaldia"].value_counts()
    ci = r["cobertura_iso"]
    return f"""# Backtest 2021 → 2026 · ¿El modelo anticipa dónde abre 3B?

Generado automáticamente por `scripts/08_backtest.py`. AUC de 0.5 = azar.

**Diseño.** Todos los scores se calculan solo con el DENUE de noviembre de 2021 (y el Censo 2020). La etiqueta son las
{cob['aperturas']} aperturas 3B confirmadas hasta mayo de 2026. Universo: {len(u):,} hexágonos con vivienda y sin 3B en 2021
({u.y.sum()} con apertura; {cob['en_hexagono_con_3b_2021']} aperturas cayeron en un hexágono que ya tenía 3B y
{cob['en_hexagono_sin_vivienda']} en hexágonos sin vivienda). Intervalos al 95% con bootstrap por bloques espaciales
(H3 res {RES_BLOQUE}, ~36 km²); validación cruzada con {N_FOLDS} grupos de bloques.

## 1. Comparación de métodos
| Método | AUC (IC 95%) | AUC promedio por bloque | Captura en el 10% superior | Lift@10% | Captura en el 20% superior | AUC vecindad (±1 hexágono) |
| --- | --- | --- | --- | --- | --- | --- |
{filas_comp}

*AUC = probabilidad de que un hexágono donde 3B abrió quede arriba de uno donde no abrió (0.5 = azar).
Captura@10% = % de aperturas que caen en el 10% de hexágonos mejor calificados; lift = cuántas veces mejor que el azar.*
El modelo de preferencia revelada se evalúa con predicciones fuera de bloque (nunca vio la zona que califica).
Isócronas calculadas con: {r['metodo_isocrona']}.

**¿Las diferencias son reales?** Bootstrap pareado por bloques (mismas zonas re-muestreadas para ambos métodos):
| Comparación | Diferencia de AUC | IC 95% | % de re-muestreos en que gana el primero |
| --- | --- | --- | --- |
{filas_pr}

## 2. ¿Qué hace que 3B abra en un lugar? (modelo de preferencia revelada)
Regresión logística con variables estandarizadas: el coeficiente es el efecto de subir una desviación estándar.
| Variable | Coeficiente | Rango entre los {N_FOLDS} folds |
| --- | --- | --- |
{filas_coef}

## 3. Top {cfg.TOP_N} que se habría recomendado en noviembre de 2021
Acierto = hubo una apertura 3B confirmada a ≤ {cfg.MIN_DIST_CANDIDATAS_M} m del centro de la zona. Azar = la misma tasa
para un hexágono elegible cualquiera. Con solo 20 zonas los intervalos son anchos: la comparación fina entre métodos
se hace con el AUC sobre los ~6 mil hexágonos (sección 1); esta tabla es la lectura de negocio.
| Método | Aciertos | Tasa al azar | Lift | Distancia mediana a la apertura más cercana |
| --- | --- | --- | --- | --- |
{filas_top}

## 4. Calibración del Huff (λ, β, radio de red)
Mejor AUC fuera de bloque: **{cv['auc_fuera_de_bloque']:.3f}**. Combinación elegida en cada fold: {', '.join(cv['elegidas'])}.
| # | λ | β (m) | Radio de red | AUC |
| --- | --- | --- | --- | --- |
{filas_rej}

Lectura: λ = 1 (sin nido) predice mejor dónde abre 3B porque 3B **no evita** la canibalización: densifica. Eso dice cómo
decide 3B, no cuántas ventas pierde una tienda vecina; sin datos de ventas, λ = 0.5 se conserva como estimación
conservadora de hogares nuevos y canibalización (supuesto a recalibrar con datos internos).

## 5. Cobertura a pie (isócrona de 10 min)
Hogares sin auto con una 3B a ≤ 10 min caminando: **{ci[cfg.CORTE_BACKTEST]:.1%}** en 2021 → **{ci[cfg.CORTE_ACTUAL]:.1%}** en 2026.

## 6. Recomendación final · Top {cfg.TOP_N} 2026
Regla de decisión: **valor esperado = P(apertura) × índice H3**: los hogares nuevos que aporta la zona según el Huff,
ponderados por la probabilidad de que sea una zona "tipo 3B" según el modelo de preferencia. El modelo de preferencia solo
replica dónde abre 3B (y concentra la lista en el centro); el índice solo mide mercado; el producto equilibra ambos.
En la app, la prioridad de cada hexágono es el percentil de este valor en la CDMX.
| # | Alcaldía | Valor esperado | P(apertura) | Hogares nuevos (índice) | Canibalización | Comercio a 500 m | 3B más cercana | H3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{filas_t26}

Por alcaldía: {', '.join(f'{a} {n}' for a, n in alc.items())}.
"""
