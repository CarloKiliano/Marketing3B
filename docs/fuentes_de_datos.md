# Fuentes de datos: para qué sirve cada una y cómo se conectan

| Capa | Fuente | Rol en el modelo | Llave de unión |
| --- | --- | --- | --- |
| Oferta | DENUE 05/2026 | Tiendas 3B actuales y competencia (Bodega Aurrera, Neto, OXXO, abarrotes) | Coordenadas → H3 |
| Oferta histórica | DENUE 11/2021 | Mapa 3B del pasado para el backtest | Coordenadas → H3; `clee` |
| Demanda | Censo 2020 por AGEB | Hogares, estructura de edad, bienes (proxy de ingreso) | `CVEGEO` |
| Geometría | Marco Geoestadístico 2020 | Polígonos de AGEB y alcaldías para ubicar el censo | `CVEGEO` |
| Perfil | CONEVAL GRS AGEB 2020 | Grado de rezago social para ponderar al cliente objetivo | `CVEGEO` |
| Flujo | Afluencia Metro por estación | Proxy de tráfico peatonal y horarios de activación | Nombre de estación → puntos |
| Red vial | OpenStreetMap (OSMnx) | Isócronas a pie de 5 y 10 min | Grafo de calles |

## Cómo se conecta todo
1. Censo + Marco Geo + CONEVAL → **demanda por AGEB** (polígonos).
2. DENUE → **oferta** en puntos.
3. Metro → **flujo** en puntos.
4. Todo se proyecta a una rejilla **H3 res 9** → índice = demanda objetivo − cobertura actual − canibalización.
5. OSM convierte distancias en línea recta en **tiempo real caminando**.

## Hallazgos del EDA (Fase 1, `notebooks/01_eda_bronze.ipynb`)
| Indicador | Valor |
| --- | --- |
| Tiendas 3B únicas en CDMX (deduplicadas) | 143 (nov 2021) → 305 (may 2026) |
| Aperturas 2021→2026 (etiqueta del backtest) | 169 (36 Iztapalapa, 22 GAM, 18 Cuauhtémoc) |
| Bodega Aurrera / OXXO / Circle K (2026) | 200 / 1,494 / 201 |
| Tiendas de abarrotes (461110, 2026) | 38,996 |
| AGEB urbanas con datos del censo | 2,433 (9.15 M habitantes, 2.74 M hogares) |
| Unión censo ↔ polígonos / ↔ CONEVAL | 99.9% / 99.8% de la población |
| Mediana hogares/km² en AGEB con 3B vs sin 3B | 5,486 vs 4,862 |
| Mediana % viviendas sin auto con 3B vs sin 3B | 60% vs 56% |
| Metro | 12 líneas, 166 estaciones, ene 2021 – sep 2026 |
