"""Configuración central del proyecto: rutas, sistemas de referencia y parámetros."""
from pathlib import Path

# --- Rutas -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DOWNLOADS = DATA / "_downloads"   # archivos tal como se descargaron (nunca se modifican)
BRONZE = DATA / "bronze"          # datos crudos extraídos, sin transformar
SILVER = DATA / "silver"          # datos limpios, tipados y unidos (GeoParquet)
GOLD = DATA / "gold"              # features, índice H3 y salidas de modelo
OUTPUTS = ROOT / "outputs"        # entregables: Top 20 en GeoJSON, tablas finales
FIGURES = ROOT / "reports" / "figures"

# --- Sistemas de referencia (CRS) -----------------------------------------
CRS_WEB = "EPSG:4326"      # WGS84: almacenamiento, mapas web y GeoJSON
CRS_METRIC = "EPSG:6369"   # Mexico ITRF2008 / UTM 14N: distancias, áreas, KDE, isócronas
CRS_INEGI = "EPSG:6372"    # Cónica Conforme de Lambert de INEGI (Marco Geoestadístico)

# --- Área de estudio -------------------------------------------------------
CVE_ENT = "09"             # Ciudad de México

# --- Parámetros del modelo (valores iniciales, se ajustan en Gold) --------
H3_RES = 9                          # ~0.1 km2 por hexágono
KDE_BANDWIDTHS_M = [300, 500, 800]  # análisis de sensibilidad
ISOCHRONES_MIN = [5, 10]            # minutos caminando
WALK_SPEED_KMH = 4.5
MIN_DIST_CANDIDATAS_M = 600         # separación mínima entre zonas del Top 20
TOP_N = 20

# --- Patrones para identificar cadenas en el DENUE ------------------------
# Se validan manualmente en Silver; ajustar si aparecen falsos positivos.
PATRONES_CADENAS = {
    # Se busca en nom_estab + raz_social. Primer conteo (verificación Bronze):
    # 3B en CDMX = 153 (DENUE 11/2021) y 338 (DENUE 05/2026).
    "3B": r"TIENDAS?\s*3\s*B\b|TIENDAS?\s*TRES\s*B\b|^\s*T?3\s*B\s*$|BBB\s*FOODS?",
    "BODEGA_AURRERA": r"BODEGA\s*AURRERA|MI\s*BODEGA",   # revisar también raz_social de Walmart
    "NETO": r"TIENDAS?\s*NETO",
    "OXXO": r"\bOXXO\b",
    "SORIANA_EXPRESS": r"SORIANA\s*(EXPRESS|SUPER)",
}
# Solo tiendas al menudeo: excluye CEDIS, oficinas, etc. (462111 supermercados, 462112 minisupers)
SCIAN_TIENDAS = ("462111", "462112", "461110")
SCIAN_ABARROTES = "461110"   # Comercio al por menor en tiendas de abarrotes
