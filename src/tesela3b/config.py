"""Configuración central del proyecto: rutas, sistemas de referencia y parámetros de negocio.

Regla: ningún número "mágico" vive dentro de la lógica; todo parámetro se define aquí con su porqué.
"""
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
DOCS = ROOT / "docs"

# --- Sistemas de referencia (CRS) -----------------------------------------
CRS_WEB = "EPSG:4326"      # WGS84: almacenamiento, mapas web y GeoJSON
CRS_METRIC = "EPSG:6369"   # Mexico ITRF2008 / UTM 14N: distancias, áreas, KDE, isócronas
# El Marco Geoestadístico viene en "MEXICO_ITRF_2008_LCC" (Lambert de INEGI, equivalente a
# EPSG:6372 pero sin código EPSG en su .prj): se reproyecta leyendo su propio .prj.

# --- Área de estudio -------------------------------------------------------
CVE_ENT = "09"             # Ciudad de México
BBOX_CDMX = (-99.37, 19.04, -98.94, 19.60)   # lon_min, lat_min, lon_max, lat_max (validación)

# --- Cortes temporales del DENUE ------------------------------------------
CORTE_BACKTEST = "2021_11"   # "foto" del pasado: se construye el índice solo con esto
CORTE_ACTUAL = "2026_05"     # "foto" actual: recomendación final y etiqueta del backtest
CORTES = (CORTE_BACKTEST, CORTE_ACTUAL)

# --- Silver · DENUE --------------------------------------------------------
# Dos registros de la misma cadena a menos de esta distancia son la misma tienda registrada
# dos veces (EDA: misma manzana, distinta fecha de alta). Se conserva el registro más antiguo.
UMBRAL_DUPLICADO_M = 50
# Para la competencia el umbral es menor: en zonas densas hay OXXO/7-Eleven reales a 25-50 m
# entre sí (direcciones distintas); por debajo de 25 m casi siempre es el mismo punto.
UMBRAL_DUPLICADO_COMPETENCIA_M = 25
# Una tienda 3B del corte actual es "apertura" si no había una 3B del corte anterior a menos
# de esta distancia. Se reporta sensibilidad con los umbrales alternativos.
UMBRAL_APERTURA_M = 100
UMBRALES_APERTURA_SENSIBILIDAD = (50, 100, 200)
# Tamaño de la muestra para validar a mano la identificación de tiendas 3B.
N_MUESTRA_VALIDACION = 50
SEMILLA = 42

# Códigos SCIAN de tiendas al menudeo de despensa (excluye CEDIS, oficinas, mayoreo).
SCIAN_ABARROTES = "461110"     # tiendas de abarrotes, ultramarinos y misceláneas
SCIAN_SUPERMERCADO = "462111"  # supermercados
SCIAN_MINISUPER = "462112"     # minisupers
SCIAN_TIENDAS = (SCIAN_ABARROTES, SCIAN_SUPERMERCADO, SCIAN_MINISUPER)
SCIAN_MAYOREO_ABARROTES = "431110"  # en 2021 INEGI registró aquí a la mayoría de las Neto

# --- Gold · Índice de expansión (supuestos iniciales; se calibran en el backtest) ---
H3_RES = 9                 # ~0.1 km² por hexágono; centros vecinos a ~350 m
# Demanda objetivo: "hogares_sin_auto" (compran su despensa caminando: el cliente 3B) u "hogares".
DEMANDA_OBJETIVO = "hogares_sin_auto"
# Modelo de Huff: P(hogar en h compra en tienda j) = A_j·f(d) / (α0 + Σ A_k·f(d_k)),  f(d) = exp(-d/β)
HUFF_BETA_M = 350          # decaimiento: a 350 m la atracción cae a 37%; a 700 m, a 14%
HUFF_RADIO_MAX_M = 1000    # más allá de 1 km caminando, la atracción se considera nula
HUFF_DIST_MIN_M = 120      # distancia típica dentro del mismo hexágono (evita d = 0)
HUFF_OPCION_EXTERNA = 1.0  # α0: mercados, tianguis y otras opciones no registradas en el DENUE
# Huff anidado (nested logit): el hogar elige primero el TIPO de tienda (nido) y luego la tienda.
# λ ∈ (0, 1]: λ = 1 es el Huff simple; λ < 1 hace que una 3B nueva compita sobre todo dentro de su
# nido (hard discount) -> canibalización realista entre tiendas 3B cercanas.
HUFF_LAMBDA_NIDO = 0.5
# Atractivo relativo por formato (3B = 1). Supuestos de partida: se prueban en el backtest.
ATRACTIVO = {
    "3B": 1.0,
    "Hard discount": 1.0,   # Neto y Bodega Aurrera compiten directo por precio
    "Supermercado": 2.0,    # surtido amplio, pero menos visitas de reposición
    "Conveniencia": 0.4,    # OXXO/7-Eleven: sustituto parcial de la despensa
    "Tradicional": 0.15,    # una tiendita es poco, pero hay una a ~40 m de cada 3B
}
# Factibilidad operativa: 3B crece "como mancha de aceite" desde su red (EDA de Fase 3: 94% de las
# aperturas 2021-2026 cayeron a < 2.5 km de una 3B existente). Fuera del radio el índice decae.
RADIO_OPERATIVO_M = 2500
DECAIMIENTO_FUERA_RED_M = 1000
KDE_BANDWIDTHS_M = [300, 500, 800]  # comparación KDE vs H3 y sensibilidad
MIN_DIST_CANDIDATAS_M = 600  # separación mínima del Top 20 (= distancia mediana entre 3B: 607 m)
TOP_N = 20
ISOCHRONES_MIN = [5, 10]            # minutos caminando
WALK_SPEED_KMH = 4.5                # 10 min = 750 m por la red de calles
# Si no está la red OSM: distancia por calle ≈ línea recta × factor de rodeo (en trayectos cortos
# urbanos la literatura reporta ~1.2-1.4; se usa 1.3).
FACTOR_RODEO = 1.3
