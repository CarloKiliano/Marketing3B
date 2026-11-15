"""Capa Bronze: extrae los archivos de data/_downloads a data/bronze sin modificarlos.

Uso (desde la raíz del repo, con el entorno activado):
    python scripts/01_extraer_bronze.py

Es idempotente: omite archivos que ya existen completos y reescribe los incompletos.
"""
import io
import shutil
import zipfile
from pathlib import Path

from tesela3b.config import BRONZE, CVE_ENT, DOWNLOADS

# archivo descargado -> carpeta destino en bronze
FUENTES = {
    "denue_09_csv.zip": BRONZE / "denue" / "2026_05",
    "denue_09_1121_csv.zip": BRONZE / "denue" / "2021_11",
    "resageburb_09csv20.zip": BRONZE / "censo2020",
    "GRS_AGEB_urbana_2020.zip": BRONZE / "coneval",
}
MARCO_GEO_ZIP = "889463807469_s.zip"  # Marco Geoestadístico, Censo de Población y Vivienda 2020
MARCO_GEO_ENTIDAD = f"{CVE_ENT}_ciudaddemexico.zip"
# Solo las capas que usa el proyecto (el resto, p. ej. frentes de manzana, pesa ~335 MB)
CAPAS_MARCO_GEO = ("a", "mun", "ent", "m", "l")  # AGEB urbana, alcaldías, entidad, manzanas, localidades
AFLUENCIA_CSV = "afluenciastc_desglosado_09_2026.csv"


def _extraer_miembros(z: zipfile.ZipFile, destino: Path, filtro=lambda nombre: True) -> int:
    n = 0
    for info in z.infolist():
        if info.is_dir() or not filtro(info.filename):
            continue
        objetivo = (destino / info.filename).resolve()
        if not str(objetivo).startswith(str(destino.resolve())):
            raise ValueError(f"Ruta insegura en el ZIP: {info.filename}")
        if objetivo.exists() and objetivo.stat().st_size == info.file_size:
            continue  # ya existe completo
        objetivo.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as src, open(objetivo, "wb") as dst:
            shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
        n += 1
    return n


def extraer_zip(origen: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(origen) as z:
        n = _extraer_miembros(z, destino)
    print(f"[ok] {origen.name} -> {destino.relative_to(BRONZE.parent)} ({n} archivos escritos)")


def extraer_marco_geo() -> None:
    """Del ZIP nacional (~3 GB) toma solo la entidad y, de ella, solo las capas necesarias."""
    destino = BRONZE / "marco_geo"
    capas = tuple(f"conjunto_de_datos/{CVE_ENT}{c}." for c in CAPAS_MARCO_GEO)

    def util(nombre: str) -> bool:
        return nombre.startswith(capas) or nombre.startswith(("catalogos/", "metadatos/"))

    with zipfile.ZipFile(DOWNLOADS / MARCO_GEO_ZIP) as nacional:
        datos = nacional.read(MARCO_GEO_ENTIDAD)
    with zipfile.ZipFile(io.BytesIO(datos)) as entidad:
        n = _extraer_miembros(entidad, destino, util)
    print(f"[ok] {MARCO_GEO_ZIP}::{MARCO_GEO_ENTIDAD} -> data/bronze/marco_geo ({n} archivos escritos)")


def copiar_afluencia() -> None:
    origen = DOWNLOADS / AFLUENCIA_CSV
    destino = BRONZE / "movilidad" / AFLUENCIA_CSV
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists() or destino.stat().st_size != origen.stat().st_size:
        shutil.copyfile(origen, destino)
    print(f"[ok] {AFLUENCIA_CSV} -> data/bronze/movilidad")


def main() -> None:
    for archivo, destino in FUENTES.items():
        extraer_zip(DOWNLOADS / archivo, destino)
    extraer_marco_geo()
    copiar_afluencia()
    print("\nBronze listo. Siguiente paso: python scripts/02_verificar_bronze.py")


if __name__ == "__main__":
    main()
