"""Paso 6 · Gold: índice de expansión por hexágono H3 (cortes 2021 y 2026) y Top 20.

Uso: python scripts/06_gold_indice.py
Salidas: data/gold/indice_h3_{corte}.parquet, data/gold/top20_{corte}.parquet, data/gold/parametros_{corte}.json,
         outputs/top20_zonas_3b.geojson, reports/indice_expansion.md
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b import config as cfg  # noqa: E402
from tesela3b.gold.indice_h3 import ejecutar  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    r = ejecutar()
    for corte, res in r.items():
        i = res["indice"]
        print(f"{corte}: {len(i):,} hexágonos | índice mediano {i.indice_final.median():,.0f} | "
              f"cuota 3B promedio {i.cuota_3b_actual.mean():.1%}")
    top = r[cfg.CORTE_ACTUAL]["top"]
    print(f"\nTop {cfg.TOP_N} ({cfg.CORTE_ACTUAL}) por alcaldía: {top.alcaldia.value_counts().to_dict()}")
    print(f"Tiempo: {time.time() - t0:.0f} s | Reporte: reports/indice_expansion.md | Entregable: outputs/top{cfg.TOP_N}_zonas_3b.geojson")
