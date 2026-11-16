# Reporte de calidad · Silver demanda

Generado automáticamente por `scripts/05_silver_demanda.py`. No editar a mano.

## Resumen y conciliación
| Indicador | Valor |
| --- | --- |
| Población total CDMX (Censo 2020) | 9,209,944 |
| Población en AGEB urbanas | 9,145,632 (99.3% del total) |
| AGEB urbanas en el censo / con polígono | 2,433 / 2,431 |
| Población en AGEB sin polígono | 7,108 |
| AGEB con datos de CONEVAL | 99.1% |
| Hogares en AGEB | 2,737,749 |
| Manzanas habitadas con punto | 63,076 |
| Manzanas habitadas sin polígono (población) | 7 (435 personas) |
| Hogares en manzanas (suma) | 2,743,005 |
| Manzanas con hogares estimados (dato confidencial) | 1,658 (2.6%) |
| Diferencia hogares manzanas vs AGEB | +0.19% |

## Perfil por AGEB (percentiles)
| Variable | P10 | Mediana | P90 | Nulos |
| --- | --- | --- | --- | --- |
| hogares_km2 | 1,216.2 | 4,913.1 | 8,641.7 | 11 |
| personas_por_hogar | 2.6 | 3.4 | 4.0 | 30 |
| escolaridad_promedio | 9.6 | 11.4 | 14.3 | 10 |
| pct_sin_auto | 25.2 | 56.4 | 70.1 | 39 |
| pct_sin_computadora | 14.4 | 41.3 | 61.8 | 31 |
| pct_sin_internet | 7.7 | 24.2 | 39.6 | 31 |
| pct_hacinamiento | 0.0 | 2.2 | 7.9 | 31 |
| pct_sin_derechohabiencia | 18.4 | 26.3 | 35.3 | 31 |

## Grado de rezago social (CONEVAL)
| Grado | AGEB | % |
| --- | --- | --- |
| Muy bajo | 948 | 39.0% |
| Bajo | 1,234 | 50.8% |
| Medio | 200 | 8.2% |
| Alto | 22 | 0.9% |
| Muy alto | 6 | 0.2% |

El grado casi no varía dentro de la CDMX; el modelo usa los porcentajes continuos.

## Por alcaldía
| Alcaldía | AGEB | Hogares | Mediana % viviendas sin auto |
| --- | --- | --- | --- |
| Iztapalapa | 458 | 504,365 | 63% |
| Gustavo A. Madero | 305 | 340,153 | 59% |
| Álvaro Obregón | 199 | 219,322 | 55% |
| Tlalpan | 207 | 197,448 | 47% |
| Cuauhtémoc | 153 | 196,466 | 61% |
| Coyoacán | 156 | 191,517 | 35% |
| Benito Juárez | 102 | 176,053 | 34% |
| Miguel Hidalgo | 130 | 146,752 | 40% |
| Venustiano Carranza | 151 | 135,767 | 58% |
| Azcapotzalco | 103 | 134,167 | 53% |
| Iztacalco | 110 | 117,720 | 57% |
| Xochimilco | 122 | 113,758 | 59% |
| Tláhuac | 110 | 104,356 | 60% |
| La Magdalena Contreras | 52 | 67,755 | 53% |
| Cuajimalpa de Morelos | 31 | 59,151 | 51% |
| Milpa Alta | 42 | 32,999 | 60% |
