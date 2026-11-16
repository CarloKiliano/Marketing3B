"""Paso 9 · Paquete de datos de la app (src/tesela3b/app/datos/).

Uso: python scripts/09_preparar_app.py      (después de 06 y 08; usa la red OSM si existe)
Luego: streamlit run src/tesela3b/app/streamlit_app.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b.app.preparar import ejecutar  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    r = ejecutar()
    for f, mb in r["archivos_mb"].items():
        print(f"  {f:28s} {mb:6.2f} MB")
    print(f"Total {r['total_mb']} MB | isócronas: {r['metodo_isocrona']} | {time.time() - t0:.0f} s")
