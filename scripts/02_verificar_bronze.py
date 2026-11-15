"""Paso 2 · Verifica la capa Bronze: filas, columnas, CRS y conteo preliminar de cadenas.

Uso: python scripts/02_verificar_bronze.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b.config import BRONZE, PATRONES_CADENAS  # noqa: E402


def titulo(t: str) -> None:
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def verificar_denue() -> None:
    for version in ["2021_11", "2026_05"]:
        ruta = BRONZE / "denue" / version / "conjunto_de_datos" / "denue_inegi_09_.csv"
        df = pd.read_csv(ruta, encoding="latin-1", dtype=str)
        titulo(f"DENUE {version}: {len(df):,} filas x {df.shape[1]} columnas")
        texto = (df["nom_estab"].fillna("") + " | " + df["raz_social"].fillna("")).str.upper()
        for cadena, patron in PATRONES_CADENAS.items():
            print(f"  {cadena:16s} {texto.str.contains(patron, regex=True).sum():6d} coincidencias")
        print("  lat/lon nulos:", df["latitud"].isna().sum(), "/", df["longitud"].isna().sum())


def verificar_censo() -> None:
    ruta = BRONZE / "censo2020" / "RESAGEBURB_09CSV20.csv"
    df = pd.read_csv(ruta, dtype=str, encoding="utf-8-sig")
    ageb = df[(df["AGEB"] != "0000") & (df["MZA"] == "000")]
    titulo(f"Censo 2020: {len(df):,} filas x {df.shape[1]} columnas")
    print(f"  Filas a nivel AGEB (AGEB != '0000' y MZA == '000'): {len(ageb):,}")
    print(f"  Valores confidenciales '*' en POBTOT: {(df['POBTOT'] == '*').sum():,}")


def verificar_coneval() -> None:
    ruta = BRONZE / "coneval" / "GRS_AGEB_urbana_2020.xlsx"
    xls = pd.ExcelFile(ruta)
    titulo(f"CONEVAL GRS: hojas = {xls.sheet_names}")
    print(pd.read_excel(ruta, sheet_name=xls.sheet_names[0], nrows=8).to_string()[:1500])


def verificar_afluencia() -> None:
    ruta = BRONZE / "movilidad" / "afluenciastc_desglosado_09_2026.csv"
    df = pd.read_csv(ruta, encoding="utf-8", encoding_errors="replace")
    titulo(f"Afluencia Metro: {len(df):,} filas | {df['fecha'].min()} a {df['fecha'].max()}")
    print(f"  Estaciones distintas: {df['estacion'].nunique()} | líneas: {df['linea'].nunique()}")


def verificar_marco_geo() -> None:
    try:
        import geopandas as gpd
    except ImportError:
        titulo("Marco Geoestadístico: instala geopandas para verificarlo (pip install -r requirements.txt)")
        return
    for capa in ["09a", "09mun", "09ent"]:
        gdf = gpd.read_file(BRONZE / "marco_geo" / "conjunto_de_datos" / f"{capa}.shp")
        titulo(f"Marco Geo {capa}: {len(gdf):,} geometrías | CRS = {gdf.crs.to_string() if gdf.crs else None}")
        print("  columnas:", list(gdf.columns))


if __name__ == "__main__":
    for paso in [verificar_denue, verificar_censo, verificar_coneval, verificar_afluencia, verificar_marco_geo]:
        try:
            paso()
        except FileNotFoundError as e:
            print(f"\n[FALTA] {e}. ¿Ya corriste scripts/01_extraer_bronze.py?")
