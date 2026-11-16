"""Gold · Índice de potencial de expansión por hexágono H3 y Top 20 (Fase 3).

Pregunta de negocio: si 3B abre una tienda en el hexágono c, ¿cuántos hogares objetivo NUEVOS gana la
cadena? (descontando los que le quitaría a sus propias tiendas).

Modelo de Huff anidado (nested logit) con opción externa. Para cada hexágono de demanda h:
    f(d)      = exp(-d / β) si d ≤ radio máximo, 0 en otro caso
    I_n(h)    = Σ_{j ∈ nido n} A_j · f(d_jh)        atracción del nido n (hard discount, conveniencia,
                                                      supermercado, tradicional); 3B está en hard discount
    P(n | h)  = I_n^λ / (α0 + Σ_m I_m^λ)            elección del tipo de tienda (α0 = opción externa)
    P(j | n)  = A_j · f(d_jh) / I_n                  elección de la tienda dentro del nido
Una tienda candidata en c suma g = A_3B · f(d_ch) al nido hard discount:
    capturada(c)      = Σ_h D(h) · P'(HD | h) · g / I'_HD             hogares que irían a la tienda nueva
    canibalizacion(c) = Σ_h D(h) · [P(3B existentes) − P'(3B existentes)]   hogares que dejan otras 3B
    indice(c)         = capturada − canibalizacion                     hogares NUEVOS para la cadena
Con λ = 1 se recupera el Huff clásico; con λ < 1 la tienda nueva compite sobre todo dentro de su nido.

`construir_indice(corte)` solo usa la oferta de ese corte: con 2021_11 produce el backtest y con 2026_05
la recomendación final, con el mismo código y sin información del futuro.
"""
from __future__ import annotations

import json
import math

import geopandas as gpd
import h3
import numpy as np
import pandas as pd

from tesela3b import config as cfg
from tesela3b.gold import demanda as gd


def parametros() -> dict:
    """Parámetros vigentes del modelo (se guardan junto a cada resultado para reproducibilidad)."""
    return {
        "h3_res": cfg.H3_RES, "demanda_objetivo": cfg.DEMANDA_OBJETIVO, "beta_m": cfg.HUFF_BETA_M,
        "radio_max_m": cfg.HUFF_RADIO_MAX_M, "dist_min_m": cfg.HUFF_DIST_MIN_M,
        "opcion_externa": cfg.HUFF_OPCION_EXTERNA, "lambda_nido": cfg.HUFF_LAMBDA_NIDO,
        "atractivo": dict(cfg.ATRACTIVO),
        "radio_operativo_m": cfg.RADIO_OPERATIVO_M, "decaimiento_fuera_red_m": cfg.DECAIMIENTO_FUERA_RED_M,
        "min_dist_top_m": cfg.MIN_DIST_CANDIDATAS_M, "top_n": cfg.TOP_N,
    }


# ---------------------------------------------------------------------------
# Oferta por hexágono
# ---------------------------------------------------------------------------
NIDOS = ["Hard discount", "Conveniencia", "Supermercado", "Tradicional"]


def _col(nido: str) -> str:
    return nido.lower().replace(" ", "_")


def oferta_por_hexagono(establecimientos: gpd.GeoDataFrame, atractivo: dict = cfg.ATRACTIVO) -> pd.DataFrame:
    """Por hexágono: número de tiendas y masa de atracción por nido (3B aparte, dentro de hard discount)."""
    e = establecimientos.to_crs(cfg.CRS_WEB)
    e = e.assign(h3=gd.celda(e.geometry.y.values, e.geometry.x.values))
    es_3b = e["cadena"].eq("3B")
    e["masa"] = np.where(es_3b, atractivo["3B"], e["formato"].map(atractivo).fillna(0))
    of = pd.DataFrame({"n_3b": es_3b.groupby(e["h3"]).sum(),
                       "masa_3b": e["masa"].where(es_3b, 0).groupby(e["h3"]).sum()})
    for nido in NIDOS:
        en_nido = e["formato"].eq(nido) & ~es_3b
        of[f"n_{_col(nido)}"] = en_nido.groupby(e["h3"]).sum()
        of[f"masa_{_col(nido)}"] = e["masa"].where(en_nido, 0).groupby(e["h3"]).sum()
    return of.reset_index()


# ---------------------------------------------------------------------------
# Pares de hexágonos cercanos
# ---------------------------------------------------------------------------
def anillos_necesarios(radio_m: float, res: int = cfg.H3_RES) -> int:
    paso = h3.average_hexagon_edge_length(res, "m") * math.sqrt(3)  # distancia entre centros vecinos
    return int(math.ceil(radio_m / paso))


def pares_cercanos(celdas, radio_m: float = cfg.HUFF_RADIO_MAX_M) -> pd.DataFrame:
    """Todos los pares (origen, destino) de celdas del universo a ≤ radio_m, con su distancia en metros."""
    universo = set(celdas)
    k = anillos_necesarios(radio_m)
    filas = [(o, d) for o in universo for d in h3.grid_disk(o, k) if d in universo]
    pares = pd.DataFrame(filas, columns=["origen", "destino"])
    c = gd.centros_metricos(sorted(universo)).set_index("h3")
    xo, yo = c.loc[pares["origen"], ["x", "y"]].to_numpy().T
    xd, yd = c.loc[pares["destino"], ["x", "y"]].to_numpy().T
    pares["d"] = np.maximum(np.hypot(xo - xd, yo - yd), cfg.HUFF_DIST_MIN_M)
    return pares[pares["d"] <= radio_m].reset_index(drop=True)


def decaimiento(d: np.ndarray, beta: float = cfg.HUFF_BETA_M, radio: float = cfg.HUFF_RADIO_MAX_M) -> np.ndarray:
    return np.where(d <= radio, np.exp(-d / beta), 0.0)


# ---------------------------------------------------------------------------
# Modelo de Huff e índice
# ---------------------------------------------------------------------------
def _potencia(x: pd.Series, lam: float) -> pd.Series:
    return np.where(x > 0, np.power(x.clip(lower=0), lam), 0.0)


def calcular_indice(demanda: pd.DataFrame, oferta: pd.DataFrame, pares: pd.DataFrame,
                    alpha0: float = cfg.HUFF_OPCION_EXTERNA, a_nueva: float = cfg.ATRACTIVO["3B"],
                    beta: float = cfg.HUFF_BETA_M, lam: float = cfg.HUFF_LAMBDA_NIDO) -> pd.DataFrame:
    """Índice incremental (Huff anidado) para cada hexágono con demanda (candidato)."""
    p = pares.copy()
    p["f"] = decaimiento(p["d"].to_numpy(), beta)
    of = oferta.set_index("h3")
    masas = ["masa_3b"] + [f"masa_{_col(n)}" for n in NIDOS]

    # 1) Atracción actual de cada nido sobre cada hexágono de demanda h (origen = tienda, destino = h)
    for mcol in masas:
        p[mcol] = p["origen"].map(of[mcol]).fillna(0) * p["f"]
    atr = p.groupby("destino")[masas].sum()
    est = pd.DataFrame(index=demanda["h3"])
    est["D"] = demanda.set_index("h3")["demanda_objetivo"]
    atr = atr.reindex(est.index).fillna(0)
    est["s3b"] = atr["masa_3b"]
    est["i_hd"] = atr["masa_3b"] + atr["masa_hard_discount"]
    v_otros = sum(_potencia(atr[f"masa_{_col(n)}"], lam) for n in NIDOS[1:])
    est["v_hd"] = _potencia(est["i_hd"], lam)
    est["den_sin_hd"] = alpha0 + v_otros
    est["den"] = est["den_sin_hd"] + est["v_hd"]
    est["p3b"] = np.where(est["i_hd"] > 0, est["v_hd"] / est["den"] * est["s3b"] / est["i_hd"].where(est["i_hd"] > 0, 1), 0)
    est["cuota_hd"] = est["v_hd"] / est["den"]

    # 2) Efecto de una tienda nueva en c sobre cada h a su alcance (origen = c, destino = h)
    q = p[p["origen"].isin(est.index) & p["destino"].isin(est.index)][["origen", "destino", "f"]]
    q = q.join(est[["D", "s3b", "i_hd", "den_sin_hd", "p3b"]], on="destino")
    g = a_nueva * q["f"]
    i_hd2 = q["i_hd"] + g
    p_hd2 = np.power(i_hd2, lam) / (q["den_sin_hd"] + np.power(i_hd2, lam))
    q["capturada"] = q["D"] * p_hd2 * g / i_hd2
    q["canibalizacion"] = q["D"] * (q["p3b"] - p_hd2 * q["s3b"] / i_hd2)
    q["accesible"] = q["D"] * q["f"]
    res = q.groupby("origen")[["capturada", "canibalizacion", "accesible"]].sum()

    out = demanda.set_index("h3").join(res).join(est[["p3b", "cuota_hd"]].rename(
        columns={"p3b": "cuota_3b_actual", "cuota_hd": "cuota_hard_discount"}))
    out[["capturada", "canibalizacion", "accesible"]] = out[["capturada", "canibalizacion", "accesible"]].fillna(0)
    out["indice"] = out["capturada"] - out["canibalizacion"]
    out["pct_canibalizacion"] = (100 * out["canibalizacion"] / out["capturada"].where(out["capturada"] > 0)).fillna(0)
    out["score"] = (100 * out["indice"].rank(pct=True)).round(1)
    out["rank"] = out["indice"].rank(ascending=False, method="first").astype(int)
    return out.reset_index().round({"capturada": 1, "canibalizacion": 1, "accesible": 1, "indice": 1,
                                    "cuota_3b_actual": 3, "cuota_hard_discount": 3, "pct_canibalizacion": 1})


def distancia_a_3b(hex_: pd.DataFrame, establecimientos: gpd.GeoDataFrame) -> np.ndarray:
    """Distancia (m) del centro de cada hexágono a la tienda 3B más cercana del corte."""
    from scipy.spatial import cKDTree
    t = establecimientos[establecimientos["cadena"] == "3B"].to_crs(cfg.CRS_METRIC)
    centros = gd.centros_metricos(hex_["h3"])[["x", "y"]].to_numpy()
    if t.empty:
        return np.full(len(hex_), np.nan)
    dist, _ = cKDTree(np.c_[t.geometry.x, t.geometry.y]).query(centros)
    return dist.round(0)


def factor_red(dist_3b_m: pd.Series, radio: float = cfg.RADIO_OPERATIVO_M,
               escala: float = cfg.DECAIMIENTO_FUERA_RED_M) -> pd.Series:
    """1 dentro del radio operativo de la red 3B actual; decae exponencialmente fuera de él."""
    return np.exp(-np.clip(dist_3b_m.fillna(np.inf) - radio, 0, None) / escala).round(4)


# ---------------------------------------------------------------------------
# Top N con separación mínima
# ---------------------------------------------------------------------------
def seleccionar_top(indice: pd.DataFrame, n: int = cfg.TOP_N, min_dist_m: float = cfg.MIN_DIST_CANDIDATAS_M,
                    columna: str = "indice_final", excluir_con_3b: bool = True) -> pd.DataFrame:
    """Selección voraz: el mejor hexágono que esté a ≥ min_dist_m de todos los ya elegidos.

    Regla de negocio: no se recomienda abrir en un hexágono que ya tiene una tienda 3B.
    """
    candidatos = indice[indice["n_3b"].fillna(0) == 0] if excluir_con_3b and "n_3b" in indice else indice
    orden = candidatos.sort_values(columna, ascending=False)
    centros = gd.centros_metricos(orden["h3"]).set_index("h3")
    elegidos, xy = [], []
    for c in orden["h3"]:
        x, y = centros.at[c, "x"], centros.at[c, "y"]
        if all(math.hypot(x - a, y - b) >= min_dist_m for a, b in xy):
            elegidos.append(c)
            xy.append((x, y))
            if len(elegidos) == n:
                break
    top = indice.set_index("h3").loc[elegidos].reset_index()
    top.insert(0, "posicion", range(1, len(top) + 1))
    return top


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def construir_indice(corte: str, manzanas_prep: gpd.GeoDataFrame | None = None,
                     demanda: pd.DataFrame | None = None) -> gpd.GeoDataFrame:
    """Índice completo para un corte del DENUE. La demanda (Censo 2020) es la misma en ambos cortes."""
    if manzanas_prep is None or demanda is None:
        manzanas_prep, demanda = preparar_demanda()
    est = gpd.read_parquet(cfg.SILVER / f"establecimientos_{corte}.parquet")
    oferta = oferta_por_hexagono(est)
    pares = pares_cercanos(set(demanda["h3"]) | set(oferta["h3"]))
    idx = calcular_indice(demanda, oferta, pares)
    idx = idx.merge(oferta[[c for c in oferta.columns if not c.startswith("masa_")]], on="h3", how="left")
    conteos = [c for c in idx.columns if c.startswith("n_") and c != "n_3b"] + ["n_3b"]
    idx[conteos] = idx[conteos].fillna(0).astype(int)
    idx["dist_3b_m"] = distancia_a_3b(idx, est)
    idx["factor_red"] = factor_red(idx["dist_3b_m"])
    idx["indice_final"] = (idx["indice"] * idx["factor_red"]).round(1)
    idx["score"] = (100 * idx["indice_final"].rank(pct=True)).round(1)
    idx["rank"] = idx["indice_final"].rank(ascending=False, method="first").astype(int)
    idx.insert(1, "corte", corte)
    return gd.a_geodataframe(idx)


def preparar_demanda():
    manzanas = gpd.read_parquet(cfg.SILVER / "manzanas_demanda.parquet")
    ageb = gpd.read_parquet(cfg.SILVER / "ageb_perfil.parquet")
    alcaldias = gpd.read_parquet(cfg.SILVER / "alcaldias.parquet")
    m = gd.preparar_manzanas(manzanas, ageb)
    dem = gd.demanda_por_hexagono(m, alcaldias)
    dem = gd.agregar_kde(dem, m)
    return m, dem


COLUMNAS_TOP = ["posicion", "h3", "alcaldia", "indice_final", "indice", "factor_red", "capturada",
                "canibalizacion", "pct_canibalizacion",
                "hogares", "hogares_sin_auto", "pct_sin_auto", "cuota_3b_actual", "dist_3b_m",
                "n_hard_discount", "n_conveniencia", "n_supermercado", "n_tradicional", "score", "lat", "lon"]


def exportar_top(top: gpd.GeoDataFrame, ruta) -> None:
    t = top.copy()
    centros = gd.centros_metricos(t["h3"]).set_index("h3")
    t["lat"], t["lon"] = t["h3"].map(centros["lat"]).round(6), t["h3"].map(centros["lon"]).round(6)
    t = gpd.GeoDataFrame(t[COLUMNAS_TOP], geometry=t.geometry.values, crs=cfg.CRS_WEB)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(t.to_json(drop_id=True, ensure_ascii=False), encoding="utf-8")   # sin borrar el archivo previo


def reporte(resultados: dict) -> str:
    from scipy.stats import spearmanr
    act = resultados[cfg.CORTE_ACTUAL]
    idx, top = act["indice"], act["top"]
    par = parametros()
    filas_par = "\n".join(f"| {k} | {v} |" for k, v in par.items())
    filas_top = "\n".join(
        f"| {r.posicion} | {r.alcaldia} | {r.indice_final:,.0f} | {r.capturada:,.0f} | {r.pct_canibalizacion:.1f}% | "
        f"{r.hogares:,.0f} | {r.pct_sin_auto:.0f}% | {r.dist_3b_m:,.0f} m | `{r.h3}` |" for r in top.itertuples())
    por_alc = top["alcaldia"].value_counts()
    filas_alc = "\n".join(f"| {a} | {n} |" for a, n in por_alc.items())
    rho = {bw: spearmanr(idx[f"kde_{bw}"], idx["indice_final"]).statistic for bw in cfg.KDE_BANDWIDTHS_M}
    filas_kde = "\n".join(f"| KDE {bw} m | {r:.2f} |" for bw, r in rho.items())
    c0 = resultados[cfg.CORTE_BACKTEST]["indice"]
    return f"""# Índice de expansión 3B · Top {cfg.TOP_N} (corte {cfg.CORTE_ACTUAL})

Generado automáticamente por `scripts/06_gold_indice.py`. Versión v1: los parámetros se calibran en la Fase 4 (backtest).

**Lectura del índice:** hogares objetivo ({cfg.DEMANDA_OBJETIVO.replace('_', ' ')}) que una tienda 3B nueva en ese hexágono
ganaría para la cadena, ya descontada la canibalización de sus propias tiendas, ponderado por su factibilidad
operativa (cercanía a la red actual).

## Top {cfg.TOP_N} zonas recomendadas
| # | Alcaldía | Índice | Hogares captados | Canibalización | Hogares en el hexágono | % sin auto | 3B más cercana | H3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{filas_top}

| Alcaldía | Zonas en el Top {cfg.TOP_N} |
| --- | --- |
{filas_alc}

## Cobertura
| Indicador | {cfg.CORTE_BACKTEST} | {cfg.CORTE_ACTUAL} |
| --- | --- | --- |
| Hexágonos con demanda | {len(c0):,} | {len(idx):,} |
| Hexágonos con al menos una 3B | {(c0.n_3b > 0).sum():,} | {(idx.n_3b > 0).sum():,} |
| Cuota 3B promedio de la demanda objetivo | {c0.cuota_3b_actual.mean():.1%} | {idx.cuota_3b_actual.mean():.1%} |
| Hexágonos dentro del radio operativo | {(c0.factor_red == 1).mean():.0%} | {(idx.factor_red == 1).mean():.0%} |

## KDE clásico vs índice H3 (correlación de rangos de Spearman)
| Superficie | ρ con el índice |
| --- | --- |
{filas_kde}

Una ρ alta indica que ambos "ven" la misma demanda; la diferencia es lo que el índice agrega: competencia (Huff),
canibalización y factibilidad operativa.

## Parámetros
| Parámetro | Valor |
| --- | --- |
{filas_par}
"""


def ejecutar(escribir: bool = True) -> dict:
    cfg.GOLD.mkdir(parents=True, exist_ok=True)
    m, dem = preparar_demanda()
    resultados = {}
    for corte in cfg.CORTES:
        idx = construir_indice(corte, m, dem)
        top = gpd.GeoDataFrame(seleccionar_top(idx), geometry="geometry", crs=cfg.CRS_WEB)
        resultados[corte] = {"indice": idx, "top": top}
        if escribir:
            idx.to_parquet(cfg.GOLD / f"indice_h3_{corte}.parquet", index=False)
            top.to_parquet(cfg.GOLD / f"top{cfg.TOP_N}_{corte}.parquet", index=False)
            (cfg.GOLD / f"parametros_{corte}.json").write_text(json.dumps(parametros(), indent=2, ensure_ascii=False))
    if escribir:
        exportar_top(resultados[cfg.CORTE_ACTUAL]["top"], cfg.OUTPUTS / f"top{cfg.TOP_N}_indice_v1.geojson")
        rep = cfg.ROOT / "reports" / "indice_expansion.md"
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(reporte(resultados), encoding="utf-8")
    return resultados
