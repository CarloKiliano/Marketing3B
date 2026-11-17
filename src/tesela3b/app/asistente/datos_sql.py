"""Base de datos del asistente: DuckDB en memoria, de SOLO LECTURA, con nombres de columna en lenguaje de negocio.

El modelo de lenguaje nunca ve los archivos: solo puede pedir consultas SELECT sobre estas 4 tablas, y la app
las ejecuta aquí con guardas (sin acceso a archivos ni a internet, una sola sentencia, máximo de filas y tiempo).
"""
from __future__ import annotations

import re
import threading

import duckdb
import pandas as pd

from tesela3b.app import logica as lg

MAX_FILAS = 200
TIEMPO_MAX_S = 5.0

DICCIONARIO = """TABLAS (DuckDB, solo SELECT):
zonas: un hexágono H3 (~0.1 km²) de la CDMX con vivienda. Columnas:
  h3, colonia, alcaldia, cp, lat, lon,
  hogares, hogares_sin_auto, poblacion, pct_sin_auto (0-100), escolaridad (años),
  comercios_barrio_500m (tienditas+OXXO a 500 m), neto_bodega_500m (Neto/Bodega Aurrera a 500 m),
  tiendas_3b (3B dentro del hexágono hoy), dist_3b_m (a la 3B más cercana),
  hogares_nuevos (hogares sin auto que una 3B ahí ganaría para la cadena, ya descontada la canibalización),
  hogares_canibalizados, pct_canibalizacion (0-100),
  prob_zona_3b (0-1: qué tanto se parece a donde 3B abrió 2021-2026),
  valor_esperado (prob_zona_3b × hogares_nuevos: criterio de la recomendación), prioridad (0-100, percentil del valor esperado),
  cubierta_10min (TRUE si hay una 3B a ≤10 min caminando), hogares_10min_sin_3b
tiendas: cadena ('3B','Neto','Bodega Aurrera'), corte ('2021' o '2026'), colonia, alcaldia, lat, lon, apertura_reciente (bool)
aperturas: las 162 aperturas 3B 2022-2026: alcaldia, colonia, fecha_alta, anticipada_por_modelo ('En zona marcada','Junto a zona marcada','No anticipada')
alcaldias: alcaldia, hogares, hogares_sin_auto, pct_cobertura_10min (0-100), hogares_sin_auto_sin_3b_10min,
  tiendas_3b_2021, tiendas_3b_2026, aperturas_2022_2026, neto_bodega_2026
Nombres de alcaldía con acentos: Álvaro Obregón, Azcapotzalco, Benito Juárez, Coyoacán, Cuajimalpa de Morelos, Cuauhtémoc,
Gustavo A. Madero, Iztacalco, Iztapalapa, La Magdalena Contreras, Miguel Hidalgo, Milpa Alta, Tláhuac, Tlalpan,
Venustiano Carranza, Xochimilco. Para buscar texto usa ILIKE '%...%' (las colonias vienen en Tipo Título)."""

PROHIBIDAS = re.compile(r"\b(attach|detach|copy|install|load|pragma|set|reset|create|insert|update|delete|drop|alter|"
                        r"export|import|call|checkpoint|vacuum|use|grant|truncate|read_\w+|glob|httpfs)\b", re.I)


class ErrorConsulta(Exception):
    """La consulta no es válida o no está permitida (el mensaje se le devuelve al modelo para que corrija)."""


def construir(datos: lg.Datos) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    h = datos.hexs
    zonas = pd.DataFrame({
        "h3": h["h3"], "colonia": h["colonia"].fillna(""), "alcaldia": h["alcaldia"], "cp": h["cp"],
        "lat": h["lat"], "lon": h["lon"], "hogares": h["hogares"].round(0), "hogares_sin_auto": h["hogares_sin_auto"].round(0),
        "poblacion": h["poblacion"].round(0), "pct_sin_auto": h["pct_sin_auto"].round(1),
        "escolaridad": h["escolaridad_promedio"].round(1), "comercios_barrio_500m": h["comercio_500"].round(0),
        "neto_bodega_500m": h["hd_competencia_500"].round(0), "tiendas_3b": h["n_3b"].astype(int),
        "dist_3b_m": h["dist_3b_m"].round(0), "hogares_nuevos": h["indice_final"].clip(lower=0).round(0),
        "hogares_canibalizados": h["canibalizacion"].round(0), "pct_canibalizacion": h["pct_canibalizacion"].round(1),
        "prob_zona_3b": h["p_apertura"].round(4), "valor_esperado": h["valor_esperado"].round(1),
        "prioridad": h["prioridad"].round(1), "cubierta_10min": h["cubierto_10"].astype(bool),
        "hogares_10min_sin_3b": h["isocrona_10"].round(0)})
    ref = h.set_index("h3")[["colonia", "alcaldia"]]
    import h3 as _h3
    t = datos.tiendas.copy()
    celdas = [_h3.latlng_to_cell(a, o, 9) for a, o in zip(t["lat"], t["lon"])]
    nuevas = set(zip(datos.aperturas["lat"].round(5), datos.aperturas["lon"].round(5)))
    tiendas = pd.DataFrame({
        "cadena": t["cadena"], "corte": t["corte"].str[:4],
        "colonia": ref["colonia"].reindex(celdas).fillna("").to_numpy(),
        "alcaldia": ref["alcaldia"].reindex(celdas).fillna("").to_numpy(), "lat": t["lat"], "lon": t["lon"],
        "apertura_reciente": [(c == "3B" and k.startswith("2026") and (round(a, 5), round(o, 5)) in nuevas)
                              for c, k, a, o in zip(t["cadena"], t["corte"], t["lat"], t["lon"])]})
    a = datos.aperturas
    aperturas = pd.DataFrame({"alcaldia": a["municipio"], "colonia": ref["colonia"].reindex(a["h3"]).fillna("").to_numpy(),
                              "fecha_alta": pd.to_datetime(a["fecha_alta"], errors="coerce").dt.date,
                              "anticipada_por_modelo": a["resultado"], "lat": a["lat"], "lon": a["lon"], "h3": a["h3"]})
    con.register("_zonas", zonas)
    con.register("_tiendas", tiendas)
    con.register("_aperturas", aperturas)
    con.execute("CREATE TABLE zonas AS SELECT * FROM _zonas")
    con.execute("CREATE TABLE tiendas AS SELECT * FROM _tiendas")
    con.execute("CREATE TABLE aperturas AS SELECT * FROM _aperturas")
    con.execute("""CREATE TABLE alcaldias AS
        SELECT z.alcaldia, SUM(hogares) AS hogares, SUM(hogares_sin_auto) AS hogares_sin_auto,
               ROUND(100 * SUM(CASE WHEN cubierta_10min THEN hogares_sin_auto ELSE 0 END) / SUM(hogares_sin_auto), 1) AS pct_cobertura_10min,
               SUM(CASE WHEN cubierta_10min THEN 0 ELSE hogares_sin_auto END) AS hogares_sin_auto_sin_3b_10min,
               (SELECT COUNT(*) FROM tiendas t WHERE t.alcaldia = z.alcaldia AND cadena = '3B' AND corte = '2021') AS tiendas_3b_2021,
               (SELECT COUNT(*) FROM tiendas t WHERE t.alcaldia = z.alcaldia AND cadena = '3B' AND corte = '2026') AS tiendas_3b_2026,
               (SELECT COUNT(*) FROM aperturas a WHERE a.alcaldia = z.alcaldia) AS aperturas_2022_2026,
               (SELECT COUNT(*) FROM tiendas t WHERE t.alcaldia = z.alcaldia AND cadena <> '3B' AND corte = '2026') AS neto_bodega_2026
        FROM zonas z GROUP BY z.alcaldia""")
    for n in ("_zonas", "_tiendas", "_aperturas"):
        con.unregister(n)
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    return con


def validar(sql: str) -> str:
    s = sql.strip().rstrip(";").strip()
    s = re.sub(r"^```(sql)?|```$", "", s, flags=re.I).strip()
    if not s:
        raise ErrorConsulta("La consulta está vacía.")
    if ";" in s:
        raise ErrorConsulta("Solo se permite UNA sentencia SELECT (sin ';').")
    if not re.match(r"^(select|with)\b", s, re.I):
        raise ErrorConsulta("Solo se permiten consultas que empiezan con SELECT o WITH.")
    sin_texto = re.sub(r"'[^']*'", "''", s)          # no confundir palabras dentro de textos ('Set', 'Copy'...)
    m = PROHIBIDAS.search(sin_texto)
    if m:
        raise ErrorConsulta(f"Operación no permitida: {m.group(0)}. Solo lectura sobre zonas, tiendas, aperturas, alcaldias.")
    return s


def ejecutar(con: duckdb.DuckDBPyConnection, sql: str, max_filas: int = MAX_FILAS) -> pd.DataFrame:
    s = validar(sql)
    cur = con.cursor()
    temporizador = threading.Timer(TIEMPO_MAX_S, cur.interrupt)
    temporizador.start()
    try:
        return cur.execute(f"SELECT * FROM ({s}) AS q LIMIT {int(max_filas)}").df()
    except duckdb.InterruptException as e:
        raise ErrorConsulta(f"La consulta tardó más de {TIEMPO_MAX_S:.0f} s; simplifícala.") from e
    except duckdb.Error as e:
        raise ErrorConsulta(f"Error de SQL: {str(e).splitlines()[0][:300]}") from e
    finally:
        temporizador.cancel()
        cur.close()
