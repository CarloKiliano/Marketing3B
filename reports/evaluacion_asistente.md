# Evaluación del asistente «Pregúntale al mapa»

Generado por `scripts/10_evaluar_asistente.py`. Proveedores: Groq (openai/gpt-oss-120b), Gemini (gemini-3.8-flash).

**Resultado: 25 de 25 correctas (100%).** 20 preguntas sobre los datos y 5 fuera de los datos (debe reconocer que no puede responder).

| # | ¿Correcta? | Pregunta | Esperado | Respuesta (inicio) | Herramientas | Proveedor | Cifras sin verificar | Tiempo | Avisos |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ✅ | ¿Cuál es la zona número 1 para abrir una 3B en la CDMX? | Zona Centro | La zona número 1 para abrir una 3B en la CDMX es la colonia **Zona Centro**, en la alcaldía **Venustiano Carranza**.  - Hogares nuevos captados: **184**   - Pro… | top_zonas | Groq | — | 1.5 s | — |
| 2 | ✅ | ¿Cuál es la mejor zona para abrir en Iztapalapa? | Iztlahuacan | La zona con mayor potencial en Iztapalapa es la colonia **Iztlahuacan**.  - Hogares nuevos captados: **362**   - Prob. zona tipo 3B: **9.5 %** (se asemeja al pa… | top_zonas | Groq | — | 2.2 s | — |
| 3 | ✅ | ¿Qué porcentaje de los hogares sin auto de Cuauhtémoc tiene una 3B a 10 minutos caminando? | 72.4 | En Cuauhtémoc, el **72.4 %** de los hogares sin auto cuenta con una tienda 3B a 10 min caminando.    - Hogares sin auto totales: 122,156   - Cobertura a 10 min:… | resumen_alcaldia | Groq | 27.6 | 1.4 s | — |
| 4 | ✅ | ¿Cuántos hogares sin auto de Tláhuac no tienen una 3B a 10 minutos? | 36369.0 | En Tláhuac hay **36,369 hogares sin auto** que no cuentan con una tienda 3B a 10 min a pie.  - Hogares sin auto totales: 63,479   - Cobertura a 10 min: 42.7 % (… | resumen_alcaldia | Groq | 26,110 | 1.4 s | — |
| 5 | ✅ | ¿Cuántas tiendas 3B hay hoy en Gustavo A. Madero? | 48 | Hay **48** tiendas 3B en la alcaldía Gustavo A. Madero (2026).… | consultar_datos | Groq | — | 1.2 s | — |
| 6 | ✅ | ¿Cuántas tiendas 3B había en Iztapalapa en 2021? | 29 | En 2021 había **29 tiendas 3B** en la alcaldía de Iztapalapa.… | resumen_alcaldia | Groq | — | 1.7 s | — |
| 7 | ✅ | ¿Cuántas tiendas abrió 3B en Álvaro Obregón entre 2022 y 2026? | 10 | 3B abrió **10 tiendas** en Álvaro Obregón entre 2022 y 2026.… | resumen_alcaldia | Groq | — | 2.3 s | — |
| 8 | ✅ | ¿Cuántas tiendas de Neto y Bodega Aurrera hay en Tlalpan? | 32 | En Tlalpan hay **19 tiendas de Neto** y **13 tiendas de Bodega Aurrera**.  - Neto: 19 sucursales   - Bodega Aurrera: 13 sucursales    (Los datos provienen del r… | consultar_datos | Groq | — | 2.2 s | — |
| 9 | ✅ | Si abro una 3B en la colonia Doctores de Cuauhtémoc, ¿cuántos hogares sin auto captaría? | 316 | Captaría **316 hogares sin auto**; después de descontar la canibalización, serían **243 hogares nuevos** para la cadena.  - Hogares captados: 316   - Hogares ca… | simular_apertura | Groq | — | 1.9 s | — |
| 10 | ✅ | ¿Cuántos hogares nuevos ganaría la cadena con una 3B en Chinampac de Juárez, Iztapalapa? | 811 | Con una 3B en la colonia **Chinampac de Juárez (Iztapalapa)** la cadena ganaría **811 hogares nuevos**.  - Hogares captados: 835   - Hogares canibalizados: 24 (… | simular_apertura | Groq | — | 1.4 s | — |
| 11 | ✅ | ¿Por qué la zona número 1 del Top tiene tanta prioridad? | ['comerci', 'tiendita', 'oxxo', 'tiendas de barrio', 'abarrote', 'negocios'] | La zona 1 (Zona Centro, Venustiano Carranza) tiene la prioridad máxima (100 %) porque combina:  - **184 hogares nuevos** sin auto que captarían. - **Prob. zona … | top_zonas, explicar_zona | Groq | — | 3.3 s | — |
| 12 | ✅ | ¿Qué alcaldía tiene más hogares sin auto sin una 3B a 10 minutos? | Iztapalapa | La alcaldía con mayor número de hogares sin auto que no cuentan con una 3B a 10 min es **Iztapalapa**, con **179,089** hogares.  - Iztapalapa: 179,089 hogares s… | consultar_datos | Groq | — | 1.5 s | — |
| 13 | ✅ | ¿Qué alcaldía tiene la menor cobertura de 3B a 10 minutos caminando? | Milpa Alta | La alcaldía con la menor cobertura de 3B a 10 min caminando es **Milpa Alta**, con **0 %** de hogares sin auto cubiertos.    - Cobertura a 10 min: 0 %   - Hogar… | consultar_datos | Groq | — | 1.6 s | — |
| 14 | ✅ | ¿Cuántos hogares sin auto hay en total en la CDMX según los datos? | 1457621.0 | Hay **1,457,621** hogares sin auto en total en la CDMX según los datos.… | consultar_datos | Groq | — | 1.8 s | — |
| 15 | ✅ | ¿Cuántos hexágonos sin 3B tienen más de 500 hogares nuevos y menos de 5% de canibalización? | 54 | Hay **54 hexágonos** sin tienda 3B que tienen más de 500 hogares nuevos y menos del 5 % de canibalización.… | consultar_datos | Groq | — | 1.5 s | — |
| 16 | ✅ | ¿Cuántas de las aperturas reales cayeron en las zonas que marcaba el modelo? | 40 | 40 aperturas reales cayeron en zonas que el modelo había marcado.… | consultar_datos | Groq | — | 1.6 s | — |
| 17 | ✅ | Con la estrategia de mercado, ¿cuál es la mejor zona? | Chinampac De Juárez | La zona con mayor potencial bajo la estrategia de mercado es **Chinampac De Juárez (Iztapalapa)**.  - Hogares nuevos captados: **811**   - Prob. zona tipo 3B: *… | top_zonas | Groq | — | 2.0 s | — |
| 18 | ✅ | Con la estrategia playbook 3B, ¿cuál es la mejor zona? | Zona Centro | La zona con mayor prioridad bajo la estrategia **playbook 3B** es:  - **Colonia:** Zona Centro   - **Alcaldía:** Venustiano Carranza   - **Hogares nuevos captad… | top_zonas | Groq | — | 1.7 s | — |
| 19 | ✅ | ¿Qué colonia de Coyoacán sin 3B se parece más a donde abre 3B? | Pedregal De Santo Domingo | La colonia sin 3B en Coyoacán que más se asemeja a los sitios donde ha abierto 3B es **Pedregal De Santo Domingo**, con una probabilidad de zona tipo 3B de **0.… | consultar_datos | Groq | — | 2.8 s | — |
| 20 | ✅ | Entre Coyoacán y Álvaro Obregón, ¿cuál tiene más hogares sin auto sin una 3B cerca? | Álvaro Obregón | Álvaro Obregón tiene más hogares sin auto que no cuentan con una 3B a 10 min.  - Álvaro Obregón: **81,265** hogares sin auto sin 3B cercana.   - Coyoacán: **44,… | consultar_datos | Groq | — | 1.7 s | — |
| 21 | ✅ | ¿Cuánto vende al mes la 3B de la colonia Doctores? | reconocer que no está en los datos | Eso no está en los datos de la app. Puedo indicarte cuántos hogares nuevos captaría, la probabilidad de zona tipo 3B, la cobertura a 10 min o los indicadores de… | — | Groq | — | 0.9 s | — |
| 22 | ✅ | ¿Cuál es la renta promedio de un local comercial en Iztapalapa? | reconocer que no está en los datos | Eso no está en los datos de la app. Puedo ofrecerte información sobre hogares sin auto, cobertura a 10 min, número de tiendas 3B, probabilidad de zona tipo 3B o… | — | Groq | — | 0.8 s | — |
| 23 | ✅ | ¿Dónde conviene abrir una 3B en Guadalajara? | reconocer que no está en los datos | Eso no está en los datos de la app. Puedo indicarte las mejores zonas para abrir una 3B en la CDMX, simular la apertura en una colonia o hexágono, explicar por … | — | Groq | — | 0.7 s | — |
| 24 | ✅ | ¿Cuántas tiendas va a abrir 3B en la CDMX en 2027? | reconocer que no está en los datos | Eso no está en los datos de la app. Puedo indicarte cuántas tiendas abrió 3B entre 2022‑2026, la cobertura actual, o las mejores zonas para una apertura futura.… | — | Groq | — | 0.7 s | — |
| 25 | ✅ | ¿A qué hora abre la 3B de Coyoacán? | reconocer que no está en los datos | Eso no está en los datos de la app. Puedo indicarte cuántas 3B hay en Coyoacán, cuántos hogares sin auto podrían captar, la cobertura a 10 min o las zonas con m… | — | Groq | — | 0.7 s | — |

## Respuestas completas

### 1. ✅ ¿Cuál es la zona número 1 para abrir una 3B en la CDMX?

La zona número 1 para abrir una 3B en la CDMX es la colonia **Zona Centro**, en la alcaldía **Venustiano Carranza**.

- Hogares nuevos captados: **184**  
- Prob. zona tipo 3B: **24.4 %**  
- Canibalización estimada: **13.1 %**  
- Distancia a la 3B más cercana: **251 m**.

### 2. ✅ ¿Cuál es la mejor zona para abrir en Iztapalapa?

La zona con mayor potencial en Iztapalapa es la colonia **Iztlahuacan**.

- Hogares nuevos captados: **362**  
- Prob. zona tipo 3B: **9.5 %** (se asemeja al patrón de aperturas 2021‑2026)  
- Canibalización estimada: **13.9 %** (dentro del límite típico)  
- Distancia a la 3B más cercana: **638 m**  

Esta colonia lidera el ranking de Iztapalapa según el modelo de la app.

### 3. ✅ ¿Qué porcentaje de los hogares sin auto de Cuauhtémoc tiene una 3B a 10 minutos caminando?

En Cuauhtémoc, el **72.4 %** de los hogares sin auto cuenta con una tienda 3B a 10 min caminando.  

- Hogares sin auto totales: 122,156  
- Cobertura a 10 min: 72.4 %  
- Hogares sin 3B a 10 min: 33,760 (≈27.6 %)  

Eso indica que la mayoría de los potenciales clientes ya están cubiertos por la red actual.

### 4. ✅ ¿Cuántos hogares sin auto de Tláhuac no tienen una 3B a 10 minutos?

En Tláhuac hay **36,369 hogares sin auto** que no cuentan con una tienda 3B a 10 min a pie.

- Hogares sin auto totales: 63,479  
- Cobertura a 10 min: 42.7 % (≈26,110 hogares cubiertos)  
- Hogares sin cobertura: 36,369 (el número solicitado)  

Eso representa la parte de la población sin auto que aún no está atendida por 3B a distancia caminable.

### 5. ✅ ¿Cuántas tiendas 3B hay hoy en Gustavo A. Madero?

Hay **48** tiendas 3B en la alcaldía Gustavo A. Madero (2026).

### 6. ✅ ¿Cuántas tiendas 3B había en Iztapalapa en 2021?

En 2021 había **29 tiendas 3B** en la alcaldía de Iztapalapa.

### 7. ✅ ¿Cuántas tiendas abrió 3B en Álvaro Obregón entre 2022 y 2026?

3B abrió **10 tiendas** en Álvaro Obregón entre 2022 y 2026.

### 8. ✅ ¿Cuántas tiendas de Neto y Bodega Aurrera hay en Tlalpan?

En Tlalpan hay **19 tiendas de Neto** y **13 tiendas de Bodega Aurrera**.

- Neto: 19 sucursales  
- Bodega Aurrera: 13 sucursales  

(Los datos provienen del registro de tiendas de la app).

### 9. ✅ Si abro una 3B en la colonia Doctores de Cuauhtémoc, ¿cuántos hogares sin auto captaría?

Captaría **316 hogares sin auto**; después de descontar la canibalización, serían **243 hogares nuevos** para la cadena.

- Hogares captados: 316  
- Hogares canibalizados: 73 (23.1 % de canibalización)  
- Hogares nuevos netos: 243  
- Distancia a la 3B más cercana: 155 m (ya hay una 3B en el hexágono)  
- Probabilidad de zona tipo 3B: 17.1 % (prioridad 99.9).

### 10. ✅ ¿Cuántos hogares nuevos ganaría la cadena con una 3B en Chinampac de Juárez, Iztapalapa?

Con una 3B en la colonia **Chinampac de Juárez (Iztapalapa)** la cadena ganaría **811 hogares nuevos**.

- Hogares captados: 835  
- Hogares canibalizados: 24 (2.9 % de canibalización)  
- Prioridad del sitio: 99.8 %  
- Distancia a la 3B más cercana: 1,314 m  
- Cobertura a 10 min: 1,768 hogares sin auto sin 3B cercana.

### 11. ✅ ¿Por qué la zona número 1 del Top tiene tanta prioridad?

La zona 1 (Zona Centro, Venustiano Carranza) tiene la prioridad máxima (100 %) porque combina:

- **184 hogares nuevos** sin auto que captarían.
- **Prob. zona tipo 3B = 24.4 %**, muy cercana al perfil de aperturas 2021‑2026.
- **Baja canibalización (13.1 %)** y está a solo 251 m de la tienda 3B más cercana.
- Factores positivos fuertes: 307 tienditas/OXXO a 500 m, 89 % de hogares compra a pie, y 3 tiendas Neto/Bodega Aurrera cercanas, lo que eleva la probabilidad de éxito.

### 12. ✅ ¿Qué alcaldía tiene más hogares sin auto sin una 3B a 10 minutos?

La alcaldía con mayor número de hogares sin auto que no cuentan con una 3B a 10 min es **Iztapalapa**, con **179,089** hogares.

- Iztapalapa: 179,089 hogares sin auto sin cobertura 10 min.  
- Es la primera en la lista de la métrica “hogares_sin_auto_sin_3b_10min”.  
- Otras alcaldías quedan por debajo de este valor.  

Eso es lo que muestra la base de datos.

### 13. ✅ ¿Qué alcaldía tiene la menor cobertura de 3B a 10 minutos caminando?

La alcaldía con la menor cobertura de 3B a 10 min caminando es **Milpa Alta**, con **0 %** de hogares sin auto cubiertos.  

- Cobertura a 10 min: 0 %  
- Hogares sin auto en la alcaldía: (dato disponible en la tabla de alcaldías)  
- Tiendas 3B en 2021: 0  
- Tiendas 3B en 2026: 0  
- Aperturas 2022‑2026: 0  

Eso no está en los datos de la app, pero puedo mostrarte las mejores zonas en otra alcaldía o simular una apertura donde prefieras.

### 14. ✅ ¿Cuántos hogares sin auto hay en total en la CDMX según los datos?

Hay **1,457,621** hogares sin auto en total en la CDMX según los datos.

### 15. ✅ ¿Cuántos hexágonos sin 3B tienen más de 500 hogares nuevos y menos de 5% de canibalización?

Hay **54 hexágonos** sin tienda 3B que tienen más de 500 hogares nuevos y menos del 5 % de canibalización.

### 16. ✅ ¿Cuántas de las aperturas reales cayeron en las zonas que marcaba el modelo?

40 aperturas reales cayeron en zonas que el modelo había marcado.

### 17. ✅ Con la estrategia de mercado, ¿cuál es la mejor zona?

La zona con mayor potencial bajo la estrategia de mercado es **Chinampac De Juárez (Iztapalapa)**.

- Hogares nuevos captados: **811**  
- Prob. zona tipo 3B: **4.2 %**  
- Canibalización estimada: **2.9 %**  
- Distancia a la 3B más cercana: **1,314 m**  

Esta colonia lidera el ranking por su combinación de hogares sin auto y baja canibalización.

### 18. ✅ Con la estrategia playbook 3B, ¿cuál es la mejor zona?

La zona con mayor prioridad bajo la estrategia **playbook 3B** es:

- **Colonia:** Zona Centro  
- **Alcaldía:** Venustiano Carranza  
- **Hogares nuevos captados:** 145 hogares (sin auto)  
- **Prob. zona tipo 3B:** 30.5 %  
- **Canibalización estimada:** 9.9 %  
- **Distancia a la 3B más cercana:** 572 m  

Esta zona maximiza el valor esperado según el modelo playbook.

### 19. ✅ ¿Qué colonia de Coyoacán sin 3B se parece más a donde abre 3B?

La colonia sin 3B en Coyoacán que más se asemeja a los sitios donde ha abierto 3B es **Pedregal De Santo Domingo**, con una probabilidad de zona tipo 3B de **0.099**.

### 20. ✅ Entre Coyoacán y Álvaro Obregón, ¿cuál tiene más hogares sin auto sin una 3B cerca?

Álvaro Obregón tiene más hogares sin auto que no cuentan con una 3B a 10 min.

- Álvaro Obregón: **81,265** hogares sin auto sin 3B cercana.  
- Coyoacán: **44,434** hogares sin auto sin 3B cercana.  

Por lo tanto, la alcaldía de Álvaro Obregón supera a Coyoacán en este indicador.

### 21. ✅ ¿Cuánto vende al mes la 3B de la colonia Doctores?

Eso no está en los datos de la app. Puedo indicarte cuántos hogares nuevos captaría, la probabilidad de zona tipo 3B, la cobertura a 10 min o los indicadores de prioridad para la colonia Doctores.

### 22. ✅ ¿Cuál es la renta promedio de un local comercial en Iztapalapa?

Eso no está en los datos de la app. Puedo ofrecerte información sobre hogares sin auto, cobertura a 10 min, número de tiendas 3B, probabilidad de zona tipo 3B o los mejores lugares para abrir una nueva 3B en Iztapalapa.

### 23. ✅ ¿Dónde conviene abrir una 3B en Guadalajara?

Eso no está en los datos de la app. Puedo indicarte las mejores zonas para abrir una 3B en la CDMX, simular la apertura en una colonia o hexágono, explicar por qué una zona tiene alta o baja prioridad, o darte un resumen de una alcaldía de la ciudad.

### 24. ✅ ¿Cuántas tiendas va a abrir 3B en la CDMX en 2027?

Eso no está en los datos de la app. Puedo indicarte cuántas tiendas abrió 3B entre 2022‑2026, la cobertura actual, o las mejores zonas para una apertura futura.

### 25. ✅ ¿A qué hora abre la 3B de Coyoacán?

Eso no está en los datos de la app. Puedo indicarte cuántas 3B hay en Coyoacán, cuántos hogares sin auto podrían captar, la cobertura a 10 min o las zonas con mayor prioridad para una nueva apertura.
