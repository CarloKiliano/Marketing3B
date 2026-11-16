"""Silver · Marco Geoestadístico 2020 (INEGI): polígonos de AGEB, manzanas, alcaldías y entidad.

Los shapefiles vienen en "MEXICO_ITRF_2008_LCC" (Lambert de INEGI, equivalente a EPSG:6372 pero sin
código EPSG en su .prj). GeoPandas los reproyecta leyendo su propio .prj, así que nunca se fuerza un CRS.
"""
from __future__ import annotations

import geopandas as gpd

from tesela3b import config as cfg

CAPAS = {"ageb": "a", "manzana": "m", "alcaldia": "mun", "entidad": "ent"}


def leer_capa(nombre: str, columnas: list[str] | None = None) -> gpd.GeoDataFrame:
    """Lee una capa del Marco Geoestadístico y la devuelve en EPSG:6369 (metros)."""
    ruta = cfg.BRONZE / "marco_geo" / "conjunto_de_datos" / f"{cfg.CVE_ENT}{CAPAS[nombre]}.shp"
    gdf = gpd.read_file(ruta, columns=columnas)
    if gdf.crs is None:
        raise ValueError(f"{ruta.name} no trae sistema de referencia (.prj)")
    return gdf.to_crs(cfg.CRS_METRIC)


def alcaldias() -> gpd.GeoDataFrame:
    g = leer_capa("alcaldia")
    return g.rename(columns={"CVE_MUN": "cve_mun", "NOMGEO": "alcaldia"})[["CVEGEO", "cve_mun", "alcaldia", "geometry"]]


def limite_cdmx() -> gpd.GeoDataFrame:
    return leer_capa("entidad")[["CVEGEO", "NOMGEO", "geometry"]]
