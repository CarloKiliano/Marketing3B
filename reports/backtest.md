# Backtest 2021 → 2026 · ¿El modelo anticipa dónde abre 3B?

Generado automáticamente por `scripts/08_backtest.py`. AUC de 0.5 = azar.

**Diseño.** Todos los scores se calculan solo con el DENUE de noviembre de 2021 (y el Censo 2020). La etiqueta son las
162 aperturas 3B confirmadas hasta mayo de 2026. Universo: 5,938 hexágonos con vivienda y sin 3B en 2021
(153 con apertura; 7 aperturas cayeron en un hexágono que ya tenía 3B y
2 en hexágonos sin vivienda). Intervalos al 95% con bootstrap por bloques espaciales
(H3 res 6, ~36 km²); validación cruzada con 5 grupos de bloques.

## 1. Comparación de métodos
| Método | AUC (IC 95%) | AUC promedio por bloque | Captura en el 10% superior | Lift@10% | Captura en el 20% superior | AUC vecindad (±1 hexágono) |
| --- | --- | --- | --- | --- | --- | --- |
| Modelo de preferencia revelada | 0.741 (0.70–0.79) | 0.731 | 26% | 2.6× | 44% | 0.752 |
| Valor esperado (preferencia × índice) | 0.718 (0.67–0.77) | 0.706 | 21% | 2.1× | 42% | 0.732 |
| Isócrona 10 min (cobertura) | 0.703 (0.65–0.75) | 0.686 | 22% | 2.2× | 41% | 0.692 |
| KDE 500 m (clásico) | 0.694 (0.64–0.75) | 0.671 | 17% | 1.7× | 41% | 0.715 |
| Huff simple (λ = 1) | 0.678 (0.63–0.73) | 0.659 | 20% | 2.0× | 36% | 0.699 |
| Hogares sin auto en el hexágono | 0.675 (0.63–0.72) | 0.654 | 16% | 1.6× | 33% | 0.690 |
| Hogares en el hexágono | 0.663 (0.62–0.71) | 0.643 | 16% | 1.6× | 32% | 0.684 |
| Índice H3 Fase 3 (Huff anidado + red) | 0.623 (0.56–0.68) | 0.604 | 12% | 1.2× | 29% | 0.639 |
| Voronoi (tienda más cercana) | 0.568 (0.50–0.62) | 0.548 | 14% | 1.4× | 25% | 0.575 |

*AUC = probabilidad de que un hexágono donde 3B abrió quede arriba de uno donde no abrió (0.5 = azar).
Captura@10% = % de aperturas que caen en el 10% de hexágonos mejor calificados; lift = cuántas veces mejor que el azar.*
El modelo de preferencia revelada se evalúa con predicciones fuera de bloque (nunca vio la zona que califica).
Isócronas calculadas con: red peatonal OSM.

**¿Las diferencias son reales?** Bootstrap pareado por bloques (mismas zonas re-muestreadas para ambos métodos):
| Comparación | Diferencia de AUC | IC 95% | % de re-muestreos en que gana el primero |
| --- | --- | --- | --- |
| Modelo de preferencia revelada vs KDE 500 m (clásico) | +0.047 | +0.014 a +0.083 | 100% |
| Valor esperado (preferencia × índice) vs KDE 500 m (clásico) | +0.025 | -0.008 a +0.052 | 95% |
| Huff simple (λ = 1) vs Voronoi (tienda más cercana) | +0.110 | +0.058 a +0.180 | 100% |
| Isócrona 10 min (cobertura) vs Voronoi (tienda más cercana) | +0.135 | +0.092 a +0.185 | 100% |

## 2. ¿Qué hace que 3B abra en un lugar? (modelo de preferencia revelada)
Regresión logística con variables estandarizadas: el coeficiente es el efecto de subir una desviación estándar.
| Variable | Coeficiente | Rango entre los 5 folds |
| --- | --- | --- |
| Comercio de barrio a ≤ 500 m (tienditas + OXXO) | +1.01 | +0.91 a +1.12 |
| Escolaridad promedio (años) | +0.85 | +0.71 a +0.99 |
| % hogares sin auto | +0.44 | +0.28 a +0.61 |
| Neto/Bodega Aurrera a ≤ 500 m | +0.24 | +0.21 a +0.27 |
| Índice Huff (hogares nuevos, Fase 3) | -0.03 | -0.05 a -0.00 |
| Cuota 3B actual (exposición a canibalización) | -0.13 | -0.19 a -0.05 |
| Fuera del radio operativo (> 2.5 km de una 3B) | -0.25 | -0.32 a -0.19 |

## 3. Top 20 que se habría recomendado en noviembre de 2021
Acierto = hubo una apertura 3B confirmada a ≤ 600 m del centro de la zona. Azar = la misma tasa
para un hexágono elegible cualquiera. Con solo 20 zonas los intervalos son anchos: la comparación fina entre métodos
se hace con el AUC sobre los ~6 mil hexágonos (sección 1); esta tabla es la lectura de negocio.
| Método | Aciertos | Tasa al azar | Lift | Distancia mediana a la apertura más cercana |
| --- | --- | --- | --- | --- |
| Valor esperado (recomendación) | 10 de 20 (50%; IC 30%–70%) | 20% | 2.5× | 583 m |
| Modelo de preferencia revelada | 11 de 20 (55%; IC 34%–74%) | 20% | 2.7× | 540 m |
| Índice H3 Fase 3 | 8 de 20 (40%; IC 22%–61%) | 20% | 2.0× | 838 m |
| KDE 500 m | 12 de 20 (60%; IC 39%–78%) | 20% | 3.0× | 556 m |

## 4. Calibración del Huff (λ, β, radio de red)
Mejor AUC fuera de bloque: **0.655**. Combinación elegida en cada fold: (1.0, 200, 1500), (1.0, 200, 2000), (1.0, 200, 2000), (1.0, 350, 2000), (1.0, 200, 2000).
| # | λ | β (m) | Radio de red | AUC |
| --- | --- | --- | --- | --- |
| 1 | 1.0 | 200 | 2000 | 0.685 |
| 2 | 1.0 | 350 | 2000 | 0.684 |
| 3 | 1.0 | 200 | 1500 | 0.683 |
| 4 | 1.0 | 200 | 2500 | 0.683 |
| 5 | 1.0 | 200 | 3000 | 0.682 |
| 6 | 1.0 | 200 | sin límite | 0.682 |
| 7 | 1.0 | 500 | 2000 | 0.681 |
| 8 | 1.0 | 350 | 1500 | 0.680 |

Lectura: λ = 1 (sin nido) predice mejor dónde abre 3B porque 3B **no evita** la canibalización: densifica. Eso dice cómo
decide 3B, no cuántas ventas pierde una tienda vecina; sin datos de ventas, λ = 0.5 se conserva como estimación
conservadora de hogares nuevos y canibalización (supuesto a recalibrar con datos internos).

## 5. Cobertura a pie (isócrona de 10 min)
Hogares sin auto con una 3B a ≤ 10 min caminando: **24.4%** en 2021 → **41.4%** en 2026.

## 6. Recomendación final · Top 20 2026
Regla de decisión: **valor esperado = P(apertura) × índice H3**: los hogares nuevos que aporta la zona según el Huff,
ponderados por la probabilidad de que sea una zona "tipo 3B" según el modelo de preferencia. El modelo de preferencia solo
replica dónde abre 3B (y concentra la lista en el centro); el índice solo mide mercado; el producto equilibra ambos.
En la app, la prioridad de cada hexágono es el percentil de este valor en la CDMX.
| # | Alcaldía | Valor esperado | P(apertura) | Hogares nuevos (índice) | Canibalización | Comercio a 500 m | 3B más cercana | H3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Venustiano Carranza | 45 | 24.4% | 184 | 13% | 307 | 251 m | `894995bb177ffff` |
| 2 | Cuauhtémoc | 43 | 26.7% | 163 | 25% | 76 | 774 m | `894995b8403ffff` |
| 3 | Álvaro Obregón | 43 | 9.1% | 473 | 3% | 82 | 1,173 m | `89499584b2bffff` |
| 4 | Cuauhtémoc | 42 | 14.1% | 294 | 18% | 154 | 363 m | `894995b8633ffff` |
| 5 | Cuauhtémoc | 35 | 14.4% | 244 | 25% | 113 | 248 m | `894995ba273ffff` |
| 6 | Iztapalapa | 34 | 9.5% | 362 | 14% | 159 | 638 m | `8949958c0d3ffff` |
| 7 | Iztapalapa | 34 | 4.2% | 811 | 3% | 104 | 1,314 m | `8949958ea2fffff` |
| 8 | Coyoacán | 33 | 5.7% | 581 | 4% | 97 | 1,341 m | `894995853b7ffff` |
| 9 | Iztapalapa | 33 | 6.0% | 547 | 3% | 118 | 1,273 m | `894995852bbffff` |
| 10 | Tláhuac | 32 | 7.5% | 432 | 18% | 90 | 839 m | `8949958e1c3ffff` |
| 11 | Venustiano Carranza | 31 | 10.3% | 303 | 18% | 119 | 190 m | `894995b8603ffff` |
| 12 | Venustiano Carranza | 31 | 12.0% | 258 | 16% | 95 | 498 m | `894995b86c7ffff` |
| 13 | Iztapalapa | 30 | 6.8% | 444 | 8% | 113 | 1,015 m | `894995bb417ffff` |
| 14 | Venustiano Carranza | 30 | 11.0% | 272 | 14% | 96 | 666 m | `894995bb56fffff` |
| 15 | Cuauhtémoc | 29 | 14.4% | 205 | 25% | 57 | 482 m | `894995b85c7ffff` |
| 16 | Álvaro Obregón | 29 | 8.4% | 347 | 13% | 108 | 1,062 m | `894995b1677ffff` |
| 17 | Coyoacán | 29 | 9.9% | 292 | 16% | 100 | 605 m | `89499585d87ffff` |
| 18 | La Magdalena Contreras | 29 | 9.4% | 307 | 0% | 88 | 1,884 m | `894995b361bffff` |
| 19 | Azcapotzalco | 29 | 13.8% | 210 | 12% | 80 | 457 m | `894995b8cabffff` |
| 20 | Cuauhtémoc | 29 | 12.1% | 238 | 16% | 105 | 377 m | `894995b868fffff` |

Por alcaldía: Cuauhtémoc 5, Venustiano Carranza 4, Iztapalapa 4, Álvaro Obregón 2, Coyoacán 2, Tláhuac 1, La Magdalena Contreras 1, Azcapotzalco 1.
