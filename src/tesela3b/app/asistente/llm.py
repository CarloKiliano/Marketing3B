"""Adaptador a modelos de lenguaje con API compatible con OpenAI (Groq, Gemini y otros).

Cambiar de proveedor = cambiar las llaves/modelos en los Secrets de Streamlit; el resto del código no cambia.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import requests

# Modelos por omisión (se pueden cambiar en Secrets con GROQ_MODEL / GEMINI_MODEL)
CATALOGO = {
    "groq": {"nombre": "Groq", "base_url": "https://api.groq.com/openai/v1", "modelo": "openai/gpt-oss-120b",
             "llave": "GROQ_API_KEY", "var_modelo": "GROQ_MODEL"},
    "gemini": {"nombre": "Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "modelo": "gemini-3.8-flash", "llave": "GEMINI_API_KEY", "var_modelo": "GEMINI_MODEL"},
}
ORDEN = ("groq", "gemini")   # principal y respaldo


@dataclass(frozen=True)
class Proveedor:
    clave: str
    nombre: str
    base_url: str
    modelo: str
    llave: str

    def __repr__(self) -> str:   # nunca imprimir la llave
        return f"Proveedor({self.nombre}, {self.modelo})"


class ErrorProveedor(Exception):
    """Falla del proveedor (red, llave inválida, modelo inexistente…): se intenta con el siguiente."""


class LimiteProveedor(ErrorProveedor):
    """El plan gratuito llegó a su límite por minuto o por día (HTTP 429)."""


def proveedores_desde(secretos: Mapping) -> list[Proveedor]:
    out = []
    orden = [x.strip().lower() for x in str(secretos.get("LLM_ORDEN", ",".join(ORDEN))).split(",") if x.strip().lower() in CATALOGO]
    for clave in orden or ORDEN:
        c = CATALOGO[clave]
        llave = str(secretos.get(c["llave"], "") or "").strip()
        if llave and not llave.startswith("tu_"):
            base = str(secretos.get(f"{clave.upper()}_BASE_URL", c["base_url"])).rstrip("/")   # solo para pruebas
            out.append(Proveedor(clave, c["nombre"], base, str(secretos.get(c["var_modelo"], c["modelo"])), llave))
    return out


def chat(p: Proveedor, mensajes: list[dict], herramientas: list[dict] | None = None, temperatura: float = 0.1,
         max_tokens: int = 1200, timeout: float = 45, sesion=None) -> dict:
    """Una llamada a /chat/completions. Devuelve el `message` de la primera opción."""
    cuerpo = {"model": p.modelo, "messages": mensajes, "temperature": temperatura, "max_tokens": max_tokens}
    if herramientas:
        cuerpo["tools"] = herramientas
        cuerpo["tool_choice"] = "auto"
    http = sesion or requests
    try:
        r = http.post(f"{p.base_url}/chat/completions", json=cuerpo, timeout=timeout,
                      headers={"Authorization": f"Bearer {p.llave}", "Content-Type": "application/json"})
    except requests.RequestException as e:
        raise ErrorProveedor(f"{p.nombre}: sin conexión ({type(e).__name__})") from e
    if r.status_code == 429:
        raise LimiteProveedor(f"{p.nombre}: límite del plan gratuito alcanzado")
    if r.status_code >= 400:
        raise ErrorProveedor(f"{p.nombre}: error {r.status_code} {detalle_error(r)}".strip())
    try:
        return r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as e:
        raise ErrorProveedor(f"{p.nombre}: respuesta inesperada") from e


def detalle_error(r) -> str:
    """Mensaje de error del proveedor. Groq devuelve {"error": {...}}; Gemini a veces una lista [{"error": {...}}]."""
    try:
        j = r.json()
    except ValueError:
        return str(getattr(r, "text", ""))[:300]
    if isinstance(j, list) and j:
        j = j[0]
    if isinstance(j, dict):
        e = j.get("error", j)
        if isinstance(e, dict):
            return str(e.get("message") or e.get("status") or e)[:300]
        return str(e)[:300]
    return str(j)[:300]
