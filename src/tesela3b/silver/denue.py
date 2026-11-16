"""Silver · DENUE: oferta de tiendas de despensa en la CDMX (Fase 2.1).

Entrada : data/bronze/denue/{corte}/conjunto_de_datos/denue_inegi_09_.csv
Salidas : data/silver/establecimientos_{corte}.parquet   tiendas de despensa clasificadas por cadena
          data/silver/tiendas_3b_{corte}.parquet         tiendas 3B únicas (deduplicadas)
          data/silver/aperturas_3b.parquet               tiendas 3B actuales + etiqueta de apertura
          docs/validacion/muestra_validacion_3b.csv      muestra para validar a mano
          docs/calidad_silver_denue.md                   reporte de calidad generado

Reglas de negocio (ver docs/decisiones.md y notebooks/01_eda_bronze.ipynb):
1. 3B se identifica por nombre + razón social, solo en códigos SCIAN de tienda, excluyendo
   CEDIS, oficinas y otras marcas con razón social de 3B.
2. Bodega Aurrera está registrada como Walmart: se identifica por razón social + prefijo/sufijo del nombre.
3. Neto se identifica por su razón social ("Tiendas Super Precio") y se busca también en mayoreo
   (SCIAN 431110), donde INEGI la clasificó en 2021.
4. Registros de la misma cadena a < UMBRAL_DUPLICADO_M son la misma tienda: se conserva el más antiguo.
5. Una 3B del corte actual es apertura si no había una 3B del corte anterior a < UMBRAL_APERTURA_M.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from tesela3b import config as cfg

# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
COLUMNAS = [
    "id", "clee", "nom_estab", "raz_social", "codigo_act", "nombre_act", "per_ocu",
    "tipo_vial", "nom_vial", "numero_ext", "nomb_asent", "cod_postal",
    "cve_ent", "cve_mun", "municipio", "cve_loc", "ageb", "manzana",
    "latitud", "longitud", "fecha_alta",
]


def leer_denue(corte: str) -> pd.DataFrame:
    """Lee el DENUE de Bronze tal cual (todo como texto)."""
    ruta = cfg.BRONZE / "denue" / corte / "conjunto_de_datos" / "denue_inegi_09_.csv"
    return pd.read_csv(ruta, encoding="latin-1", dtype=str, usecols=COLUMNAS)


# ---------------------------------------------------------------------------
# Clasificación por cadena
# ---------------------------------------------------------------------------
PATRON_3B = r"TIENDAS?\s*3\s*B\b|TIENDAS?\s*TRES\s*B\b|^\s*T?3\s*B\s*$|BBB\s*FOODS?|TIENDA\s*BBB"
EXCLUSIONES_3B = r"CEDIS|CENTRO DE DISTRIBUCION|OFICINAS|CIRCULO K|SUPER YEMA"

FORMATO = {
    "3B": "Hard discount", "Neto": "Hard discount", "Bodega Aurrera": "Hard discount",
    "OXXO": "Conveniencia", "7-Eleven": "Conveniencia", "Circle K": "Conveniencia",
    "Walmart otros": "Supermercado", "Soriana": "Supermercado", "Chedraui": "Supermercado",
    "La Comer": "Supermercado", "Supermercado independiente": "Supermercado",
    "Abarrotes": "Tradicional", "Minisúper independiente": "Tradicional",
}
CADENAS = [c for c in FORMATO if c not in ("Abarrotes", "Minisúper independiente", "Supermercado independiente")]


def _mayus(s: pd.Series) -> pd.Series:
    return s.fillna("").str.upper().str.strip()


def es_3b(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Devuelve (candidato, confirmado): el patrón coincide / además es tienda y no está excluido."""
    texto = _mayus(df["nom_estab"]) + " | " + _mayus(df["raz_social"])
    nombre_o_razon = _mayus(df["nom_estab"]).str.contains(PATRON_3B, regex=True) | \
        _mayus(df["raz_social"]).str.contains(PATRON_3B, regex=True)
    excluido = texto.str.contains(EXCLUSIONES_3B, regex=True) | ~df["codigo_act"].isin(cfg.SCIAN_TIENDAS)
    return nombre_o_razon, nombre_o_razon & ~excluido


def clasificar_cadena(df: pd.DataFrame) -> pd.Series:
    """Asigna una cadena a cada establecimiento (NA si no es tienda de despensa).

    Las reglas se aplican en orden de prioridad: la primera que coincide gana.
    """
    nom, raz, cod = _mayus(df["nom_estab"]), _mayus(df["raz_social"]), df["codigo_act"].fillna("")
    texto = nom + " | " + raz
    tienda = cod.isin(cfg.SCIAN_TIENDAS)
    super_o_mini = cod.isin([cfg.SCIAN_SUPERMERCADO, cfg.SCIAN_MINISUPER])
    walmart = raz.str.contains(r"WAL\s*-?\s*MART", regex=True)
    bodega = nom.str.contains(
        r"AURRERA|^(?:\d+\s+)?(?:BODEGA|BA EXPRESS|BAE|BOA|MI BODEGA)\b|\b(?:BOA|BAE)\s*$", regex=True)

    reglas = [
        ("3B", es_3b(df)[1]),
        ("Bodega Aurrera", (walmart & bodega & super_o_mini) | (nom.str.contains("AURRERA") & tienda)),
        ("Walmart otros", walmart & super_o_mini),
        ("Neto", (raz.str.contains(r"SUPER\s*PRECIO", regex=True) |
                  nom.str.contains(r"^(?:\d+\s+)?(?:TIENDAS?\s+)?NETO\b", regex=True))
                 & cod.isin(cfg.SCIAN_TIENDAS + (cfg.SCIAN_MAYOREO_ABARROTES,))),
        ("OXXO", (raz.str.contains("CADENA COMERCIAL OXXO") | nom.str.contains(r"\bOXXO\b", regex=True))
                 & tienda & ~nom.str.contains("CEDIS")),
        ("7-Eleven", texto.str.contains(r"7\s*-?\s*ELEVEN", regex=True) & tienda),
        ("Circle K", texto.str.contains(r"CIRCLE\s*K|CIRCULO\s*K|CIRCULO\s*CCK", regex=True) & tienda),
        ("Soriana", raz.str.contains("SORIANA") & super_o_mini),
        ("Chedraui", raz.str.contains("CHEDRAUI") & super_o_mini),
        ("La Comer", raz.str.contains(r"CITY\s*FRESKO|\bLA COMER\b", regex=True) & super_o_mini),
        ("Supermercado independiente", cod.eq(cfg.SCIAN_SUPERMERCADO)),
        ("Minisúper independiente", cod.eq(cfg.SCIAN_MINISUPER)),
        ("Abarrotes", cod.eq(cfg.SCIAN_ABARROTES)),
    ]
    cadena = pd.Series(pd.NA, index=df.index, dtype="object")
    for nombre, mascara in reglas:
        cadena = cadena.where(cadena.notna() | ~mascara, nombre)
    return cadena


# ---------------------------------------------------------------------------
# Limpieza y geometría
# ---------------------------------------------------------------------------
def _personal(per_ocu: pd.Series) -> pd.DataFrame:
    nums = per_ocu.fillna("").str.findall(r"\d+")
    minimo = nums.map(lambda x: int(x[0]) if x else np.nan)
    maximo = nums.map(lambda x: int(x[1]) if len(x) > 1 else np.nan)
    return pd.DataFrame({"per_ocu_min": minimo, "per_ocu_max": maximo}, index=per_ocu.index)


def construir_establecimientos(df: pd.DataFrame, corte: str) -> gpd.GeoDataFrame:
    """Filtra tiendas de despensa, clasifica por cadena y crea la geometría (EPSG:4326)."""
    out = df.assign(cadena=clasificar_cadena(df)).dropna(subset=["cadena"]).copy()
    out["formato"] = out["cadena"].map(FORMATO)
    out["es_cadena"] = out["cadena"].isin(CADENAS)
    out["corte"] = corte
    out["cvegeo_ageb"] = out["cve_ent"] + out["cve_mun"] + out["cve_loc"] + out["ageb"]
    tipo, via = _mayus(out["tipo_vial"]), _mayus(out["nom_vial"])
    tipo = tipo.where(~pd.Series([v.startswith(t) and t != "" for t, v in zip(tipo, via)], index=out.index), "")
    out["direccion"] = ((tipo + " " + via + " " + out["numero_ext"].fillna("").str.strip())
                        .str.replace(r"\s+", " ", regex=True).str.strip().str.title())
    out["cod_postal"] = out["cod_postal"].fillna("").str.strip().str.zfill(5).replace("00000", pd.NA)
    out = pd.concat([out, _personal(out["per_ocu"])], axis=1)
    out["latitud"] = pd.to_numeric(out["latitud"], errors="coerce")
    out["longitud"] = pd.to_numeric(out["longitud"], errors="coerce")
    lon0, lat0, lon1, lat1 = cfg.BBOX_CDMX
    dentro = out["longitud"].between(lon0, lon1) & out["latitud"].between(lat0, lat1)
    out = out[dentro].copy()
    columnas = ["id", "clee", "corte", "cadena", "formato", "es_cadena", "nom_estab", "raz_social",
                "codigo_act", "per_ocu", "per_ocu_min", "per_ocu_max", "direccion", "nomb_asent",
                "cod_postal", "cve_mun", "municipio", "cvegeo_ageb", "fecha_alta", "latitud", "longitud"]
    geo = gpd.points_from_xy(out["longitud"], out["latitud"])
    return gpd.GeoDataFrame(out[columnas].reset_index(drop=True), geometry=geo, crs=cfg.CRS_WEB)


def umbral_duplicado(cadena: str) -> float:
    """3B: 50 m (no abre dos tiendas en la misma cuadra). Competencia: 25 m."""
    return cfg.UMBRAL_DUPLICADO_M if cadena == "3B" else cfg.UMBRAL_DUPLICADO_COMPETENCIA_M


def deduplicar(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Agrupa registros de la misma cadena a menos de su umbral (componentes conexas)
    y conserva el de fecha de alta más antigua. Solo aplica a cadenas, no a independientes."""
    gdf = gdf.copy()
    gdf["n_registros"] = 1
    cadenas = gdf[gdf["es_cadena"]]
    if cadenas.empty:
        return gdf
    m = cadenas.to_crs(cfg.CRS_METRIC)[["cadena", "geometry"]]
    umbral_max = max(cfg.UMBRAL_DUPLICADO_M, cfg.UMBRAL_DUPLICADO_COMPETENCIA_M)
    pares = gpd.sjoin(m, m, predicate="dwithin", distance=umbral_max)
    pares = pares[(pares.index != pares["index_right"]) & (pares["cadena_left"] == pares["cadena_right"])]
    dist = m.geometry.loc[pares.index].distance(m.geometry.loc[pares["index_right"]], align=False).values
    pares = pares[dist < pares["cadena_left"].map(umbral_duplicado).values]

    padre = {i: i for i in m.index}  # union-find

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for a, b in zip(pares.index, pares["index_right"]):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[rb] = ra
    grupo = pd.Series({i: raiz(i) for i in m.index})

    orden = cadenas.assign(_grupo=grupo).sort_values(["_grupo", "fecha_alta", "id"])
    tamanos = orden.groupby("_grupo").size()
    conservar = orden.drop_duplicates("_grupo", keep="first")
    conservar = conservar.assign(n_registros=conservar["_grupo"].map(tamanos).values).drop(columns="_grupo")
    resultado = pd.concat([conservar, gdf[~gdf["es_cadena"]]])
    return gpd.GeoDataFrame(resultado, geometry="geometry", crs=gdf.crs).sort_values("id").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Aperturas (etiqueta del backtest)
# ---------------------------------------------------------------------------
def marcar_aperturas(actual: gpd.GeoDataFrame, anterior: gpd.GeoDataFrame,
                     fecha_corte_anterior: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Etiqueta aperturas en `actual` y continuidad en `anterior`.

    apertura             : no había 3B del corte anterior a < UMBRAL_APERTURA_M
    apertura_confirmada  : además su fecha de alta en el DENUE es posterior al corte anterior
                           (descarta tiendas viejas que el DENUE anterior no registró)
    """
    a = actual.to_crs(cfg.CRS_METRIC)
    b = anterior.to_crs(cfg.CRS_METRIC)
    dist_a = gpd.sjoin_nearest(a[["geometry"]], b[["geometry"]], distance_col="d")["d"]
    dist_a = dist_a[~dist_a.index.duplicated()]
    act = actual.copy()
    act["dist_3b_corte_anterior_m"] = dist_a.round(1)
    for u in cfg.UMBRALES_APERTURA_SENSIBILIDAD:
        act[f"apertura_{u}m"] = act["dist_3b_corte_anterior_m"] >= u
    act["apertura"] = act[f"apertura_{cfg.UMBRAL_APERTURA_M}m"]
    act["apertura_confirmada"] = act["apertura"] & (act["fecha_alta"].fillna("") >= fecha_corte_anterior)

    dist_b = gpd.sjoin_nearest(b[["geometry"]], a[["geometry"]], distance_col="d")["d"]
    dist_b = dist_b[~dist_b.index.duplicated()]
    ant = anterior.copy()
    ant["dist_3b_corte_actual_m"] = dist_b.reindex(ant.index).round(1)
    ant["sigue_en_corte_actual"] = ant["dist_3b_corte_actual_m"] < cfg.UMBRAL_APERTURA_M
    return act, ant


# ---------------------------------------------------------------------------
# Validación manual
# ---------------------------------------------------------------------------
def muestra_validacion(tiendas: gpd.GeoDataFrame, n: int = cfg.N_MUESTRA_VALIDACION,
                       semilla: int = cfg.SEMILLA) -> pd.DataFrame:
    """Muestra aleatoria de tiendas 3B para verificar a mano (Google Maps / tiendas3b.com)."""
    m = tiendas.sample(n=min(n, len(tiendas)), random_state=semilla).sort_values("municipio")
    return pd.DataFrame({
        "id": m["id"], "nombre_denue": m["nom_estab"], "razon_social": m["raz_social"],
        "direccion": m["direccion"], "colonia": m["nomb_asent"].str.title(), "cp": m["cod_postal"],
        "alcaldia": m["municipio"], "fecha_alta": m["fecha_alta"],
        "google_maps": "https://www.google.com/maps/search/?api=1&query="
                       + m["latitud"].round(6).astype(str) + "," + m["longitud"].round(6).astype(str),
        "es_3b": "", "comentario": "",
    })


def precision_validacion(ruta: Path) -> dict:
    """Lee la muestra llenada a mano y calcula la precisión con intervalo de Wilson al 95%."""
    # Excel puede re-guardar con otra codificación (cp1252) y otro separador (tabulador o ;)
    crudo = Path(ruta).read_bytes()
    try:
        texto = crudo.decode("utf-8-sig")
        codificacion = "utf-8-sig"
    except UnicodeDecodeError:
        texto, codificacion = crudo.decode("cp1252"), "cp1252"
    encabezado = texto.splitlines()[0] if texto else ""
    sep = max([",", ";", "\t"], key=encabezado.count) if any(c in encabezado for c in ",;\t") else ","
    df = pd.read_csv(ruta, dtype=str, sep=sep, encoding=codificacion)
    resp = df["es_3b"].fillna("").str.strip().str.upper().str.replace("Í", "I")
    validas = resp[resp.isin(["SI", "NO"])]
    n, k = len(validas), int((validas == "SI").sum())
    if n == 0:
        return {"evaluadas": 0, "pendientes": len(df)}
    p, z = k / n, 1.96
    centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    margen = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return {"evaluadas": n, "son_3b": k, "precision": round(p, 3),
            "ic95": (round(centro - margen, 3), round(centro + margen, 3)),
            "dudosas": int((resp == "NO SE").sum()), "pendientes": int((resp == "").sum())}


# ---------------------------------------------------------------------------
# Reporte de calidad
# ---------------------------------------------------------------------------
def reporte_calidad(stats: dict, ant: gpd.GeoDataFrame, act: gpd.GeoDataFrame,
                    est: dict[str, gpd.GeoDataFrame]) -> str:
    c0, c1 = cfg.CORTES
    conteo = pd.DataFrame({c: e["cadena"].value_counts() for c, e in est.items()}).fillna(0).astype(int)
    conteo["formato"] = conteo.index.map(FORMATO)
    conteo = conteo.sort_values(["formato", c1], ascending=[True, False])
    sens = {u: int(act[f"apertura_{u}m"].sum()) for u in cfg.UMBRALES_APERTURA_SENSIBILIDAD}
    por_alc = (act.groupby("municipio").agg(tiendas=("id", "size"), aperturas=("apertura_confirmada", "sum"))
                  .sort_values("aperturas", ascending=False))
    filas = "\n".join(f"| {k} | {v} |" for k, v in stats.items())
    tabla_cad = "\n".join(f"| {i} | {r['formato']} | {r[c0]:,} | {r[c1]:,} |" for i, r in conteo.iterrows())
    tabla_alc = "\n".join(f"| {i} | {r['tiendas']} | {r['aperturas']} |" for i, r in por_alc.iterrows())
    return f"""# Reporte de calidad · Silver DENUE

Generado automáticamente por `scripts/03_silver_denue.py`. No editar a mano.

## Resumen
| Indicador | Valor |
| --- | --- |
{filas}

## Aperturas 3B: sensibilidad al umbral de distancia
| Umbral | Aperturas |
| --- | --- |
""" + "\n".join(f"| {u} m | {n} |" for u, n in sens.items()) + f"""

La etiqueta del backtest es `apertura_confirmada`: sin 3B de {c0} a < {cfg.UMBRAL_APERTURA_M} m **y** fecha de alta en el DENUE posterior al corte {c0}.

## Establecimientos por cadena (deduplicados)
| Cadena | Formato | {c0} | {c1} |
| --- | --- | --- | --- |
{tabla_cad}

## Tiendas 3B y aperturas confirmadas por alcaldía ({c1})
| Alcaldía | Tiendas 3B | Aperturas |
| --- | --- | --- |
{tabla_alc}
"""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def ejecutar(escribir: bool = True) -> dict:
    cfg.SILVER.mkdir(parents=True, exist_ok=True)
    est, tiendas, stats = {}, {}, {}
    for corte in cfg.CORTES:
        crudo = leer_denue(corte)
        candidatos, confirmados = es_3b(crudo)
        e = construir_establecimientos(crudo, corte)
        antes = e["es_cadena"].sum()
        e = deduplicar(e)
        est[corte] = e
        tiendas[corte] = e[e["cadena"] == "3B"].reset_index(drop=True)
        stats[f"Registros DENUE {corte}"] = f"{len(crudo):,}"
        stats[f"Tiendas de despensa {corte}"] = f"{len(e):,}"
        stats[f"Registros 3B: patrón / excluidos / confirmados ({corte})"] = \
            f"{candidatos.sum()} / {(candidatos & ~confirmados).sum()} / {confirmados.sum()}"
        stats[f"Duplicados de cadenas eliminados ({corte})"] = int(antes - e["es_cadena"].sum())
        stats[f"Tiendas 3B únicas ({corte})"] = len(tiendas[corte])

    c0, c1 = cfg.CORTES
    fecha_c0 = c0.replace("_", "-")
    act, ant = marcar_aperturas(tiendas[c1], tiendas[c0], fecha_c0)
    stats[f"Aperturas (umbral {cfg.UMBRAL_APERTURA_M} m)"] = int(act["apertura"].sum())
    stats["Aperturas confirmadas (etiqueta del backtest)"] = int(act["apertura_confirmada"].sum())
    stats[f"Tiendas 3B de {c0} sin equivalente en {c1}"] = int((~ant["sigue_en_corte_actual"]).sum())

    from tesela3b.silver.esquemas import ESTABLECIMIENTOS, TIENDAS_3B_ACTUAL, validar
    for e in est.values():
        validar(e, ESTABLECIMIENTOS)
    validar(act, TIENDAS_3B_ACTUAL)

    if escribir:
        for corte, e in est.items():
            e.to_parquet(cfg.SILVER / f"establecimientos_{corte}.parquet", index=False)
        ant.to_parquet(cfg.SILVER / f"tiendas_3b_{c0}.parquet", index=False)
        act.to_parquet(cfg.SILVER / f"tiendas_3b_{c1}.parquet", index=False)
        act.to_parquet(cfg.SILVER / "aperturas_3b.parquet", index=False)
        val = cfg.DOCS / "validacion" / "muestra_validacion_3b.csv"
        val.parent.mkdir(parents=True, exist_ok=True)
        if not val.exists():  # nunca sobrescribir una validación ya llenada a mano
            muestra_validacion(act).to_csv(val, index=False, encoding="utf-8-sig")
        (cfg.DOCS / "calidad_silver_denue.md").write_text(reporte_calidad(stats, ant, act, est), encoding="utf-8")
    return {"stats": stats, "establecimientos": est, "tiendas_anterior": ant, "tiendas_actual": act}
