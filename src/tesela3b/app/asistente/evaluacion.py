"""Evaluación del asistente: 25 preguntas con respuesta conocida (20 sobre los datos y 5 fuera de los datos).

La respuesta correcta se calcula en vivo con las mismas herramientas, así que la prueba sigue siendo válida
si se regeneran los datos. Una respuesta es correcta si contiene la cifra o el nombre esperado; en las preguntas
fuera de alcance, si reconoce que "no está en los datos" (sin inventar cifras).
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from tesela3b.app.asistente import datos_sql as ds
from tesela3b.app.asistente.herramientas import Herramientas


def _norm(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower())


def _numeros(t: str) -> list[float]:
    from tesela3b.app.asistente.agente import _NUM, _a_numero
    return [_a_numero(m.group(0)) for m in _NUM.finditer(t)]


@dataclass
class Caso:
    pregunta: str
    tipo: str            # "numero" | "texto" | "fuera"
    esperado: object = None
    tolerancia: float = 0.01
    alternativas: tuple = ()     # otras formas correctas: cada una es una tupla de cifras que deben aparecer todas


def contiene(respuesta: str, caso: Caso) -> bool:
    if caso.tipo == "fuera":
        r = _norm(respuesta)
        return any(f in r for f in ("no esta en los datos", "no tengo datos", "no cuento con", "no esta disponible",
                                    "no se encuentra en los datos", "no incluye", "fuera de los datos"))
    if caso.tipo == "texto":   # esperado puede ser una lista de formas válidas (basta una)
        opciones = caso.esperado if isinstance(caso.esperado, (list, tuple)) else [caso.esperado]
        return any(_norm(o) in _norm(respuesta) for o in opciones)
    nums = _numeros(respuesta)
    esta = lambda v: any(abs(n - float(v)) <= max(caso.tolerancia * abs(float(v)), 0.051) for n in nums)
    return esta(caso.esperado) or any(all(esta(v) for v in grupo) for grupo in caso.alternativas)


def casos(h: Herramientas) -> list[Caso]:
    q = lambda sql: ds.ejecutar(h.con, sql)
    alc = q("SELECT * FROM alcaldias").set_index("alcaldia")
    top = lambda est, n=1, a=None: json.loads(h.top_zonas(est, n, a).para_modelo)["zonas"]
    sim = lambda c, a: json.loads(h.simular_apertura(c, a).para_modelo)
    coy = q("SELECT colonia FROM zonas WHERE alcaldia = 'Coyoacán' AND tiendas_3b = 0 ORDER BY prob_zona_3b DESC LIMIT 1")
    return [
        Caso("¿Cuál es la zona número 1 para abrir una 3B en la CDMX?", "texto", top("equilibrada")[0]["colonia"]),
        Caso("¿Cuál es la mejor zona para abrir en Iztapalapa?", "texto", top("equilibrada", 1, ["Iztapalapa"])[0]["colonia"]),
        Caso("¿Qué porcentaje de los hogares sin auto de Cuauhtémoc tiene una 3B a 10 minutos caminando?", "numero",
             alc.loc["Cuauhtémoc", "pct_cobertura_10min"]),
        Caso("¿Cuántos hogares sin auto de Tláhuac no tienen una 3B a 10 minutos?", "numero",
             alc.loc["Tláhuac", "hogares_sin_auto_sin_3b_10min"]),
        Caso("¿Cuántas tiendas 3B hay hoy en Gustavo A. Madero?", "numero", alc.loc["Gustavo A. Madero", "tiendas_3b_2026"]),
        Caso("¿Cuántas tiendas 3B había en Iztapalapa en 2021?", "numero", alc.loc["Iztapalapa", "tiendas_3b_2021"]),
        Caso("¿Cuántas tiendas abrió 3B en Álvaro Obregón entre 2022 y 2026?", "numero", alc.loc["Álvaro Obregón", "aperturas_2022_2026"]),
        Caso("¿Cuántas tiendas de Neto y Bodega Aurrera hay en Tlalpan?", "numero", alc.loc["Tlalpan", "neto_bodega_2026"],
             alternativas=(tuple(q("SELECT COUNT(*) n FROM tiendas WHERE alcaldia = 'Tlalpan' AND corte = '2026' AND cadena <> '3B' "
                                   "GROUP BY cadena ORDER BY cadena")["n"]),)),     # desglosado por cadena también es correcto
        Caso("Si abro una 3B en la colonia Doctores de Cuauhtémoc, ¿cuántos hogares sin auto captaría?", "numero",
             sim("Doctores", "Cuauhtémoc")["hogares_captados"], 0.02),
        Caso("¿Cuántos hogares nuevos ganaría la cadena con una 3B en Chinampac de Juárez, Iztapalapa?", "numero",
             sim("Chinampac de Juárez", "Iztapalapa")["hogares_nuevos_para_la_cadena"], 0.02),
        # el factor que más pesa en el modelo es la vida comercial de barrio; el modelo puede nombrarlo de varias formas
        Caso("¿Por qué la zona número 1 del Top tiene tanta prioridad?", "texto",
             ["comerci", "tiendita", "oxxo", "tiendas de barrio", "abarrote", "negocios"]),
        Caso("¿Qué alcaldía tiene más hogares sin auto sin una 3B a 10 minutos?", "texto",
             alc["hogares_sin_auto_sin_3b_10min"].idxmax()),
        Caso("¿Qué alcaldía tiene la menor cobertura de 3B a 10 minutos caminando?", "texto", alc["pct_cobertura_10min"].idxmin()),
        Caso("¿Cuántos hogares sin auto hay en total en la CDMX según los datos?", "numero", alc["hogares_sin_auto"].sum(), 0.01),
        Caso("¿Cuántos hexágonos sin 3B tienen más de 500 hogares nuevos y menos de 5% de canibalización?", "numero",
             q("SELECT COUNT(*) n FROM zonas WHERE tiendas_3b = 0 AND hogares_nuevos > 500 AND pct_canibalizacion < 5")["n"][0]),
        Caso("¿Cuántas de las aperturas reales cayeron en las zonas que marcaba el modelo?", "numero",
             q("SELECT COUNT(*) n FROM aperturas WHERE anticipada_por_modelo = 'En zona marcada'")["n"][0]),
        Caso("Con la estrategia de mercado, ¿cuál es la mejor zona?", "texto", top("mercado")[0]["colonia"]),
        Caso("Con la estrategia playbook 3B, ¿cuál es la mejor zona?", "texto", top("playbook")[0]["colonia"]),
        Caso("¿Qué colonia de Coyoacán sin 3B se parece más a donde abre 3B?", "texto", coy["colonia"][0]),
        Caso("Entre Coyoacán y Álvaro Obregón, ¿cuál tiene más hogares sin auto sin una 3B cerca?", "texto",
             max(["Coyoacán", "Álvaro Obregón"], key=lambda a: alc.loc[a, "hogares_sin_auto_sin_3b_10min"])),
        Caso("¿Cuánto vende al mes la 3B de la colonia Doctores?", "fuera"),
        Caso("¿Cuál es la renta promedio de un local comercial en Iztapalapa?", "fuera"),
        Caso("¿Dónde conviene abrir una 3B en Guadalajara?", "fuera"),
        Caso("¿Cuántas tiendas va a abrir 3B en la CDMX en 2027?", "fuera"),
        Caso("¿A qué hora abre la 3B de Coyoacán?", "fuera"),
    ]
