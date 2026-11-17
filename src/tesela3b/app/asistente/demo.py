"""Preguntas de ejemplo con respuesta determinista (sin modelo de lenguaje).

Se usan como "modo demo" cuando no hay llaves o el plan gratuito se agotó: las cifras salen de las mismas
herramientas que usa el agente, así que siempre son correctas y la pestaña nunca se ve rota.
"""
from __future__ import annotations

import json

from tesela3b.app.asistente.agente import Respuesta
from tesela3b.app.asistente.herramientas import Herramientas


def _m(x: float) -> str:
    return f"{x:,.0f}"


def _top_iztapalapa(h: Herramientas):
    r = h.top_zonas("equilibrada", 5, ["Iztapalapa"])
    z = json.loads(r.para_modelo)["zonas"]
    txt = (f"Las 5 mejores zonas de Iztapalapa (estrategia equilibrada) suman {_m(sum(x['hogares_nuevos'] for x in z))} "
           "hogares sin auto nuevos para la cadena:\n" +
           "\n".join(f"- **#{x['posicion']} {x['colonia'] or 'Sin colonia'}**: {_m(x['hogares_nuevos'])} hogares nuevos, "
                     f"canibalización {x['pct_canibalizacion']:.0f}%, 3B más cercana a {_m(x['dist_3b_m'])} m" for x in z))
    return txt, [r]


def _cobertura_tlahuac(h: Herramientas):
    r = h.resumen_alcaldia("Tláhuac")
    d = json.loads(r.para_modelo)
    txt = (f"En Tláhuac, **{_m(d['hogares_sin_auto_sin_3b_10min'])}** de {_m(d['hogares_sin_auto'])} hogares sin auto no tienen una "
           f"3B a 10 minutos caminando (cobertura actual: {d['pct_cobertura_10min']:.1f}%).\n"
           f"- Tiendas 3B: {d['tiendas_3b_2021']} en 2021 → {d['tiendas_3b_2026']} en 2026\n"
           f"- Neto y Bodega Aurrera en 2026: {d['neto_bodega_2026']}")
    return txt, [r]


def _simular_doctores(h: Herramientas):
    r = h.simular_apertura("Doctores", "Cuauhtémoc")
    d = json.loads(r.para_modelo)
    txt = (f"Una 3B en la colonia {d['colonia']} ({d['alcaldia']}) captaría **{_m(d['hogares_captados'])}** hogares sin auto, "
           f"pero {_m(d['hogares_canibalizados'])} ({d['pct_canibalizacion']:.0f}%) se los quitaría a otras 3B: "
           f"ganancia neta de **{_m(d['hogares_nuevos_para_la_cadena'])}** hogares para la cadena.\n"
           f"- La 3B más cercana está a {_m(d['dist_3b_m'])} m\n"
           f"- Hogares sin auto a 10 min caminando sin una 3B hoy: {_m(d['hogares_sin_auto_a_10min_sin_3b_hoy'])}\n"
           f"- Prioridad {d['prioridad_0_100']:.0f}/100")
    return txt, [r]


SQL_GRANDES = ("SELECT colonia, alcaldia, hogares_nuevos, pct_canibalizacion, dist_3b_m, h3, COUNT(*) OVER () AS total "
               "FROM zonas WHERE tiendas_3b = 0 AND hogares_nuevos > 500 AND pct_canibalizacion < 5 "
               "ORDER BY valor_esperado DESC")


def _grandes_sin_canib(h: Herramientas):
    r = h.consultar_datos(SQL_GRANDES)
    t = r.tabla
    if t is None or t.empty:
        return "No hay hexágonos con más de 500 hogares nuevos y menos de 5% de canibalización.", [r]
    alc = t["alcaldia"].value_counts().head(3)
    txt = (f"Hay **{int(t['total'].iloc[0])}** hexágonos sin 3B con más de 500 hogares nuevos y menos de 5% de canibalización. "
           "Se concentran en " + ", ".join(f"{a} ({n})" for a, n in alc.items()) + ". Los de mayor valor esperado:\n" +
           "\n".join(f"- {x.colonia or 'Sin colonia'} ({x.alcaldia}): {_m(x.hogares_nuevos)} hogares nuevos, "
                     f"canibalización {x.pct_canibalizacion:.1f}%" for x in t.head(4).itertuples()))
    return txt, [r]


FILTRO_COMPETENCIA = "neto_bodega_500m >= 1 AND NOT cubierta_10min AND tiendas_3b = 0"
SQL_COMPETENCIA = ("SELECT colonia, alcaldia, neto_bodega_500m, hogares_sin_auto, hogares_nuevos, h3 "
                   f"FROM zonas WHERE {FILTRO_COMPETENCIA} ORDER BY hogares_nuevos DESC")
SQL_COMPETENCIA_ALC = (f"SELECT alcaldia, COUNT(*) AS hexagonos, SUM(COUNT(*)) OVER () AS total FROM zonas "
                       f"WHERE {FILTRO_COMPETENCIA} GROUP BY alcaldia ORDER BY hexagonos DESC")


def _competencia_sin_3b(h: Herramientas):
    conteo = h.consultar_datos(SQL_COMPETENCIA_ALC)
    r = h.consultar_datos(SQL_COMPETENCIA)
    c, t = conteo.tabla, r.tabla
    txt = (f"**{_m(c['total'].iloc[0])}** hexágonos tienen un Neto o Bodega Aurrera a 500 m pero ninguna 3B a 10 minutos "
           "caminando: zonas donde el formato de descuento ya está probado y 3B no compite. Más frecuentes en " +
           ", ".join(f"{x.alcaldia} ({x.hexagonos})" for x in c.head(3).itertuples()) + ". Con más hogares nuevos:\n" +
           "\n".join(f"- {x.colonia or 'Sin colonia'} ({x.alcaldia}): {_m(x.hogares_nuevos)} hogares nuevos"
                     for x in t.head(4).itertuples()))
    return txt, [conteo, r]


def _comparar(h: Herramientas):
    a, b = h.resumen_alcaldia("Coyoacán"), h.resumen_alcaldia("Álvaro Obregón")
    da, db = json.loads(a.para_modelo), json.loads(b.para_modelo)
    fila = lambda d: (f"- **{d['alcaldia']}**: cobertura a 10 min {d['pct_cobertura_10min']:.1f}%, "
                      f"{_m(d['hogares_sin_auto_sin_3b_10min'])} hogares sin auto sin 3B cerca, "
                      f"3B {d['tiendas_3b_2021']} → {d['tiendas_3b_2026']}, competencia {d['neto_bodega_2026']}")
    mas = da if da["hogares_sin_auto_sin_3b_10min"] > db["hogares_sin_auto_sin_3b_10min"] else db
    txt = (f"{mas['alcaldia']} tiene más mercado sin atender a pie.\n{fila(da)}\n{fila(db)}")
    return txt, [a, b]


def _explicar_top1(h: Herramientas):
    top = h.top_zonas("equilibrada", 1)
    r = h.explicar_zona(h3=top.h3[0])
    d = json.loads(r.para_modelo)
    txt = (f"La zona #1 ({d['colonia']}, {d['alcaldia']}) tiene prioridad {d['prioridad_0_100']:.0f}/100 y aporta "
           f"{_m(d['hogares_nuevos'])} hogares nuevos. Lo que más la empuja:\n" +
           "\n".join(f"- {x[0].upper() + x[1:]}" for x in d["razones_a_favor"]))
    return txt, [top, r]


SQL_BACKTEST = ("SELECT anticipada_por_modelo, COUNT(*) AS aperturas, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct, "
                "SUM(COUNT(*)) OVER () AS total FROM aperturas GROUP BY 1 ORDER BY 2 DESC")


def _backtest(h: Herramientas):
    r = h.consultar_datos(SQL_BACKTEST)
    t = r.tabla.set_index("anticipada_por_modelo")
    total = int(t["total"].iloc[0])
    marc = t["aperturas"].get("En zona marcada", 0)
    junto = t["aperturas"].get("Junto a zona marcada", 0)
    txt = (f"De las {total} aperturas 3B de 2022 a 2026, **{marc}** cayeron en el 10% de la ciudad que el modelo marcaba "
           f"con datos de 2021 ({t['pct'].get('En zona marcada', 0):.0f}%) y {junto} más justo al lado "
           f"({t['pct'].get('Junto a zona marcada', 0):.0f}%). Al azar, en ese 10% de la ciudad habría caído ~10%.")
    return txt, [r]


EJEMPLOS = {
    "¿Cuáles son las 5 mejores zonas en Iztapalapa?": _top_iztapalapa,
    "¿Cuántos hogares sin auto no tienen una 3B a 10 minutos en Tláhuac?": _cobertura_tlahuac,
    "¿Qué pasa si abro una 3B en la colonia Doctores?": _simular_doctores,
    "¿Qué zonas tienen más de 500 hogares nuevos y menos de 5% de canibalización?": _grandes_sin_canib,
    "¿Dónde hay Neto o Bodega Aurrera pero ninguna 3B a 10 minutos?": _competencia_sin_3b,
    "Compara Coyoacán contra Álvaro Obregón": _comparar,
    "¿Por qué la zona #1 del Top está tan arriba?": _explicar_top1,
    "¿Cuántas aperturas reales anticipó el modelo?": _backtest,
}


def responder_demo(pregunta: str, h: Herramientas) -> Respuesta | None:
    f = EJEMPLOS.get(pregunta)
    if f is None:
        return None
    texto, resultados = f(h)
    return Respuesta(texto=texto, resultados=resultados, proveedor="Respuesta verificada (sin modelo)")
