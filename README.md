# 3B Geo-Expansion · Inteligencia geoespacial para Tiendas 3B

Producto de datos que recomienda **dónde abrir las próximas tiendas 3B en la Ciudad de México** y **dónde activar campañas drive-to-store** alrededor de las tiendas existentes, usando solo datos públicos (INEGI, CONEVAL, Datos CDMX, OpenStreetMap). Inspirado en plataformas de IA geoespacial como [Tesela](https://tesela.io/es/).

> Proyecto final · Mercadotecnia para Ciencia de Datos · Lic. en Ciencia de Datos, IIMAS UNAM

## Problema de negocio

Tiendas 3B (BBB Foods, NYSE: TBBB) cerró el 2T26 con 3,624 tiendas y planea hasta 630 aperturas en 2026. Su decisión más cara y frecuente es **dónde abrir la siguiente tienda**: una mala ubicación inmoviliza renta e inventario y canibaliza ventas de otra 3B cercana. Ver [`docs/business_case.md`](docs/business_case.md).

## Preguntas que responde

1. **Expansión:** ¿qué zonas de la CDMX tienen alta demanda de su cliente objetivo y baja cobertura actual? → Top 20 de zonas en GeoJSON.
2. **Activación:** ¿alrededor de qué tiendas hay demanda no capturada para campañas de geofencing, volanteo o folleto? → zonas por tienda.
3. **Medición:** ¿cómo probar que una campaña aumentó visitas? → diseño de geo-experimento.

**Validación:** backtest con DENUE histórico. En la CDMX hay 144 tiendas 3B únicas en 11/2021 y 305 en 05/2026: **162 aperturas confirmadas**. El índice se construye solo con datos de 2021 y se evalúa contra esas aperturas reales (ver [`docs/calidad_silver_denue.md`](docs/calidad_silver_denue.md)).

## Metodología

CRISP-DM para el proceso y arquitectura medallion para los datos:

```
data/_downloads  →  data/bronze  →  data/silver  →  data/gold  →  outputs/ + app
 (originales)       (extraído,      (limpio,        (H3, índice,    (Top 20 GeoJSON,
                     sin cambios)    unido,          backtest)       mapa Streamlit)
                                     GeoParquet)
```

- **CRS:** almacenamiento en EPSG:4326; todo cálculo métrico en EPSG:6369 (UTM 14N). El Marco Geoestadístico viene en EPSG:6372.
- **Métodos:** KDE, hexágonos H3, modelo de Huff, Voronoi vs isócronas a pie (OSMnx), LISA / Getis-Ord Gi*, Maximal Coverage Location Problem, geo-experimento con diferencias en diferencias.

## Estructura del repositorio

```
Proyecto/
├── data/
│   ├── _downloads/        # descargas originales (no se tocan, no se suben)
│   ├── bronze/            # datos crudos extraídos + MANIFEST.md
│   ├── silver/            # datos limpios y unidos (GeoParquet)
│   └── gold/              # features, índice H3, resultados de modelo
├── docs/                  # caso de negocio, fuentes de datos, decisiones
├── notebooks/             # exploración y presentación
├── src/tesela3b/
│   ├── config.py          # rutas, CRS, parámetros, patrones de cadenas
│   ├── ingest/            # Bronze
│   ├── silver/            # limpieza y uniones
│   ├── gold/              # demanda, índice, influencia, backtest, geoexperimento
│   └── app/               # app Streamlit
├── scripts/               # pasos ejecutables del pipeline
├── tests/                 # pruebas automáticas
├── reports/figures/       # figuras para el reporte y el pitch
├── outputs/               # entregables (Top 20 GeoJSON, tablas)
└── references/            # apuntes y documentación de apoyo
```

## Cómo reproducir

```bash
# 1. Entorno (Python 3.10+)
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e .

# 2. Descargar los datos a data/_downloads/ (ver data/bronze/MANIFEST.md)

# 3. Capa Bronze
python scripts/01_extraer_bronze.py
python scripts/02_verificar_bronze.py

# 4. Capa Silver
python scripts/03_silver_denue.py          # tiendas por cadena, 3B y aperturas
python scripts/04_precision_validacion.py  # tras validar a mano docs/validacion/muestra_validacion_3b.csv

# 4. Pruebas
pytest
```

## Estado

| Fase | Entregable | Estado |
| --- | --- | --- |
| 0 | Alcance aprobado, caso de negocio, Bronze | Completa |
| 1 | Exploración de datos (EDA): 143 → 305 tiendas 3B, 169 aperturas para el backtest | Completa |
| 2.1 | Silver DENUE: 10 cadenas, 3B 144 → 305, 162 aperturas confirmadas, 34 tests | Completa (falta validación manual) |
| 2.2 | Silver censo + Marco Geo + CONEVAL | Siguiente |
| 3 | Índice de expansión H3 + Top 20 + comparación KDE vs H3 | Pendiente |
| 4 | Backtest + comparación Voronoi vs Huff vs isócronas | Pendiente |
| 5 | App Streamlit publicada | Pendiente |
| 6 | Presentación ejecutiva de marketing para 3B | Pendiente |
| Extra 1 | Capa generativa dentro de la app | Opcional |
| Extra 2 | Drive-to-store completo + geo-experimento | Opcional |

## Limitaciones

Sin ventas por tienda (la demanda se aproxima con hogares y perfil socioeconómico); Censo de 2020; el DENUE puede no registrar todas las tiendas. Todo supuesto se documenta en [`docs/decisiones.md`](docs/decisiones.md).
