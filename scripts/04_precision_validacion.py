"""Paso 4 · Precisión de la identificación de tiendas 3B a partir de la validación manual.

1. Abre docs/validacion/muestra_validacion_3b.csv en Excel.
2. Para cada fila abre el enlace de Google Maps y escribe en la columna es_3b: SI, NO o NO SE.
3. Corre: python scripts/04_precision_validacion.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b import config as cfg  # noqa: E402
from tesela3b.silver.denue import precision_validacion  # noqa: E402

if __name__ == "__main__":
    r = precision_validacion(cfg.DOCS / "validacion" / "muestra_validacion_3b.csv")
    if not r.get("evaluadas"):
        print(f"Aún no hay respuestas SI/NO ({r.get('pendientes')} filas pendientes).")
    else:
        print(f"Evaluadas: {r['evaluadas']} | son 3B: {r['son_3b']} | dudosas: {r['dudosas']} | pendientes: {r['pendientes']}")
        print(f"Precisión estimada: {r['precision']:.1%}  (IC 95% Wilson: {r['ic95'][0]:.1%} – {r['ic95'][1]:.1%})")
