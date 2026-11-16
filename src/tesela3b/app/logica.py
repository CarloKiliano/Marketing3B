"""Lógica de la app (sin Streamlit, para poder probarla): carga de datos, estrategia, Top N, simulador y fichas.

Solo depende de pandas, numpy y h3: funciona igual en la app publicada (sin geopandas ni datos crudos).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATOS = Path(__file__).resolve().parent / "datos"

# Parámetros del Huff anidado (mismos que la Fase 3; se leen de metricas.json si existen)
BETA_M, LAMBDA, RADIO_RED_M, DECAE_RED_M = 350.0, 0.5, 2500.0, 1000.0
LAT0 = 19.4   # para pasar grados a metros en la CDMX (aprox. equirrectangular)

ETIQUETAS_VARIABLES = {
    "log_indice": "Hogares nuevos que aporta (índice Huff)",
    "cuota_3b": "Ya hay clientes de 3B (canibalización)",
    "log_comercio_500": "Vida comercial de barrio (tienditas y OXXO a 500 m)",
    "log_hd_competencia_500": "Neto o Bodega Aurrera cerca",
    "fuera_red": "Lejos de la red 3B (más de 2.5 km)",
    "pct_sin_auto": "Hogares sin auto",
    "escolaridad_promedio": "Escolaridad promedio",
}


ETIQUETAS_CORTAS = {
    "log_indice": "Hogares nuevos",
    "cuota_3b": "Clientes 3B actuales",
    "log_comercio_500": "Comercio de barrio",
    "log_hd_competencia_500": "Neto/Bodega cerca",
    "fuera_red": "Lejos de la red",
    "pct_sin_auto": "Hogares sin auto",
    "escolaridad_promedio": "Escolaridad",
}


@dataclass
class Datos:
    hexs: pd.DataFrame
    estado: pd.DataFrame
    pares: pd.DataFrame
    alcance: pd.DataFrame | None
    tiendas: pd.DataFrame
    aperturas: pd.DataFrame
    backtest: pd.DataFrame
    metricas: dict
    modelo: dict
    capas: dict = field(default_factory=dict)


def cargar(carpeta: Path = DATOS) -> Datos:
    leer = lambda n: pd.read_parquet(carpeta / n)
    alcance = leer("alcance_10min.parquet") if (carpeta / "alcance_10min.parquet").exists() else None
    capas = {n: json.loads((carpeta / f"{n}.geojson").read_text(encoding="utf-8"))
             for n in ("alcaldias", "voronoi_3b", "isocronas_3b") if (carpeta / f"{n}.geojson").exists()}
    hexs = leer("hexagonos.parquet")
    hexs["x"], hexs["y"] = a_metros(hexs["lat"], hexs["lon"])
    return Datos(hexs=hexs, estado=leer("estado_huff.parquet").set_index("h3"), pares=leer("pares_1km.parquet"),
                 alcance=alcance, tiendas=leer("tiendas.parquet"), aperturas=leer("aperturas.parquet"),
                 backtest=leer("backtest_hex.parquet"),
                 metricas=json.loads((carpeta / "metricas.json").read_text(encoding="utf-8")),
                 modelo=json.loads((carpeta / "modelo_preferencia.json").read_text(encoding="utf-8")), capas=capas)


def a_metros(lat, lon) -> tuple[np.ndarray, np.ndarray]:
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return lon * 111_320 * math.cos(math.radians(LAT0)), lat * 110_574


# ---------------------------------------------------------------------------
# Estrategia y Top N
# ---------------------------------------------------------------------------
def puntaje(hexs: pd.DataFrame, peso_playbook: float = 0.5) -> pd.Series:
    """Prioridad = P(apertura)^w × hogares nuevos^(1−w).

    w = 0: solo mercado (índice Huff); w = 1: solo "dónde suele abrir 3B"; w = 0.5 ordena igual que el
    valor esperado del backtest (P × índice).
    """
    w = float(np.clip(peso_playbook, 0, 1))
    p = hexs["p_apertura"].clip(lower=1e-9)
    i = hexs["indice_final"].clip(lower=0)
    return pd.Series(np.power(p, w) * np.power(i, 1 - w), index=hexs.index)


def seleccionar_top(hexs: pd.DataFrame, score: pd.Series, n: int = 20, separacion_m: float = 600,
                    alcaldias: list[str] | None = None, max_canibalizacion: float | None = None) -> pd.DataFrame:
    """Selección voraz: el mejor hexágono elegible a ≥ separacion_m de los ya elegidos."""
    c = hexs.assign(puntaje=score)
    c = c[c["n_3b"].eq(0) & c["puntaje"].gt(0)]
    if alcaldias:
        c = c[c["alcaldia"].isin(alcaldias)]
    if max_canibalizacion is not None:
        c = c[c["pct_canibalizacion"] <= max_canibalizacion]
    c = c.sort_values("puntaje", ascending=False)
    xy, elegidos = np.empty((0, 2)), []
    for idx, x, y in zip(c.index, c["x"].to_numpy(), c["y"].to_numpy()):
        if len(xy) == 0 or np.min(np.hypot(xy[:, 0] - x, xy[:, 1] - y)) >= separacion_m:
            elegidos.append(idx)
            xy = np.vstack([xy, [x, y]])
            if len(elegidos) == n:
                break
    top = c.loc[elegidos].copy()
    top.insert(0, "posicion", range(1, len(top) + 1))
    return top.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Simulador "¿y si abro aquí?"
# ---------------------------------------------------------------------------
def factor_red(dist_m: float) -> float:
    return float(math.exp(-max(dist_m - RADIO_RED_M, 0) / DECAE_RED_M)) if np.isfinite(dist_m) else 0.0


def simular(datos: Datos, h: str, beta: float = BETA_M, lam: float = LAMBDA) -> dict:
    """Huff anidado para UNA tienda 3B nueva en el hexágono h (mismas fórmulas que indice_h3.calcular_indice)."""
    q = datos.pares[datos.pares["origen"] == h]
    if q.empty:
        return {"valido": False}
    q = q.join(datos.estado, on="destino")
    f = np.where(q["d"] <= 1000, np.exp(-q["d"].to_numpy() / beta), 0.0)
    i2 = q["i_hd"].to_numpy() + f
    p2 = np.power(i2, lam) / (q["den_sin_hd"].to_numpy() + np.power(i2, lam))
    D = q["D"].to_numpy()
    cap = D * p2 * f / i2
    can = D * (q["p3b"].to_numpy() - p2 * q["s3b"].to_numpy() / i2)
    por_hex = pd.DataFrame({"h3": q["destino"].to_numpy(), "capturada": cap, "canibalizacion": can})
    fila = datos.hexs.set_index("h3").loc[h] if h in set(datos.hexs["h3"]) else None
    dist = float(fila["dist_3b_m"]) if fila is not None else float("nan")
    capt, cani = float(cap.sum()), float(can.sum())
    out = {"valido": True, "h3": h, "capturada": capt, "canibalizacion": cani, "indice": capt - cani,
           "pct_canibalizacion": 100 * cani / capt if capt > 0 else 0.0, "dist_3b_m": dist,
           "factor_red": factor_red(dist), "por_hex": por_hex}
    out["indice_final"] = out["indice"] * out["factor_red"]
    if datos.alcance is not None:
        alc = datos.alcance.loc[datos.alcance["origen"] == h, "destino"]
        a = datos.hexs[datos.hexs["h3"].isin(set(alc) | {h})]
        out["alcance_10min"] = a["h3"].tolist()
        out["hogares_10min"] = float(a["hogares_sin_auto"].sum())
        out["hogares_10min_sin_3b"] = float(a.loc[~a["cubierto_10"], "hogares_sin_auto"].sum())
    if fila is not None:
        out.update({c: fila[c] for c in ("alcaldia", "colonia", "p_apertura", "prioridad", "valor_esperado", "n_3b",
                                         "lat", "lon") if c in fila})
    return out


# ---------------------------------------------------------------------------
# Ficha: por qué se eligió
# ---------------------------------------------------------------------------
def explicar(fila: pd.Series, modelo: dict) -> pd.DataFrame:
    """Contribución de cada variable al log-momio frente a la zona promedio de la CDMX (coef × valor estandarizado)."""
    v = modelo["variables"]
    z = (fila[v].to_numpy(float) - np.array(modelo["media"])) / np.array(modelo["escala"])
    contrib = z * np.array(modelo["coef"])
    etiquetas = [ETIQUETAS_VARIABLES.get(x, x) for x in v]
    if "fuera_red" in v and fila["fuera_red"] == 0:
        etiquetas[v.index("fuera_red")] = "Dentro de la red 3B (a menos de 2.5 km)"
    cortas = [ETIQUETAS_CORTAS.get(x, x) for x in v]
    if "fuera_red" in v and fila["fuera_red"] == 0:
        cortas[v.index("fuera_red")] = "Dentro de la red"
    return (pd.DataFrame({"variable": v, "etiqueta": etiquetas, "corta": cortas,
                          "contribucion": contrib, "valor": fila[v].to_numpy(float)})
            .sort_values("contribucion", ascending=False).reset_index(drop=True))


def razones(fila: pd.Series, modelo: dict, n: int = 3) -> list[str]:
    """Las n razones más fuertes a favor, en lenguaje de negocio."""
    e = explicar(fila, modelo)
    textos = {
        "log_comercio_500": f"calle con vida comercial ({fila['comercio_500']:.0f} tienditas y OXXO a 500 m)",
        "escolaridad_promedio": f"perfil del cliente 3B (escolaridad de {fila['escolaridad_promedio']:.1f} años)",
        "pct_sin_auto": f"{fila['pct_sin_auto']:.0f}% de los hogares compra a pie (sin auto)",
        "log_hd_competencia_500": f"{fila['hd_competencia_500']:.0f} tiendas de Neto/Bodega Aurrera cerca: zona probada de descuento",
        "log_indice": f"{fila['indice']:.0f} hogares sin auto nuevos para la cadena",
        "cuota_3b": "poca presencia actual de 3B",
        "fuera_red": "dentro del radio logístico de la red 3B",
    }
    return [textos[x] for x in e.loc[e["contribucion"] > 0, "variable"].head(n)]


def enlaces_mapa(lat: float, lon: float) -> dict:
    return {"maps": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}",
            "street_view": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}"}


# ---------------------------------------------------------------------------
# Cifras del resumen ejecutivo
# ---------------------------------------------------------------------------
def kpis(datos: Datos, top: pd.DataFrame) -> dict:
    m = datos.metricas
    comp = {c["modelo"]: c for c in m["comparacion"]}
    pref = comp["Modelo de preferencia revelada"]
    h = datos.hexs
    sin_cob = h.loc[~h["cubierto_10"], "hogares_sin_auto"].sum()
    return {"tiendas": m["tiendas_3b"][m["cortes"][1]], "tiendas_antes": m["tiendas_3b"][m["cortes"][0]],
            "cobertura": m["cobertura_10min"][m["cortes"][1]], "cobertura_antes": m["cobertura_10min"][m["cortes"][0]],
            "hogares_sin_cobertura": float(sin_cob), "lift_10": pref["lift_10"], "auc": pref["auc"],
            "hogares_top": float(top["indice_final"].sum()) if len(top) else 0.0}
