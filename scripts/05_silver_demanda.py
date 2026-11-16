"""Paso 5 · Silver de demanda: Censo 2020 + Marco Geoestadístico + CONEVAL.

Uso: python scripts/05_silver_demanda.py
Salidas en data/silver/ y docs/calidad_silver_demanda.md
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b.silver.demanda import ejecutar  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    resultado = ejecutar()
    print("\nSilver demanda listo\n" + "-" * 70)
    for k, v in resultado["stats"].items():
        print(f"{k:55s} {v}")
    print(f"\nTiempo: {time.time() - t0:.0f} s  |  Reporte: docs/calidad_silver_demanda.md")
