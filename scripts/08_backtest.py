"""Paso 8 · Backtest 2021 -> 2026, comparación de métodos, calibración y recomendación final.

Uso: python scripts/08_backtest.py        (requiere haber corrido 06; 07 es opcional: red peatonal OSM)
Salidas: data/gold/backtest_2021_11.parquet, data/gold/prioridad_2026_05.parquet, data/gold/modelo_preferencia.json,
         outputs/top20_zonas_3b.geojson (recomendación final), reports/backtest.md
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b import config as cfg  # noqa: E402
from tesela3b.gold.backtest import ejecutar  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    r = ejecutar()
    print(f"Isócronas: {r['metodo_isocrona']}")
    print(r["comparacion"][["modelo", "auc", "auc_ic_inf", "auc_ic_sup", "captura_10", "lift_10"]]
          .sort_values("auc", ascending=False).round(3).to_string(index=False))
    for n, (_, a) in r["tops_2021"].items():
        print(f"Top {cfg.TOP_N} 2021 · {n}: {a['aciertos']}/{a['zonas']} aciertos (azar {a['tasa_azar']:.0%}, lift {a['lift']:.1f}x)")
    print(f"\nTop {cfg.TOP_N} final ({cfg.CORTE_ACTUAL}) por alcaldía: {r['top_2026'].alcaldia.value_counts().to_dict()}")
    print(f"Tiempo: {time.time() - t0:.0f} s | Reporte: reports/backtest.md | Entregable: outputs/top{cfg.TOP_N}_zonas_3b.geojson")
