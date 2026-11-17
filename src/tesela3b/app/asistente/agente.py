"""Agente "Pregúntale al mapa": pregunta -> herramientas -> respuesta con cifras verificables.

Ciclo: el modelo pide herramientas (máximo MAX_PASOS rondas), la app las ejecuta sobre los datos y el modelo
redacta la respuesta. Si el proveedor principal falla o llega a su límite, se repite con el de respaldo.
Después se verifica que cada cifra del texto aparezca en los resultados de las herramientas.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from tesela3b.app.asistente import llm
from tesela3b.app.asistente.herramientas import ESQUEMAS, Herramientas, Resultado

MAX_PASOS = 5
TURNOS_HISTORIAL = 6

SISTEMA = """Eres el asistente del "Mapa de expansión 3B · CDMX", una propuesta académica (no afiliada a BBB Foods).
Respondes a un director de expansión, en español de México, de forma breve y con cifras.

Reglas:
1. TODA cifra de tu respuesta debe venir de una herramienta usada en esta conversación. Nunca inventes ni estimes.
2. Prefiere top_zonas, simular_apertura, explicar_zona y resumen_alcaldia. Usa consultar_datos solo si no alcanzan.
3. Si piden algo que NO está en los datos (ventas, rentas, utilidades, tráfico, horarios, otros estados, el futuro,
   personas), di "Eso no está en los datos de la app" y sugiere qué sí puedes responder. No uses herramientas para eso.
4. Glosario: "hogares nuevos" = hogares sin auto que una 3B ganaría para la cadena, ya descontada la canibalización.
   "Prob. zona tipo 3B" = qué tanto se parece a donde 3B abrió en 2021-2026 (NO es probabilidad de éxito ni de ventas).
   "Cobertura a 10 min" = hogares sin auto con una 3B a 10 minutos caminando por la calle.
   Datos: DENUE mayo 2026 y nov 2021 (INEGI), Censo 2020, CONEVAL, OpenStreetMap.
5. No muestres SQL, JSON ni nombres de herramientas: la app ya muestra la tabla, el mapa y cómo se calculó.
6. Escribe los miles con coma (36,369) y los decimales con punto (42.7%).
7. Formato: una o dos frases con la respuesta directa y, si ayuda, hasta 5 viñetas cortas con números.
   Sin tablas markdown. Máximo ~120 palabras."""


@dataclass
class Respuesta:
    texto: str
    resultados: list[Resultado] = field(default_factory=list)
    proveedor: str = ""
    modelo: str = ""
    cifras_no_verificadas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    error: bool = False

    @property
    def h3(self) -> list[str]:
        vistos, out = set(), []
        for r in self.resultados:
            for h in r.h3:
                if h not in vistos:
                    vistos.add(h)
                    out.append(h)
        return out


# ---------------------------------------------------------------------------
# Verificación de cifras
# ---------------------------------------------------------------------------
# Miles con coma, espacio o espacio fino (los modelos escriben "36,369", "36 369" o "36 369")
_SEP = "[,\u00a0\u202f\u2009 ]"
_NUM = re.compile(rf"(?<![\w.])-?\d{{1,3}}(?:{_SEP}\d{{3}})+(?:\.\d+)?(?!\d)|(?<![\w.])-?\d+(?:\.\d+)?")


def _a_numero(t: str) -> float:
    return float(re.sub(_SEP, "", t))


def _numeros_texto(t: str) -> list[tuple[str, float]]:
    return [(m.group(0), _a_numero(m.group(0))) for m in _NUM.finditer(t)]


def _numeros_json(obj, acc: set[float]) -> set[float]:
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        acc.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numeros_json(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _numeros_json(v, acc)
    elif isinstance(obj, str):
        for _, v in _numeros_texto(obj):
            acc.add(v)
    return acc


def verificar_cifras(texto: str, resultados: list[Resultado], pregunta: str = "") -> list[str]:
    """Cifras del texto que no salen de ninguna herramienta (ni de la pregunta). Tolera redondeos y porcentajes."""
    fuente: set[float] = set()
    for r in resultados:
        try:
            _numeros_json(json.loads(r.para_modelo), fuente)
        except ValueError:
            pass
        if r.tabla is not None:
            for v in r.tabla.select_dtypes("number").to_numpy().ravel():
                fuente.add(float(v))
    fuente |= {v for _, v in _numeros_texto(pregunta)}
    derivados = set()
    for v in fuente:
        derivados |= {v, round(v), round(v, 1), round(v * 100), round(v * 100, 1), round(v / 1000), round(v / 1000, 1),
                      round(v / 1e6, 1), round(v / 1e6, 2)}
    sospechosas = []
    for crudo, v in _numeros_texto(texto):
        if abs(v) <= 20 or 2019 <= v <= 2027:   # posiciones, conteos chicos y años
            continue
        if not any(abs(v - d) <= max(0.051, 0.006 * abs(v)) for d in derivados):
            sospechosas.append(crudo)
    return sospechosas


# ---------------------------------------------------------------------------
# Ciclo del agente
# ---------------------------------------------------------------------------
def _ciclo(p: llm.Proveedor, pregunta: str, historial: list[dict], herr: Herramientas, chat=llm.chat) -> Respuesta:
    mensajes = [{"role": "system", "content": SISTEMA}] + historial[-TURNOS_HISTORIAL:] + [{"role": "user", "content": pregunta}]
    resultados: list[Resultado] = []
    texto = None
    for _ in range(MAX_PASOS):
        m = chat(p, mensajes, ESQUEMAS)
        llamadas = m.get("tool_calls") or []
        if not llamadas:
            texto = (m.get("content") or "").strip()
            break
        mensajes.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": llamadas})
        for i, c in enumerate(llamadas):
            nombre = c.get("function", {}).get("name", "")
            try:
                args = json.loads(c.get("function", {}).get("arguments") or "{}")
            except ValueError:
                args = {}
            r = herr.ejecutar(nombre, args if isinstance(args, dict) else {})
            resultados.append(r)
            msg = {"role": "tool", "tool_call_id": c.get("id") or f"llamada_{len(resultados)}_{i}", "content": r.para_modelo}
            if p.clave == "gemini":
                msg["name"] = nombre
            mensajes.append(msg)
    if texto is None:   # agotó las rondas: pedir la respuesta final sin más herramientas
        mensajes.append({"role": "user", "content": "Responde ya con la información que tienes."})
        texto = (chat(p, mensajes, None).get("content") or "").strip()
    if not texto:
        texto = "No pude formular una respuesta. Intenta reformular la pregunta."
    return Respuesta(texto=texto, resultados=resultados, proveedor=p.nombre, modelo=p.modelo,
                     cifras_no_verificadas=verificar_cifras(texto, resultados, pregunta))


def responder(pregunta: str, historial: list[dict], proveedores: list[llm.Proveedor], herr: Herramientas,
              chat=llm.chat) -> Respuesta:
    """Intenta con cada proveedor en orden (principal, respaldo)."""
    avisos = []
    for p in proveedores:
        try:
            r = _ciclo(p, pregunta, historial, herr, chat)
            r.avisos = avisos
            return r
        except llm.LimiteProveedor as e:
            avisos.append(str(e))
        except llm.ErrorProveedor as e:
            avisos.append(str(e))
        except Exception as e:   # nunca tumbar la app por una respuesta rara del proveedor
            avisos.append(f"{p.nombre}: error inesperado ({type(e).__name__}: {str(e)[:200]})")
    texto = ("Los modelos gratuitos no están disponibles en este momento (límite por minuto o por día). "
             "Espera un minuto e intenta de nuevo, o usa las preguntas de ejemplo, que funcionan sin modelo.")
    return Respuesta(texto=texto, avisos=avisos, error=True)
