"""Herramientas que el asistente puede pedir. Reutilizan la lógica ya probada de la app (logica.py).

Cada herramienta devuelve un Resultado con:
- `para_modelo`: texto JSON compacto (pocas filas, números redondeados) que se le manda al modelo;
- `tabla`: DataFrame para mostrar en la app;
- `h3`: hexágonos a resaltar en el mapa del chat.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

from tesela3b.app import logica as lg
from tesela3b.app.asistente import datos_sql as ds

ESTRATEGIAS = {"mercado": 0.0, "mas_mercado": 0.25, "equilibrada": 0.5, "mas_playbook": 0.75, "playbook": 1.0}
FILAS_MODELO = 25
MAX_CARACTERES = 4000   # ~1,200 tokens por resultado: los planes gratuitos limitan tokens por minuto


@dataclass
class Resultado:
    nombre: str
    argumentos: dict
    para_modelo: str
    tabla: pd.DataFrame | None = None
    h3: list[str] = field(default_factory=list)
    sql: str | None = None
    error: bool = False


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn").lower().strip()


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=lambda x: x.item() if hasattr(x, "item") else str(x))


def _registros(df: pd.DataFrame, n: int = FILAS_MODELO) -> list[dict]:
    d = df.head(n).copy()
    for c in d.select_dtypes("float").columns:
        d[c] = d[c].round(3 if d[c].abs().max() < 1.5 else 1)
    return d.to_dict(orient="records")


class Herramientas:
    def __init__(self, datos: lg.Datos):
        self.d = datos
        self.con = ds.construir(datos)
        self.alcaldias = sorted(datos.hexs["alcaldia"].dropna().unique())
        self._alc_norm = {_sin_acentos(a): a for a in self.alcaldias}

    # -- utilidades ---------------------------------------------------------------------------------
    def normalizar_alcaldia(self, nombre: str) -> str | None:
        n = _sin_acentos(nombre)
        n = {"gam": "gustavo a. madero", "gustavo a madero": "gustavo a. madero", "magdalena contreras": "la magdalena contreras",
             "cuajimalpa": "cuajimalpa de morelos", "benito juarez": "benito juarez"}.get(n, n)
        if n in self._alc_norm:
            return self._alc_norm[n]
        for k, v in self._alc_norm.items():
            if n and (n in k or k in n):
                return v
        return None

    def buscar_hexagono(self, colonia: str | None = None, alcaldia: str | None = None, h3: str | None = None) -> pd.Series | None:
        h = self.d.hexs
        if h3:
            f = h[h["h3"] == h3.strip()]
            return f.iloc[0] if len(f) else None
        if not colonia:
            return None
        c = h[h["colonia"].fillna("").map(_sin_acentos).str.contains(_sin_acentos(colonia), regex=False)]
        if alcaldia and (a := self.normalizar_alcaldia(alcaldia)):
            c = c[c["alcaldia"] == a]
        if c.empty:
            return None
        return c.sort_values("valor_esperado", ascending=False).iloc[0]   # el mejor hexágono de esa colonia

    # -- herramientas ---------------------------------------------------------------------------------
    def top_zonas(self, estrategia: str = "equilibrada", n: int = 10, alcaldias: list[str] | None = None,
                  canibalizacion_max: float | None = None, separacion_m: float = 600) -> Resultado:
        args = {"estrategia": estrategia, "n": n, "alcaldias": alcaldias, "canibalizacion_max": canibalizacion_max}
        w = ESTRATEGIAS.get(str(estrategia).lower(), 0.5)
        alc = None
        if alcaldias:
            alc = [a for a in (self.normalizar_alcaldia(x) for x in alcaldias) if a]
            if not alc:
                return Resultado("top_zonas", args, _json({"error": f"Alcaldías no reconocidas: {alcaldias}",
                                                           "validas": self.alcaldias}), error=True)
        n = int(max(1, min(n, 50)))
        h = self.d.hexs
        top = lg.seleccionar_top(h, lg.puntaje(h, w), n=n, separacion_m=separacion_m, alcaldias=alc,
                                 max_canibalizacion=canibalizacion_max)
        tabla = pd.DataFrame({"posicion": top["posicion"], "colonia": top["colonia"], "alcaldia": top["alcaldia"],
                              "hogares_nuevos": top["indice_final"].clip(lower=0).round(0),
                              "prob_zona_3b_pct": (100 * top["p_apertura"]).round(1),
                              "pct_canibalizacion": top["pct_canibalizacion"].round(1),
                              "dist_3b_m": top["dist_3b_m"].round(0), "h3": top["h3"]})
        return Resultado("top_zonas", args, _json({"zonas": _registros(tabla.drop(columns="h3")),
                                                   "total_hogares_nuevos": float(tabla["hogares_nuevos"].sum())}),
                         tabla=tabla, h3=tabla["h3"].tolist())

    def simular_apertura(self, colonia: str | None = None, alcaldia: str | None = None, h3: str | None = None) -> Resultado:
        args = {"colonia": colonia, "alcaldia": alcaldia, "h3": h3}
        f = self.buscar_hexagono(colonia, alcaldia, h3)
        if f is None:
            return Resultado("simular_apertura", args, _json({"error": "No encontré esa colonia o hexágono con vivienda. "
                                                                      "Usa consultar_datos con ILIKE para buscar el nombre."}), error=True)
        r = lg.simular(self.d, f["h3"])
        out = {"colonia": f["colonia"], "alcaldia": f["alcaldia"], "hogares_captados": round(r["capturada"]),
               "hogares_canibalizados": round(r["canibalizacion"]), "pct_canibalizacion": round(r["pct_canibalizacion"], 1),
               "hogares_nuevos_para_la_cadena": round(max(r["indice_final"], 0)),
               "hogares_sin_auto_a_10min": round(r.get("hogares_10min", 0)),
               "hogares_sin_auto_a_10min_sin_3b_hoy": round(r.get("hogares_10min_sin_3b", 0)),
               "dist_3b_m": round(r["dist_3b_m"]), "prob_zona_3b_pct": round(100 * float(f["p_apertura"]), 1),
               "prioridad_0_100": round(float(f["prioridad"]), 1), "ya_hay_3b_en_el_hexagono": bool(f["n_3b"] > 0)}
        return Resultado("simular_apertura", args, _json(out), tabla=pd.DataFrame([out]), h3=[f["h3"]])

    def explicar_zona(self, colonia: str | None = None, alcaldia: str | None = None, h3: str | None = None) -> Resultado:
        args = {"colonia": colonia, "alcaldia": alcaldia, "h3": h3}
        f = self.buscar_hexagono(colonia, alcaldia, h3)
        if f is None:
            return Resultado("explicar_zona", args, _json({"error": "No encontré esa zona."}), error=True)
        e = lg.explicar(f, self.d.modelo)
        out = {"colonia": f["colonia"], "alcaldia": f["alcaldia"], "prioridad_0_100": round(float(f["prioridad"]), 1),
               "prob_zona_3b_pct": round(100 * float(f["p_apertura"]), 1),
               "hogares_nuevos": round(max(float(f["indice_final"]), 0)),
               "razones_a_favor": lg.razones(f, self.d.modelo, n=4),
               "factores": [{"factor": r.etiqueta, "efecto": round(float(r.contribucion), 2)} for r in e.itertuples()],
               "nota": "efecto > 0 sube la probabilidad frente a la zona promedio de la CDMX"}
        return Resultado("explicar_zona", args, _json(out), tabla=e[["etiqueta", "contribucion"]].round(2), h3=[f["h3"]])

    def resumen_alcaldia(self, alcaldia: str) -> Resultado:
        args = {"alcaldia": alcaldia}
        a = self.normalizar_alcaldia(alcaldia or "")
        if not a:
            return Resultado("resumen_alcaldia", args, _json({"error": "Alcaldía no reconocida", "validas": self.alcaldias}), error=True)
        fila = ds.ejecutar(self.con, f"SELECT * FROM alcaldias WHERE alcaldia = '{a}'")
        top = self.top_zonas("equilibrada", 5, [a])
        out = {**_registros(fila)[0], "top5_zonas_de_la_alcaldia": json.loads(top.para_modelo)["zonas"]}
        return Resultado("resumen_alcaldia", args, _json(out), tabla=fila, h3=top.h3)

    def consultar_datos(self, sql: str) -> Resultado:
        args = {"sql": sql}
        try:
            df = ds.ejecutar(self.con, sql)
        except ds.ErrorConsulta as e:
            return Resultado("consultar_datos", args, _json({"error": str(e)}), sql=sql, error=True)
        h3s = df["h3"].dropna().astype(str).tolist()[:200] if "h3" in df.columns else []
        modelo = df.drop(columns=[c for c in ("h3", "lat", "lon") if c in df.columns])
        n = FILAS_MODELO
        texto = _json({"filas_totales": len(df), "filas": _registros(modelo, n)})
        while len(texto) > MAX_CARACTERES and n > 5:      # cuida el límite de tokens del plan gratuito
            n -= 5
            texto = _json({"filas_totales": len(df), "filas_mostradas": n, "filas": _registros(modelo, n)})
        return Resultado("consultar_datos", args, texto, tabla=df, h3=h3s, sql=sql)

    def ejecutar(self, nombre: str, argumentos: dict) -> Resultado:
        f = {"top_zonas": self.top_zonas, "simular_apertura": self.simular_apertura, "explicar_zona": self.explicar_zona,
             "resumen_alcaldia": self.resumen_alcaldia, "consultar_datos": self.consultar_datos}.get(nombre)
        if f is None:
            return Resultado(nombre, argumentos, _json({"error": f"Herramienta desconocida: {nombre}"}), error=True)
        try:
            return f(**{k: v for k, v in (argumentos or {}).items() if v is not None})
        except TypeError as e:
            return Resultado(nombre, argumentos, _json({"error": f"Argumentos inválidos: {e}"}), error=True)


# Esquemas (formato OpenAI "tools"; lo aceptan Groq y Gemini)
def _f(nombre, desc, props, req=()):
    params = {"type": "object", "properties": props}
    if req:                      # Gemini rechaza "required" vacío
        params["required"] = list(req)
    return {"type": "function", "function": {"name": nombre, "description": desc, "parameters": params}}


ESQUEMAS = [
    _f("top_zonas", "Mejores zonas para abrir una 3B (mismo cálculo que la app). Úsala para 'mejores zonas', 'dónde abrir', rankings.",
       {"estrategia": {"type": "string", "enum": list(ESTRATEGIAS),
                       "description": "equilibrada (recomendada) | mercado (más hogares nuevos) | playbook (como abre 3B)"},
        "n": {"type": "integer", "description": "cuántas zonas (1-50)"},
        "alcaldias": {"type": "array", "items": {"type": "string"}, "description": "filtrar por alcaldías"},
        "canibalizacion_max": {"type": "number", "description": "máximo % de canibalización permitido"}}),
    _f("simular_apertura", "Simula abrir una 3B en una colonia u hexágono: hogares captados, canibalización y cobertura a 10 min.",
       {"colonia": {"type": "string"}, "alcaldia": {"type": "string"}, "h3": {"type": "string"}}),
    _f("explicar_zona", "Explica por qué una zona tiene alta o baja prioridad (factores del modelo).",
       {"colonia": {"type": "string"}, "alcaldia": {"type": "string"}, "h3": {"type": "string"}}),
    _f("resumen_alcaldia", "Resumen de una alcaldía: hogares, cobertura a 10 min, tiendas 3B 2021/2026, aperturas, competencia y sus 5 mejores zonas.",
       {"alcaldia": {"type": "string"}}, ["alcaldia"]),
    _f("consultar_datos", "Consulta SQL (DuckDB, solo SELECT) para preguntas que las otras herramientas no cubren. " + ds.DICCIONARIO,
       {"sql": {"type": "string", "description": "una sola sentencia SELECT"}}, ["sql"]),
]
