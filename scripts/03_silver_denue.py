"""Paso 3 · Silver del DENUE: tiendas de despensa por cadena, tiendas 3B y aperturas 2021→2026.

Uso: python scripts/03_silver_denue.py
Salidas en data/silver/, docs/calidad_silver_denue.md y docs/validacion/muestra_validacion_3b.csv
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b.silver.denue import ejecutar  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    resultado = ejecutar()
    print("\nSilver DENUE listo\n" + "-" * 60)
    for k, v in resultado["stats"].items():
        print(f"{k:58s} {v}")
    print(f"\nTiempo: {time.time() - t0:.0f} s")
    print("Siguiente: valida a mano docs/validacion/muestra_validacion_3b.csv y corre scripts/04_precision_validacion.py")
