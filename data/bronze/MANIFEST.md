# Manifiesto de datos (capa Bronze)

Los archivos originales viven en `data/_downloads/` y se extraen con `python scripts/01_extraer_bronze.py`. Ningún archivo de Bronze se modifica a mano.

| Fuente | Archivo original | Destino en Bronze | Edición / corte | Descargado | Enlace |
| --- | --- | --- | --- | --- | --- |
| DENUE CDMX (INEGI) | `denue_09_csv.zip` | `denue/2026_05/` | 05/2026 | 2026-11-03 | https://www.inegi.org.mx/app/descarga/?ti=6 |
| DENUE CDMX (INEGI) | `denue_09_1121_csv.zip` | `denue/2021_11/` | 11/2021 | 2026-11-03 | https://www.inegi.org.mx/app/descarga/?ti=6 |
| Censo 2020 por AGEB y manzana, CDMX | `resageburb_09csv20.zip` | `censo2020/` | CPV 2020 | 2026-11-03 | https://www.inegi.org.mx/app/scitel/Default?ev=10 |
| Marco Geoestadístico CPV 2020 (nacional) | `889463807469_s.zip` | `marco_geo/` (solo entidad 09; capas a, mun, ent, m, l + catálogos) | CPV 2020 | 2026-11-04 | https://www.inegi.org.mx/temas/mg/#descargas |
| Grado de Rezago Social AGEB urbana (CONEVAL) | `GRS_AGEB_urbana_2020.zip` | `coneval/` | 2020 | 2026-11-03 | https://www.coneval.org.mx/Medicion/IRS/Paginas/Rezago_social_AGEB_2020.aspx |
| Afluencia STC Metro desglosada | `afluenciastc_desglosado_09_2026.csv` | `movilidad/` | 2021-01 a 2026-09 | 2026-11-03 | https://datos.cdmx.gob.mx |
| Red vial peatonal OSM | (se descarga con OSMnx) | `osm/` | — | Semana 4 | https://www.openstreetmap.org |

## Pendientes

- [ ] Ubicación de estaciones del Metro (capa de puntos): https://sieg.cdmx.gob.mx/layers/geonode%3Astc_metro_estaciones
- [ ] (Opcional) DENUE del Estado de México (`denue_15`) si se amplía a la Zona Metropolitana.

## Notas de lectura

- DENUE: `encoding="latin-1"`, leer todo como texto (`dtype=str`).
- Censo: `encoding="utf-8-sig"`; valores confidenciales vienen como `*`.
- Afluencia: columnas `fecha, mes, anio, linea, estacion, tipo_pago, afluencia`; viene en UTF-8.
- Marco Geoestadístico: shapefiles en EPSG:6372; llave de unión `CVEGEO`.
