# Reporte de calidad · Silver DENUE

Generado automáticamente por `scripts/03_silver_denue.py`. No editar a mano.

## Resumen
| Indicador | Valor |
| --- | --- |
| Registros DENUE 2021_11 | 474,333 |
| Tiendas de despensa 2021_11 | 41,667 |
| Registros 3B: patrón / excluidos / confirmados (2021_11) | 154 / 5 / 149 |
| Duplicados de cadenas eliminados (2021_11) | 86 |
| Tiendas 3B únicas (2021_11) | 144 |
| Registros DENUE 2026_05 | 462,732 |
| Tiendas de despensa 2026_05 | 42,288 |
| Registros 3B: patrón / excluidos / confirmados (2026_05) | 339 / 3 / 336 |
| Duplicados de cadenas eliminados (2026_05) | 87 |
| Tiendas 3B únicas (2026_05) | 305 |
| Aperturas (umbral 100 m) | 168 |
| Aperturas confirmadas (etiqueta del backtest) | 162 |
| Tiendas 3B de 2021_11 sin equivalente en 2026_05 | 8 |

## Aperturas 3B: sensibilidad al umbral de distancia
| Umbral | Aperturas |
| --- | --- |
| 50 m | 181 |
| 100 m | 168 |
| 200 m | 162 |

La etiqueta del backtest es `apertura_confirmada`: sin 3B de 2021_11 a < 100 m **y** fecha de alta en el DENUE posterior al corte 2021_11.

## Establecimientos por cadena (deduplicados)
| Cadena | Formato | 2021_11 | 2026_05 |
| --- | --- | --- | --- |
| OXXO | Conveniencia | 1,244 | 1,483 |
| 7-Eleven | Conveniencia | 362 | 332 |
| Circle K | Conveniencia | 113 | 193 |
| 3B | Hard discount | 144 | 305 |
| Neto | Hard discount | 149 | 233 |
| Bodega Aurrera | Hard discount | 186 | 189 |
| Chedraui | Supermercado | 54 | 117 |
| Walmart otros | Supermercado | 92 | 88 |
| Supermercado independiente | Supermercado | 85 | 57 |
| Soriana | Supermercado | 56 | 53 |
| La Comer | Supermercado | 27 | 28 |
| Abarrotes | Tradicional | 37,974 | 38,985 |
| Minisúper independiente | Tradicional | 1,181 | 225 |

## Tiendas 3B y aperturas confirmadas por alcaldía (2026_05)
| Alcaldía | Tiendas 3B | Aperturas |
| --- | --- | --- |
| Iztapalapa | 63 | 35 |
| Gustavo A. Madero | 48 | 21 |
| Cuauhtémoc | 35 | 18 |
| Azcapotzalco | 17 | 11 |
| Iztacalco | 15 | 10 |
| Coyoacán | 22 | 10 |
| Álvaro Obregón | 13 | 10 |
| Tláhuac | 21 | 10 |
| Tlalpan | 17 | 9 |
| Benito Juárez | 10 | 8 |
| Miguel Hidalgo | 19 | 8 |
| Xochimilco | 11 | 6 |
| Venustiano Carranza | 11 | 5 |
| Cuajimalpa de Morelos | 3 | 1 |
