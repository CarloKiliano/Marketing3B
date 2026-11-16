"""Gold · Territorio de cada tienda: Voronoi vs isócronas vs Huff (Fase 4).

Tres formas clásicas de responder "¿qué hogares atiende cada tienda?", convertidas en el mismo score
para poder compararlas en el backtest: hogares objetivo NUEVOS que gana la cadena si abre en c.

- Voronoi (determinista, distancia en línea recta): cada hogar compra en la tienda hard discount más
  cercana. Una 3B nueva en c gana los hogares (a ≤ 1 km) que pasan a tenerla como la más cercana y que
  antes eran de Neto/Bodega Aurrera; si antes eran de otra 3B es canibalización (no suma).
- Isócronas (cobertura, red de calles): un hogar está atendido si una 3B está a ≤ T minutos caminando.
  Una 3B nueva en c gana los hogares a ≤ T min de c que hoy NO tienen una 3B a ≤ T min.
- Huff anidado (probabilístico, todos los formatos): `indice_h3.calcular_indice`.

Las isócronas usan la red peatonal de OpenStreetMap (data/bronze/osm, `scripts/07_descargar_red_osm.py`).
Si la red no está descargada se usa la aproximación estándar: distancia en línea recta × factor de rodeo.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from tesela3b import config as cfg
from tesela3b.gold import demanda as gd

OSM = cfg.DATA / "bronze" / "osm"


def _xy(gdf: gpd.GeoDataFrame) -> np.ndarray:
    g = gdf.to_crs(cfg.CRS_METRIC).geometry
    return np.c_[g.x, g.y]


def limite_caminando_m(minutos: float) -> float:
    return minutos * cfg.WALK_SPEED_KMH * 1000 / 60


# ---------------------------------------------------------------------------
# Voronoi
# ---------------------------------------------------------------------------
def score_voronoi(demanda: pd.DataFrame, establecimientos: gpd.GeoDataFrame, pares: pd.DataFrame) -> pd.Series:
    """Hogares objetivo que una 3B en c le quita a Neto/Bodega Aurrera bajo la regla del más cercano."""
    hd = establecimientos[establecimientos["formato"].eq("Hard discount")]
    arbol = cKDTree(_xy(hd))
    es_3b = hd["cadena"].eq("3B").to_numpy()
    centros = gd.centros_metricos(demanda["h3"])
    d_cerca, i_cerca = arbol.query(centros[["x", "y"]].to_numpy())
    est = pd.DataFrame({"D": demanda["demanda_objetivo"].to_numpy(), "d_cerca": np.maximum(d_cerca, 0),
                        "de_3b": es_3b[i_cerca]}, index=demanda["h3"].to_numpy())
    q = pares[pares["origen"].isin(est.index) & pares["destino"].isin(est.index)]
    q = q.join(est, on="destino")
    gana = (q["d"] < q["d_cerca"]) & ~q["de_3b"]
    s = (q["D"] * gana).groupby(q["origen"]).sum()
    return demanda["h3"].map(s).fillna(0).rename("voronoi")


def poligonos_voronoi(tiendas: gpd.GeoDataFrame, recorte: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Celdas de Voronoi de las tiendas (para mapas), recortadas al límite de la CDMX."""
    from shapely.geometry import MultiPoint
    from shapely.ops import voronoi_diagram
    t = tiendas.to_crs(cfg.CRS_METRIC)
    lim = recorte.to_crs(cfg.CRS_METRIC).union_all()
    celdas = voronoi_diagram(MultiPoint(list(t.geometry)), envelope=lim.envelope.buffer(5000))
    v = gpd.GeoDataFrame(geometry=list(celdas.geoms), crs=cfg.CRS_METRIC)
    v = v.clip(lim)
    return v.to_crs(cfg.CRS_WEB)


# ---------------------------------------------------------------------------
# Red peatonal (OSM)
# ---------------------------------------------------------------------------
class RedPeatonal:
    """Grafo no dirigido de calles caminables, en metros, listo para Dijkstra de scipy."""

    def __init__(self, nodos: pd.DataFrame, aristas: pd.DataFrame):
        g = gpd.GeoSeries(gpd.points_from_xy(nodos["x"], nodos["y"]), crs=cfg.CRS_WEB).to_crs(cfg.CRS_METRIC)
        self.xy = np.c_[g.x, g.y]
        pos = pd.Series(np.arange(len(nodos)), index=nodos["osmid"].to_numpy())
        u = pos.reindex(aristas["u"].to_numpy()).to_numpy()
        v = pos.reindex(aristas["v"].to_numpy()).to_numpy()
        ok = ~(np.isnan(u) | np.isnan(v))
        u, v, w = u[ok].astype(int), v[ok].astype(int), aristas["length"].to_numpy()[ok]
        n = len(nodos)
        df = pd.DataFrame({"i": np.r_[u, v], "j": np.r_[v, u], "w": np.r_[w, w]})
        df = df.groupby(["i", "j"], as_index=False)["w"].min()   # aristas paralelas: la más corta
        self.n = n
        self.i, self.j, self.w = df["i"].to_numpy(), df["j"].to_numpy(), df["w"].to_numpy()
        self.grafo = coo_matrix((self.w, (self.i, self.j)), shape=(n, n)).tocsr()
        self.arbol = cKDTree(self.xy)

    @classmethod
    def cargar(cls, carpeta=OSM) -> "RedPeatonal | None":
        if not (carpeta / "nodos.parquet").exists() or not (carpeta / "aristas.parquet").exists():
            return None
        return cls(pd.read_parquet(carpeta / "nodos.parquet"), pd.read_parquet(carpeta / "aristas.parquet"))

    def ajustar(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Nodo más cercano a cada punto y la distancia (m) para llegar a él."""
        d, i = self.arbol.query(xy)
        return i, d

    def distancia_minima(self, origenes_xy: np.ndarray, destinos_xy: np.ndarray, limite: float) -> np.ndarray:
        """Distancia caminando desde el origen MÁS CERCANO a cada destino (inf si > límite).

        Truco estándar: un nodo virtual conectado a cada origen con peso = distancia de ajuste a la red,
        y un solo Dijkstra desde ese nodo.
        """
        io, so = self.ajustar(origenes_xy)
        idest, sd = self.ajustar(destinos_xy)
        n = self.n
        g = coo_matrix((np.r_[self.w, so + 1e-6], (np.r_[self.i, np.full(len(io), n)], np.r_[self.j, io])),
                       shape=(n + 1, n + 1)).tocsr()
        dist = dijkstra(g, directed=True, indices=n, limit=limite)
        d = dist[idest] + sd
        return np.where(d <= limite, d, np.inf)

    def pares_alcance(self, celdas, limite: float, lote: int = 200) -> pd.DataFrame:
        """Pares (origen, destino) de hexágonos a ≤ limite metros caminando por la red."""
        celdas = list(celdas)
        c = gd.centros_metricos(celdas)[["x", "y"]].to_numpy()
        nodo, snap = self.ajustar(c)
        por_nodo = pd.DataFrame({"h": np.arange(len(celdas)), "nodo": nodo, "snap": snap})
        filas = []
        for ini in range(0, len(celdas), lote):
            sub = por_nodo.iloc[ini:ini + lote]
            dist = dijkstra(self.grafo, directed=False, indices=sub["nodo"].to_numpy(), limit=limite)
            dd = dist[:, por_nodo["nodo"].to_numpy()] + sub["snap"].to_numpy()[:, None] + por_nodo["snap"].to_numpy()[None, :]
            o, d = np.nonzero(dd <= limite)
            filas.append(pd.DataFrame({"origen": sub["h"].to_numpy()[o], "destino": d, "d": dd[o, d]}))
        p = pd.concat(filas, ignore_index=True)
        p = p[p["origen"] != p["destino"]]
        propio = pd.DataFrame({"origen": np.arange(len(celdas)), "destino": np.arange(len(celdas)),
                               "d": float(cfg.HUFF_DIST_MIN_M)})
        p = pd.concat([p, propio], ignore_index=True)
        arr = np.array(celdas, dtype=object)
        return pd.DataFrame({"origen": arr[p["origen"]], "destino": arr[p["destino"]], "d": p["d"].to_numpy()})

    def isocrona(self, punto_xy: np.ndarray, limite: float, ancho_m: float = 35):
        """Polígono de la isócrona (calles alcanzadas con un buffer), en EPSG:6369."""
        from shapely.geometry import MultiLineString, Point
        from shapely.ops import unary_union
        i, s = self.ajustar(np.atleast_2d(punto_xy))
        dist = dijkstra(self.grafo, directed=False, indices=int(i[0]), limit=max(limite - s[0], 0))
        ok = np.isfinite(dist)
        aristas = ok[self.i] & ok[self.j] & (self.i < self.j)
        lineas = [(tuple(self.xy[a]), tuple(self.xy[b])) for a, b in zip(self.i[aristas], self.j[aristas])]
        if not lineas:
            return Point(punto_xy).buffer(ancho_m)
        return unary_union(MultiLineString(lineas).buffer(ancho_m))


# ---------------------------------------------------------------------------
# Isócronas (cobertura)
# ---------------------------------------------------------------------------
def score_isocrona(demanda: pd.DataFrame, establecimientos: gpd.GeoDataFrame, pares: pd.DataFrame,
                   minutos: float = 10, red: RedPeatonal | None = None,
                   pares_red: pd.DataFrame | None = None) -> tuple[pd.Series, str]:
    """Hogares objetivo a ≤ T min de c que hoy no tienen una 3B a ≤ T min. Devuelve (score, método)."""
    limite = limite_caminando_m(minutos)
    tiendas = establecimientos[establecimientos["cadena"].eq("3B")]
    centros = gd.centros_metricos(demanda["h3"])[["x", "y"]].to_numpy()
    if red is not None:
        d3b = red.distancia_minima(_xy(tiendas), centros, limite)
        alcance = pares_red if pares_red is not None else red.pares_alcance(demanda["h3"], limite)
        metodo = "red peatonal OSM"
    else:
        d3b, _ = cKDTree(_xy(tiendas)).query(centros)
        d3b = d3b * cfg.FACTOR_RODEO
        alcance = pares.assign(d=pares["d"] * cfg.FACTOR_RODEO)
        metodo = f"línea recta × {cfg.FACTOR_RODEO} (rodeo)"
    est = pd.DataFrame({"D": demanda["demanda_objetivo"].to_numpy(), "cubierto": d3b <= limite},
                       index=demanda["h3"].to_numpy())
    q = alcance[(alcance["d"] <= limite) & alcance["origen"].isin(est.index) & alcance["destino"].isin(est.index)]
    q = q.join(est, on="destino")
    s = (q["D"] * ~q["cubierto"]).groupby(q["origen"]).sum()
    out = demanda["h3"].map(s).fillna(0).rename(f"isocrona_{int(minutos)}")
    return out, metodo


def cobertura_isocrona(demanda: pd.DataFrame, establecimientos: gpd.GeoDataFrame, minutos: float = 10,
                       red: RedPeatonal | None = None) -> float:
    """% de la demanda objetivo con una 3B a ≤ T minutos caminando."""
    limite = limite_caminando_m(minutos)
    tiendas = establecimientos[establecimientos["cadena"].eq("3B")]
    centros = gd.centros_metricos(demanda["h3"])[["x", "y"]].to_numpy()
    if red is not None:
        d = red.distancia_minima(_xy(tiendas), centros, limite)
    else:
        d = cKDTree(_xy(tiendas)).query(centros)[0] * cfg.FACTOR_RODEO
    D = demanda["demanda_objetivo"].to_numpy()
    return float(D[d <= limite].sum() / D.sum())
