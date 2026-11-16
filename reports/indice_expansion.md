# Índice de expansión 3B · Top 20 (corte 2026_05)

Generado automáticamente por `scripts/06_gold_indice.py`. Versión v1: los parámetros se calibran en la Fase 4 (backtest).

**Lectura del índice:** hogares objetivo (hogares sin auto) que una tienda 3B nueva en ese hexágono
ganaría para la cadena, ya descontada la canibalización de sus propias tiendas, ponderado por su factibilidad
operativa (cercanía a la red actual).

## Top 20 zonas recomendadas
| # | Alcaldía | Índice | Hogares captados | Canibalización | Hogares en el hexágono | % sin auto | 3B más cercana | H3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Iztapalapa | 811 | 835 | 2.9% | 1,206 | 75% | 1,314 m | `8949958ea2fffff` |
| 2 | Iztapalapa | 683 | 706 | 3.3% | 193 | 78% | 1,560 m | `8949958cc83ffff` |
| 3 | Iztapalapa | 667 | 681 | 2.1% | 558 | 81% | 1,122 m | `8949958ea67ffff` |
| 4 | Iztapalapa | 640 | 645 | 0.8% | 1,060 | 67% | 1,303 m | `8949958ea3bffff` |
| 5 | Gustavo A. Madero | 623 | 637 | 2.2% | 948 | 74% | 1,288 m | `894995aa2bbffff` |
| 6 | Iztapalapa | 612 | 655 | 6.5% | 695 | 62% | 940 m | `8949958eb4bffff` |
| 7 | Coyoacán | 605 | 611 | 1.0% | 682 | 48% | 1,710 m | `894995853b3ffff` |
| 8 | Gustavo A. Madero | 602 | 602 | 0.0% | 635 | 47% | 2,209 m | `894995b963bffff` |
| 9 | Tlalpan | 574 | 592 | 3.2% | 1,179 | 58% | 1,362 m | `894995845d7ffff` |
| 10 | La Magdalena Contreras | 573 | 573 | 0.0% | 555 | 70% | 2,115 m | `894995b34d3ffff` |
| 11 | Iztapalapa | 553 | 570 | 3.1% | 906 | 70% | 1,242 m | `894995852abffff` |
| 12 | Gustavo A. Madero | 532 | 534 | 0.3% | 725 | 79% | 1,896 m | `894995aa207ffff` |
| 13 | Álvaro Obregón | 532 | 533 | 0.2% | 1,226 | 54% | 1,744 m | `89499584b0fffff` |
| 14 | Gustavo A. Madero | 530 | 539 | 1.8% | 487 | 71% | 1,341 m | `894995aa213ffff` |
| 15 | La Magdalena Contreras | 519 | 519 | 0.0% | 521 | 65% | 2,185 m | `894995869afffff` |
| 16 | Coyoacán | 510 | 513 | 0.5% | 1,390 | 50% | 1,561 m | `89499585397ffff` |
| 17 | Iztapalapa | 495 | 530 | 6.7% | 1,113 | 64% | 999 m | `8949958528fffff` |
| 18 | Iztapalapa | 493 | 554 | 10.9% | 793 | 81% | 731 m | `8949958eb53ffff` |
| 19 | La Magdalena Contreras | 489 | 492 | 0.6% | 202 | 67% | 1,603 m | `894995b34c7ffff` |
| 20 | Iztapalapa | 488 | 518 | 5.7% | 807 | 50% | 1,292 m | `8949958ccd7ffff` |

| Alcaldía | Zonas en el Top 20 |
| --- | --- |
| Iztapalapa | 9 |
| Gustavo A. Madero | 4 |
| La Magdalena Contreras | 3 |
| Coyoacán | 2 |
| Tlalpan | 1 |
| Álvaro Obregón | 1 |

## Cobertura
| Indicador | 2021_11 | 2026_05 |
| --- | --- | --- |
| Hexágonos con demanda | 6,080 | 6,080 |
| Hexágonos con al menos una 3B | 142 | 295 |
| Cuota 3B promedio de la demanda objetivo | 2.6% | 4.6% |
| Hexágonos dentro del radio operativo | 80% | 89% |

## KDE clásico vs índice H3 (correlación de rangos de Spearman)
| Superficie | ρ con el índice |
| --- | --- |
| KDE 300 m | 0.66 |
| KDE 500 m | 0.65 |
| KDE 800 m | 0.61 |

Una ρ alta indica que ambos "ven" la misma demanda; la diferencia es lo que el índice agrega: competencia (Huff),
canibalización y factibilidad operativa.

## Parámetros
| Parámetro | Valor |
| --- | --- |
| h3_res | 9 |
| demanda_objetivo | hogares_sin_auto |
| beta_m | 350 |
| radio_max_m | 1000 |
| dist_min_m | 120 |
| opcion_externa | 1.0 |
| lambda_nido | 0.5 |
| atractivo | {'3B': 1.0, 'Hard discount': 1.0, 'Supermercado': 2.0, 'Conveniencia': 0.4, 'Tradicional': 0.15} |
| radio_operativo_m | 2500 |
| decaimiento_fuera_red_m | 1000 |
| min_dist_top_m | 600 |
| top_n | 20 |
