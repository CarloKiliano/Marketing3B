"""Paso 10 · Evalúa el asistente "Pregúntale al mapa" con 25 preguntas de respuesta conocida.

Uso (con tus llaves en .streamlit/secrets.toml o como variables de entorno):
    python scripts/10_evaluar_asistente.py                 # Groq con respaldo Gemini
    python scripts/10_evaluar_asistente.py --solo gemini   # un solo proveedor
Salida: reports/evaluacion_asistente.md
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tesela3b.app import logica as lg  # noqa: E402
from tesela3b.app.asistente import agente as ag  # noqa: E402
from tesela3b.app.asistente import evaluacion as ev  # noqa: E402
from tesela3b.app.asistente import llm  # noqa: E402
from tesela3b.app.asistente.herramientas import Herramientas  # noqa: E402


def secretos() -> dict:
    out = dict(os.environ)
    archivo = ROOT / ".streamlit" / "secrets.toml"
    if archivo.exists():
        import tomllib
        out.update(tomllib.loads(archivo.read_text(encoding="utf-8")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=list(llm.CATALOGO), help="usar un solo proveedor")
    ap.add_argument("--pausa", type=float, default=4.0, help="segundos entre preguntas (cuida el plan gratuito)")
    ap.add_argument("--preguntas", help="solo estas preguntas, p. ej. 4,11 (no reescribe el reporte)")
    a = ap.parse_args()
    prov = [p for p in llm.proveedores_desde(secretos()) if not a.solo or p.clave == a.solo]
    if not prov:
        sys.exit("No encontré llaves (GROQ_API_KEY / GEMINI_API_KEY) en .streamlit/secrets.toml ni en el entorno.")
    h = Herramientas(lg.cargar())
    filas, completas, aciertos = [], [], 0
    elegidas = {int(x) for x in a.preguntas.split(",")} if a.preguntas else None
    for i, c in enumerate(ev.casos(h), 1):
        if elegidas and i not in elegidas:
            continue
        t0 = time.time()
        r = ag.responder(c.pregunta, [], prov, h)
        ok = (not r.error) and ev.contiene(r.texto, c)
        aciertos += ok
        herrs = ", ".join(x.nombre for x in r.resultados) or "—"
        print(f"{i:2d}. {'OK ' if ok else 'MAL'} [{r.proveedor or 'sin respuesta'}] {c.pregunta}")
        for aviso in r.avisos:
            print(f"      aviso: {aviso}")
        if not ok or elegidas:
            print("      respuesta: " + r.texto.replace("\n", "\n                 "))
        completas.append(f"### {i}. {'✅' if ok else '❌'} {c.pregunta}\n\n{r.texto}\n")
        filas.append(f"| {i} | {'✅' if ok else '❌'} | {c.pregunta} | {c.esperado if c.tipo != 'fuera' else 'reconocer que no está en los datos'} "
                     f"| {r.texto[:160].replace(chr(10), ' ').replace('|', '/')}… | {herrs} | {r.proveedor} | "
                     f"{', '.join(r.cifras_no_verificadas) or '—'} | {time.time() - t0:.1f} s | {'; '.join(r.avisos).replace('|', '/') or '—'} |")
        time.sleep(a.pausa)
    n = len(filas)
    if elegidas:
        print(f"\n{aciertos}/{n} correctas (prueba parcial; el reporte no se modificó)")
        return
    rep = (f"# Evaluación del asistente «Pregúntale al mapa»\n\nGenerado por `scripts/10_evaluar_asistente.py`. "
           f"Proveedores: {', '.join(f'{p.nombre} ({p.modelo})' for p in prov)}.\n\n"
           f"**Resultado: {aciertos} de {n} correctas ({aciertos / n:.0%}).** 20 preguntas sobre los datos y 5 fuera de los datos "
           "(debe reconocer que no puede responder).\n\n"
           "| # | ¿Correcta? | Pregunta | Esperado | Respuesta (inicio) | Herramientas | Proveedor | Cifras sin verificar | Tiempo | Avisos |\n"
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(filas) + "\n"
           "\n## Respuestas completas\n\n" + "\n".join(completas))
    (ROOT / "reports" / "evaluacion_asistente.md").write_text(rep, encoding="utf-8")
    print(f"\n{aciertos}/{n} correctas -> reports/evaluacion_asistente.md")


if __name__ == "__main__":
    main()
