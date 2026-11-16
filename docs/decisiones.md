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
