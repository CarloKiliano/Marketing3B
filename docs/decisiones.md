# Bitácora de decisiones

Formato: fecha · decisión · motivo · alternativa descartada.

| Fecha | Decisión | Motivo | Alternativa descartada |
| --- | --- | --- | --- |
| 2026-11-01 | Proyecto 3 (geoespacial) para Tiendas 3B | Datos públicos mexicanos completos; 3B en expansión acelerada | BI Generativo, DCO |
| 2026-11-01 | Alcance: CDMX (16 alcaldías) | Cabe en el semestre; censo y DENUE completos | Zona Metropolitana (queda como extensión) |
| 2026-11-01 | Capa generativa al final | Prioridad a un núcleo limpio y validado | Construirla desde el inicio |
| 2026-11-03 | DENUE 05/2026 (actual) y 11/2021 (backtest) | Ventana de 4.5 años con ~185 aperturas 3B observables | Una sola versión sin validación |
| 2026-11-04 | Marco Geo CPV 2020, solo capas a/mun/ent/m/l | Claves coinciden con el censo 2020; evita 335 MB innecesarios | Ediciones 2021–2025 |
| 2026-11-04 | CRS: 4326 almacenamiento, 6369 cálculo | Distancias en metros correctas para la CDMX | Medir en grados |
| 2026-11-04 | Filtro SCIAN 462111/462112/461110 para tiendas | Excluir CEDIS y oficinas con razón social de 3B | Solo filtro por nombre |
| 2026-11-15 | Alcance confirmado por el profesor: solo CDMX | Profundidad sobre cobertura | Zona Metropolitana |
| 2026-11-15 | Se presenta como propuesta real a 3B, con aviso de ejercicio académico | Sin datos internos; el modelo se recalibraría con ventas reales | Presentarlo como caso ficticio |
| 2026-11-15 | Comparación metodológica explícita: KDE vs H3 (demanda) y Voronoi vs Huff vs isócronas (área de influencia), evaluadas con el backtest | El profesor pide entender la diferencia; el backtest decide con datos cuál funciona mejor | Elegir un método sin compararlo |
| 2026-11-15 | El backtest es la pieza central de evidencia | Es lo que convierte el índice en un modelo validado | Validación cualitativa |
| 2026-11-15 | Entrega visual: app funcionando + presentación ejecutiva de marketing | Formato pedido por el profesor | Reporte técnico extenso |
| 2026-11-15 | Drive-to-store completo y geo-experimento pasan a extra; se mantiene una versión ligera de zonas de activación derivada del índice | Bajo costo, conserva el ángulo de marketing | Fase completa de isócronas por tienda |
| 2026-11-15 | Capa generativa dentro de la app, al final del plan | Alto valor visual, riesgo de tiempo | Construirla antes del núcleo |
| 2026-11-15 | EDA (Fase 1): deduplicar tiendas a < 50 m conservando la fecha de alta más antigua | Hay registros duplicados de la misma tienda (5 en 2021, 30 en 2026) | Contar registros como tiendas |
| 2026-11-15 | Etiqueta del backtest: tienda 3B de 2026 sin 3B de 2021 a < 100 m = apertura (169); sensibilidad 50 m = 181, 200 m = 163 | Umbral robusto a errores de geocodificación | Emparejar solo por `clee` (cambia entre versiones) |
| 2026-11-15 | Excluir registros 3B que no son tienda (CEDIS, oficinas) u otra marca (Circulo K, Super Yema) | Son ruido para el modelo | Incluirlos |
| 2026-11-15 | Bodega Aurrera se identifica por razón social Walmart + prefijo del nombre (BODEGA, BA, BAE, BOA) | Casi no aparece por su nombre comercial | Buscar solo "AURRERA" |
| 2026-11-15 | Competencia se busca en todos los sectores SCIAN, no solo el 46 | En 2021 INEGI clasificó a Neto como mayoreo (431110) | Filtrar solo sector 46 |
| 2026-11-15 | Perfil socioeconómico con indicadores continuos (% sin auto, sin computadora), no el grado de rezago | 90% de las AGEB de la CDMX tienen rezago Bajo o Muy bajo: el grado casi no discrimina | Grado de rezago categórico |
| 2026-11-15 | Metro: normalizar texto (doble codificación + acentos) y usar promedios 2023+ | El archivo mezcla "Línea"/"Linea"; 2021–2022 afectados por la pandemia | Usar la serie completa |
| 2026-11-15 | Silver DENUE (Fase 2.1): Neto se identifica por razón social "Tiendas Super Precio", también en SCIAN 431110 | Es la única marca confiable en ambos cortes (148 → 230 tiendas) | Buscar "NETO" en el nombre |
| 2026-11-15 | Cadenas identificadas: 3B, Neto, Bodega Aurrera, OXXO, 7-Eleven, Circle K, Walmart otros, Soriana, Chedraui, La Comer | Cubren los formatos que compiten por la despensa: hard discount, conveniencia y supermercado | Solo 3B y Bodega Aurrera |
| 2026-11-15 | Deduplicación: 50 m para 3B, 25 m para la competencia | A 25–50 m hay OXXO/7-Eleven reales con direcciones distintas; 3B no tiene tiendas tan cercanas | Un solo umbral de 50 m (borraba tiendas reales) |
| 2026-11-15 | Etiqueta del backtest = `apertura_confirmada` (162): sin 3B de 2021 a < 100 m y fecha de alta ≥ 2021-11 | Descarta 6 tiendas antiguas que el DENUE 2021 no registró | `apertura` geográfica sola (168) |
| 2026-11-15 | Abarrotes + minisúper independiente se modelan juntos como "comercio tradicional" | 534 minisúpers de 2021 aparecen en el mismo punto como abarrotes en 2026 (reclasificación INEGI) | Tratarlos como capas separadas |
| 2026-11-15 | Contratos de datos con pandera en cada corrida de Silver | Un dato roto falla el pipeline en lugar de contaminar el modelo | Validar solo en tests |
| 2026-11-15 | Validación manual de 50 tiendas 3B: 44 confirmadas en Google Maps = 88% (IC 95% Wilson 76–94%) | Los 6 "NO" son registros llamados "TIENDAS TRES B" en el DENUE (la regla de nombre es correcta); 5 de 6 tienen alta ≥ 2023, probablemente posteriores a la imagen de Street View | Reportar 100% por nombre sin verificar ubicación |
| 2026-11-15 | El ruido de la etiqueta (~12%) se trata en el backtest con umbral de 100 m y análisis de sensibilidad | Un error de ubicación de decenas de metros no cambia el hexágono vecino; una tienda no visible cuenta como ruido aleatorio | Descartar las aperturas recientes |
| 2026-11-15 | Demanda dasimétrica (Fase 2.2): hogares por MANZANA, perfil socioeconómico por AGEB | El hexágono H3 res 9 (~0.1 km²) es menor que una AGEB típica (~0.25 km²); por manzana hasta 8% de los bienes es confidencial | Todo por AGEB (demanda demasiado gruesa) |
| 2026-11-15 | Hogares confidenciales por manzana (2.6%) se estiman con personas por hogar de su AGEB | Conciliación: hogares por manzana difieren +0.19% del total por AGEB | Dejarlos en cero |
| 2026-11-15 | Manzanas guardadas como punto representativo (dentro del polígono) | Una manzana (~0.01 km²) es 10 veces menor que el hexágono; el archivo pesa una fracción | Guardar polígonos de manzana |
| 2026-11-15 | Perfil con indicadores continuos de Censo y CONEVAL: % sin auto, sin computadora, sin internet, hacinamiento, sin derechohabiencia, educación básica incompleta | El grado de rezago es Bajo/Muy bajo en 90% de las AGEB | Usar el grado categórico |
| 2026-11-15 | Fase 3: índice = hogares objetivo NUEVOS para la cadena (captados − canibalización) × factibilidad operativa | Responde la pregunta de negocio en una unidad interpretable (hogares por tienda) | Score abstracto de 0 a 100 sin unidades |
| 2026-11-15 | Demanda objetivo = hogares sin auto (asignados desde manzanas a H3 res 9) | Compran su despensa caminando: es el cliente de proximidad de 3B | Hogares totales (se compara en el backtest) |
| 2026-11-15 | Huff anidado (nested logit, λ = 0.5) con nidos por formato y opción externa α0 = 1 | El Huff simple subestimaba la canibalización (~6% a < 200 m de otra 3B); el anidado da ~29% | Huff simple (λ = 1) |
| 2026-11-15 | β = 350 m (decaimiento) y radio máximo 1 km a pie | Compra de reposición 3–4 veces por semana; la 3B más cercana a otra 3B está a 607 m (mediana) | β de 1 km o más (modelo de auto) |
| 2026-11-15 | Atractivos iniciales: 3B = Neto = Bodega Aurrera = 1; supermercado 2; conveniencia 0.4; tradicional 0.15 | Supuestos explícitos de partida; se prueban en el backtest | Igual atractivo para todos |
| 2026-11-15 | Factor de red: índice × 1 dentro de 2.5 km de una 3B existente, decae fuera (escala 1 km) | 94% de las aperturas 2021→2026 cayeron a < 2.5 km de una 3B existente (crecimiento "en mancha de aceite") | Ignorar la logística |
| 2026-11-15 | Top 20 voraz con separación ≥ 600 m y excluyendo hexágonos que ya tienen una 3B | 600 m = distancia mediana entre 3B; regla de negocio obvia | Optimización MCLP (queda como extensión) |
| 2026-11-15 | Hallazgo: λ = 1 predice mejor las aperturas (AUC preliminar 0.68) que λ = 0.5 (0.63) | 3B acepta canibalización para densificar zonas; se resolverá con validación cruzada espacial en la Fase 4, no ajustando a ojo | Elegir λ mirando el AUC (fuga de información) |
| 2026-11-15 | El GeoJSON del Top 20 se versiona en GitHub | Es el entregable del producto (17 KB) | Ignorar todos los outputs |
| 2026-11-15 | Fase 4: etiqueta = hexágono con ≥ 1 apertura 3B confirmada (2021-11 → 2026-05); universo = hexágonos con vivienda y sin 3B en 2021 | Solo se evalúa donde realmente se podía abrir; 153 de 162 aperturas caen en el universo (7 en hexágonos que ya tenían 3B, 2 sin vivienda) y se reportan | Incluir hexágonos con 3B (inflaría el AUC) |
| 2026-11-15 | Incertidumbre con bootstrap por bloques espaciales (H3 res 6, ~36 km²) y validación cruzada con 5 grupos de bloques equilibrados por aperturas | Las aperturas vecinas no son independientes; un CV aleatorio sobreestimaría el desempeño | Bootstrap / CV por hexágono |
| 2026-11-15 | Comparar Voronoi, isócronas y Huff con el MISMO score: hogares objetivo nuevos que gana la cadena | Permite comparar los tres paradigmas de territorio en el backtest con la misma métrica | Comparación solo visual |
| 2026-11-15 | Isócronas de 10 min (750 m a 4.5 km/h) sobre la red peatonal de OSM (scripts/07); respaldo: línea recta × 1.3 | La red real mejora el AUC de 0.67 (línea recta) a 0.70: el territorio se dibuja con calles | Solo línea recta |
| 2026-11-15 | Huff calibrado por CV espacial: λ = 1, β = 200 m, red 2 km gana en los 5 folds (AUC fuera de bloque 0.655) | 3B NO evita la canibalización: densifica. Sin datos de ventas no se calibra la canibalización real | Cambiar λ a 1 para valuar (se perdería la canibalización realista) |
| 2026-11-15 | Se conserva λ = 0.5 para VALUAR (hogares nuevos y canibalización) y se usa un modelo de preferencia revelada para PREDECIR | Separar "cuánto vale la zona" (supuesto explícito) de "dónde abre 3B" (aprendido de los datos) | Un solo score |
| 2026-11-15 | Modelo de preferencia revelada: regresión logística L2 (C = 0.5) con 7 variables interpretables (índice Huff, cuota 3B, comercio de barrio a 500 m, Neto/BA a 500 m, fuera de red, % sin auto, escolaridad) | AUC fuera de bloque 0.74 vs 0.69 del KDE (+0.047, IC 95% +0.014 a +0.083); coeficientes estables entre folds y explicables a negocio | Gradient boosting (AUC 0.70, menos interpretable); términos cuadráticos (+0.001, no compensa) |
| 2026-11-15 | Regla de decisión final: valor esperado = P(apertura) × índice H3 (hogares nuevos) | El modelo solo replicaba a 3B y concentraba 12 de 20 zonas en Cuauhtémoc; el producto conserva AUC 0.72 y equilibra centro comercial con zonas de gran mercado | Ranking solo por P(apertura) o solo por el índice |
| 2026-11-15 | La recomendación final (outputs/top20_zonas_3b.geojson) la genera scripts/08; el Top 20 de la Fase 3 pasa a outputs/top20_indice_v1.geojson | El entregable es el modelo validado; la v1 queda como referencia | Mantener la v1 como entregable |
| 2026-11-15 | Los GeoJSON se escriben como texto (to_json) y no con GDAL | GDAL borra el archivo antes de reescribirlo, lo que falla en carpetas sin permiso de borrado | to_file |
