"""Descarga la red peatonal de la CDMX desde OpenStreetMap (OSMnx) y la guarda en Bronze.

Se usa para las isócronas caminando de la Fase 4 (Voronoi vs Huff vs isócronas).
Correr una sola vez, con internet:  python scripts/07_descargar_red_osm.py   (tarda ~5-15 min)

Salida (formato compacto, sin depender de OSMnx para leerla):
    data/bronze/osm/nodos.parquet    osmid, x (lon), y (lat)
    data/bronze/osm/aristas.parquet  u, v, length (metros)
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import geopandas as gpd  # noqa: E402
import osmnx as ox  # noqa: E402

from tesela3b import config as cfg  # noqa: E402

SALIDA = cfg.DATA / "bronze" / "osm"


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    limite = gpd.read_parquet(cfg.SILVER / "limite_cdmx.parquet").to_crs(cfg.CRS_WEB)
    poligono = limite.union_all()
    ox.settings.requests_timeout = 900
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(SALIDA / "_cache")
    t0 = time.time()
    print("Descargando la red peatonal de la CDMX desde OpenStreetMap (puede tardar varios minutos)...")
    G = ox.graph_from_polygon(poligono, network_type="walk", simplify=True, retain_all=False)
    nodos, aristas = ox.graph_to_gdfs(G)
    nodos = nodos.reset_index()[["osmid", "x", "y"]]
    aristas = aristas.reset_index()[["u", "v", "length"]]
    nodos.to_parquet(SALIDA / "nodos.parquet", index=False)
    aristas.to_parquet(SALIDA / "aristas.parquet", index=False)
    print(f"Listo en {time.time() - t0:,.0f} s: {len(nodos):,} nodos y {len(aristas):,} aristas "
          f"({aristas['length'].sum() / 1000:,.0f} km de calles caminables) -> {SALIDA}")


if __name__ == "__main__":
    main()
