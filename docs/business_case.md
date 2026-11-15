# Caso de negocio · 3B Geo-Expansion

> **Aviso:** propuesta formulada como si se presentara a Tiendas 3B, desarrollada como ejercicio académico con datos públicos. No usa información interna de BBB Foods ni está afiliada a la empresa. Con acceso a sus datos (ventas por tienda, tickets, rentas) el mismo modelo se recalibraría; la metodología y la validación se mantienen.

## Cliente
**Tiendas 3B (BBB Foods Inc., NYSE: TBBB)**, cadena hard discount mexicana fundada en 2005.

| Dato | Valor | Fuente |
| --- | --- | --- |
| Tiendas al cierre 2T26 | 3,624 en 17 estados | El Imparcial, 03-09-2026 |
| Aperturas netas últimos 12 meses | 593 | El Imparcial |
| Plan de aperturas 2026 | Hasta 630 | Xataka México |
| Ventas mismas tiendas 2T26 | +20% anual | El Imparcial |
| Frecuencia de visita del cliente | 3–4 veces por semana | Prospecto de IPO |
| Surtido | ~800 productos, >60% marca propia | tiendas3b.com |

## Problema
3B crece abriendo una tienda nueva casi cada día. La decisión de **dónde abrir** es cara (renta, inventario, personal) y riesgosa (canibalización entre tiendas propias, saturación frente a Bodega Aurrera, Neto y OXXO).

## Hipótesis
Con datos públicos se puede construir un índice de potencial por zona que (1) anticipe dónde 3B termina abriendo y (2) detecte zonas con demanda no capturada para activar campañas.

## Objetivos y KPIs
| Pregunta | Entregable | KPI |
| --- | --- | --- |
| ¿Dónde abrir? | Top 20 de zonas (GeoJSON) | Backtest 2021→2026: hit rate@k, AUC, lift vs densidad de población |
| ¿Dónde activar? | Zonas de activación por tienda | Hogares objetivo cubiertos por zona |
| ¿Cómo medir? | Diseño de geo-experimento | Efecto mínimo detectable y número de zonas requerido |

## Impacto (escenario para el pitch)
Si el índice evita X aperturas débiles al año, el ahorro es X × costo de apertura. El costo de apertura es un **supuesto explícito**, no un dato de 3B.

## Fuera de alcance
Pronóstico de ventas por tienda, logística de CEDIS, otros estados (extensión: Zona Metropolitana).

## Por qué proxies de demanda y por qué son válidos
No hay ventas públicas por tienda, así que el modelo estima **demanda potencial**, no ventas:

| Proxy | Fuente | Justificación |
| --- | --- | --- |
| Hogares por zona | Censo 2020 (AGEB) | 3B vende despensa de reposición: la unidad de compra es el hogar, y compra a pie cerca de casa |
| Perfil socioeconómico | Bienes del hogar (Censo) + Grado de Rezago Social (CONEVAL) | El cliente hard discount es de ingreso bajo y medio; un hogar sin auto compra en su colonia |
| Oferta existente | DENUE (3B, Bodega Aurrera, Neto, OXXO, abarrotes) | La demanda ya atendida no es oportunidad |
| Preferencia revelada | Aperturas reales de 3B 2021→2026 (DENUE) | Las decisiones de expansión de la empresa son la "etiqueta" contra la que se valida |

**Argumento central:** si un índice construido solo con datos públicos de 2021 anticipa dónde 3B abrió después, el proxy captura lo que la empresa considera una buena ubicación.

## Comparación de métodos (pedida por el profesor)
| Pregunta | Método clásico (visto en clase) | Método propuesto | Cómo se decide |
| --- | --- | --- | --- |
| ¿Cómo representar la demanda? | KDE (superficie continua) | Hexágonos H3 (celdas iguales, agregables) | Estabilidad del ranking y desempeño en backtest |
| ¿Qué territorio atiende cada tienda? | Voronoi (tienda más cercana en línea recta) | Huff (probabilidad por distancia y atractivo) e isócronas a pie | Cuál índice anticipa mejor las aperturas reales |
