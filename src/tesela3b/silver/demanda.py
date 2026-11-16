"""Silver · Demanda: Censo 2020 + Marco Geoestadístico + CONEVAL (Fase 2.2).

Diseño (asignación dasimétrica):
- CUÁNTOS hogares hay se toma de la MANZANA (más fina que un hexágono H3 res 9 de ~0.1 km²).
- QUÉ PERFIL tienen se toma de la AGEB (por manzana hasta 8% de los bienes es confidencial).
  En Gold cada manzana hereda el perfil de su AGEB.

Salidas:
    data/silver/ageb_perfil.parquet        polígonos de AGEB con hogares, densidad y perfil socioeconómico
    data/silver/manzanas_demanda.parquet   punto representativo de cada manzana habitada con sus hogares
    data/silver/alcaldias.parquet          polígonos de las 16 alcaldías
    data/silver/limite_cdmx.parquet        contorno de la CDMX
    docs/calidad_silver_demanda.md         reporte de calidad generado
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from tesela3b import config as cfg
from tesela3b.silver import censo as cs
from tesela3b.silver import marco_geo as mg

# ---------------------------------------------------------------------------
# CONEVAL · Grado de Rezago Social por AGEB urbana 2020
# ---------------------------------------------------------------------------
# El Excel tiene encabezados en varias filas; los datos empiezan en la fila 7.
COLUMNAS_CONEVAL = {
    7: "CVEGEO",
    13: "pct_educ_basica_incompleta",
    14: "pct_sin_derechohabiencia",
    15: "pct_hacinamiento",
    21: "pct_sin_lavadora",
    22: "pct_sin_refrigerador",
    25: "pct_sin_computadora",
    26: "pct_sin_internet",
    27: "grado_rezago",
}
GRADOS = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]


def leer_coneval() -> pd.DataFrame:
    crudo = pd.read_excel(cfg.BRONZE / "coneval" / "GRS_AGEB_urbana_2020.xlsx",
                          header=None, skiprows=6, dtype=str)
    return limpiar_coneval(crudo)


def limpiar_coneval(crudo: pd.DataFrame) -> pd.DataFrame:
    df = crudo[crudo[0].astype(str).str.zfill(2) == cfg.CVE_ENT][list(COLUMNAS_CONEVAL)]
    df = df.rename(columns=COLUMNAS_CONEVAL)
    for c in df.columns:
        if c.startswith("pct_"):
            df[c] = pd.to_numeric(df[c], errors="coerce").clip(0, 100).round(1)
    df["grado_rezago"] = df["grado_rezago"].str.strip().str.capitalize()
    df["grado_rezago"] = df["grado_rezago"].where(df["grado_rezago"].isin(GRADOS))
    return df.drop_duplicates("CVEGEO").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Construcción de las tablas
# ---------------------------------------------------------------------------
def construir_ageb(ageb_censo: pd.DataFrame, poligonos: gpd.GeoDataFrame, coneval: pd.DataFrame) -> gpd.GeoDataFrame:
    """Une perfil censal + CONEVAL a los polígonos de AGEB. Polígonos en EPSG:6369."""
    perfil = cs.perfil_ageb(ageb_censo).merge(coneval, on="CVEGEO", how="left")
    g = poligonos[["CVEGEO", "geometry"]].merge(perfil, on="CVEGEO", how="inner")
    g["area_km2"] = (g.area / 1e6).round(4)
    g["hogares_km2"] = (g["hogares"] / g["area_km2"]).round(1)
    g["poblacion_km2"] = (g["poblacion"] / g["area_km2"]).round(1)
    return g.to_crs(cfg.CRS_WEB)


def construir_manzanas(manzana_censo: pd.DataFrame, ageb_censo: pd.DataFrame,
                       poligonos: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Manzanas habitadas como puntos representativos (siempre caen dentro del polígono).

    Se guardan como puntos porque una manzana (~0.01 km²) es mucho menor que un hexágono H3 res 9
    (~0.1 km²): asignarla por su punto es preciso y el archivo pesa una fracción.
    """
    dem = cs.demanda_manzana(manzana_censo, ageb_censo)
    dem = dem[dem["poblacion"] > 0]
    g = poligonos[["CVEGEO", "TIPOMZA", "geometry"]].merge(dem, on="CVEGEO", how="inner")
    g["area_m2"] = g.area.round(0)
    g["geometry"] = g.representative_point()
    g = g.rename(columns={"TIPOMZA": "tipo_manzana"})
    return g.to_crs(cfg.CRS_WEB)


# ---------------------------------------------------------------------------
# Reporte de calidad
# ---------------------------------------------------------------------------
def reporte_calidad(stats: dict, ageb: gpd.GeoDataFrame) -> str:
    filas = "\n".join(f"| {k} | {v} |" for k, v in stats.items())
    perfil = ["hogares_km2", "personas_por_hogar", "escolaridad_promedio", "pct_sin_auto",
              "pct_sin_computadora", "pct_sin_internet", "pct_hacinamiento", "pct_sin_derechohabiencia"]
    d = ageb[perfil].describe(percentiles=[0.1, 0.5, 0.9]).T
    tabla = "\n".join(
        f"| {v} | {r['10%']:,.1f} | {r['50%']:,.1f} | {r['90%']:,.1f} | {int(ageb[v].isna().sum())} |"
        for v, r in d.iterrows())
    grado = ageb["grado_rezago"].value_counts().reindex(GRADOS).fillna(0).astype(int)
    tabla_grado = "\n".join(f"| {g} | {n:,} | {n / len(ageb):.1%} |" for g, n in grado.items())
    alc = (ageb.groupby("alcaldia").agg(agebs=("CVEGEO", "size"), hogares=("hogares", "sum"),
                                        sin_auto=("pct_sin_auto", "median"))
              .sort_values("hogares", ascending=False))
    tabla_alc = "\n".join(f"| {i} | {int(r.agebs)} | {r.hogares:,.0f} | {r.sin_auto:.0f}% |" for i, r in alc.iterrows())
    return f"""# Reporte de calidad · Silver demanda

Generado automáticamente por `scripts/05_silver_demanda.py`. No editar a mano.

## Resumen y conciliación
| Indicador | Valor |
| --- | --- |
{filas}

## Perfil por AGEB (percentiles)
| Variable | P10 | Mediana | P90 | Nulos |
| --- | --- | --- | --- | --- |
{tabla}

## Grado de rezago social (CONEVAL)
| Grado | AGEB | % |
| --- | --- | --- |
{tabla_grado}

El grado casi no varía dentro de la CDMX; el modelo usa los porcentajes continuos.

## Por alcaldía
| Alcaldía | AGEB | Hogares | Mediana % viviendas sin auto |
| --- | --- | --- | --- |
{tabla_alc}
"""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def ejecutar(escribir: bool = True) -> dict:
    cfg.SILVER.mkdir(parents=True, exist_ok=True)
    censo = cs.leer_censo()
    a_censo, m_censo = cs.tabla_ageb(censo), cs.tabla_manzana(censo)
    coneval = leer_coneval()
    pol_ageb = mg.leer_capa("ageb", ["CVEGEO"])
    pol_mza = mg.leer_capa("manzana", ["CVEGEO", "TIPOMZA"])
    alcaldias, limite = mg.alcaldias(), mg.limite_cdmx()

    ageb = construir_ageb(a_censo, pol_ageb, coneval)
    manzanas = construir_manzanas(m_censo, a_censo, pol_mza)

    habitadas = m_censo[m_censo["POBTOT"] > 0]
    entidad = pd.to_numeric(censo.loc[censo["MUN"] == "000", "POBTOT"]).iloc[0]
    sin_poligono = a_censo.loc[~a_censo["CVEGEO"].isin(pol_ageb["CVEGEO"]), "POBTOT"].sum()
    stats = {
        "Población total CDMX (Censo 2020)": f"{entidad:,.0f}",
        "Población en AGEB urbanas": f"{a_censo['POBTOT'].sum():,.0f} ({a_censo['POBTOT'].sum() / entidad:.1%} del total)",
        "AGEB urbanas en el censo / con polígono": f"{len(a_censo):,} / {len(ageb):,}",
        "Población en AGEB sin polígono": f"{sin_poligono:,.0f}",
        "AGEB con datos de CONEVAL": f"{ageb['grado_rezago'].notna().mean():.1%}",
        "Hogares en AGEB": f"{ageb['hogares'].sum():,.0f}",
        "Manzanas habitadas con punto": f"{len(manzanas):,}",
        "Manzanas habitadas sin polígono (población)": f"{(~habitadas['CVEGEO'].isin(manzanas['CVEGEO'])).sum():,} "
                                                       f"({habitadas.loc[~habitadas['CVEGEO'].isin(manzanas['CVEGEO']), 'POBTOT'].sum():,.0f} personas)",
        "Hogares en manzanas (suma)": f"{manzanas['hogares'].sum():,.0f}",
        "Manzanas con hogares estimados (dato confidencial)": f"{manzanas['hogares_imputado'].sum():,} ({manzanas['hogares_imputado'].mean():.1%})",
        "Diferencia hogares manzanas vs AGEB": f"{manzanas['hogares'].sum() / ageb['hogares'].sum() - 1:+.2%}",
    }

    from tesela3b.silver.esquemas import AGEB_PERFIL, MANZANAS_DEMANDA, validar
    validar(ageb, AGEB_PERFIL)
    validar(manzanas, MANZANAS_DEMANDA)

    if escribir:
        ageb.to_parquet(cfg.SILVER / "ageb_perfil.parquet", index=False)
        manzanas.to_parquet(cfg.SILVER / "manzanas_demanda.parquet", index=False)
        alcaldias.to_crs(cfg.CRS_WEB).to_parquet(cfg.SILVER / "alcaldias.parquet", index=False)
        limite.to_crs(cfg.CRS_WEB).to_parquet(cfg.SILVER / "limite_cdmx.parquet", index=False)
        (cfg.DOCS / "calidad_silver_demanda.md").write_text(reporte_calidad(stats, ageb), encoding="utf-8")
    return {"stats": stats, "ageb": ageb, "manzanas": manzanas, "alcaldias": alcaldias}
