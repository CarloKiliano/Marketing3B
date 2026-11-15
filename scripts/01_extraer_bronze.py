"""Paso 1 · Extrae las descargas originales (data/_downloads) a la capa Bronze."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tesela3b.ingest.extract_bronze import main  # noqa: E402

if __name__ == "__main__":
    main()
