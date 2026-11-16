"""Tests de las reglas de negocio de Silver DENUE con datos sintéticos (no requieren el DENUE real)."""
import pandas as pd
import pytest

from tesela3b import config as cfg
from tesela3b.silver import denue as d

# Centro de la CDMX y desplazamientos aproximados en grados (1e-4 grados ≈ 11 m)
LAT, LON = 19.40, -99.15


def fila(id_, nom, raz, cod, lat=LAT, lon=LON, fecha="2024-05", **extra):
    base = {c: "" for c in d.COLUMNAS}
    base.update(id=str(id_), clee=f"c{id_}", nom_estab=nom, raz_social=raz, codigo_act=cod,
                per_ocu="6 a 10 personas", cve_ent="09", cve_mun="007", municipio="Iztapalapa",
                cve_loc="0001", ageb="1234", latitud=str(lat), longitud=str(lon), fecha_alta=fecha)
    base.update(extra)
    return base


def df(*filas):
    return pd.DataFrame(list(filas))


# --- Identificación de 3B --------------------------------------------------
@pytest.mark.parametrize("nom,raz,cod,esperado", [
    ("TIENDAS TRES B", "TIENDAS TRES B", "462112", True),
    ("TIENDA 3B", "", "462112", True),
    ("T3B", "TIENDAS TRES B SA DE CV", "462112", True),
    ("CENTRO DE DISTRIBUCION CEDIS 3B", "TIENDAS TRES B SA DE CV", "462112", False),  # no es tienda
    ("TIENDAS TRES B OFICINAS EJECUTIVAS", "TIENDAS TRES B", "462112", False),
    ("CIRCULO K", "TIENDAS TRES B SA DE CV", "462112", False),                       # otra marca
    ("TIENDAS 3B", "TIENDAS 3B", "468212", False),                                    # código no es tienda
    ("ALMACENES DE CALZADO LAS 3B", "", "463211", False),
    ("ABARROTES LUPITA", "", "461110", False),
])
def test_identificacion_3b(nom, raz, cod, esperado):
    _, confirmado = d.es_3b(df(fila(1, nom, raz, cod)))
    assert bool(confirmado.iloc[0]) is esperado


# --- Clasificación de competencia -----------------------------------------
@pytest.mark.parametrize("nom,raz,cod,cadena", [
    ("BA EXPRESS TRONCOSO 3416", "NUEVA WAL MART DE MEXICO", "462112", "Bodega Aurrera"),
    ("2767 DOCTORES BOA", "NUEVA WAL MART DE MEXICO", "462111", "Bodega Aurrera"),
    ("BODEGA TULYEHUALCO 3761", "NUEVA WAL MART DE MEXICO", "462111", "Bodega Aurrera"),
    ("SUPERAMA INDIANA 3834", "NUEVA WAL MART DE MEXICO", "462111", "Walmart otros"),
    ("AT&T WALMART CUEMANCO", "NUEVA WAL MART DE MEXICO", "517312", None),           # no es tienda
    ("NETO ARENAL", "TIENDAS SUPER PRECIO SA DE CV", "431110", "Neto"),               # Neto en mayoreo (2021)
    ("650899 NETO ARENAL", "TIENDAS SUPER PRECIO", "462112", "Neto"),
    ("ABARROTES DON NETO", "", "461110", "Abarrotes"),                                # no es Neto
    ("OXXO REFORMA", "CADENA COMERCIAL OXXO", "462112", "OXXO"),
    ("7 ELEVEN SUC 0062 LONDRES", "7-ELEVEN MEXICO", "462112", "7-Eleven"),
    ("CIRCULO K", "TIENDAS TRES B SA DE CV", "462112", "Circle K"),
    ("SUPERCITO SAN RAFAEL", "TIENDAS CHEDRAUI", "462112", "Chedraui"),
    ("CITY MARKET", "COMERCIAL CITY FRESKO", "462111", "La Comer"),
    ("MINISUPER EL SOL", "", "462112", "Minisúper independiente"),
    ("PAPELERIA", "", "465311", None),
])
def test_clasificacion_cadena(nom, raz, cod, cadena):
    resultado = d.clasificar_cadena(df(fila(1, nom, raz, cod))).iloc[0]
    assert (resultado if pd.notna(resultado) else None) == cadena


def test_formato_cubre_todas_las_cadenas():
    assert set(d.CADENAS) <= set(d.FORMATO)


# --- Deduplicación -----------------------------------------------------------
def test_deduplicar_conserva_registro_mas_antiguo():
    crudo = df(
        fila(1, "TIENDAS TRES B", "", "462112", fecha="2024-05"),
        fila(2, "TIENDAS TRES B", "", "462112", lat=LAT + 0.0001, fecha="2019-11"),  # ~11 m: duplicado
        fila(3, "TIENDAS TRES B", "", "462112", lat=LAT + 0.01, fecha="2023-11"),    # ~1.1 km: otra tienda
        fila(4, "ABARROTES A", "", "461110"),                                         # independientes no se tocan
        fila(5, "ABARROTES B", "", "461110"),
    )
    est = d.deduplicar(d.construir_establecimientos(crudo, cfg.CORTE_ACTUAL))
    tres_b = est[est.cadena == "3B"].set_index("id")
    assert set(tres_b.index) == {"2", "3"}
    assert tres_b.loc["2", "n_registros"] == 2
    assert (est.cadena == "Abarrotes").sum() == 2


def test_cadenas_distintas_no_se_deduplican():
    crudo = df(fila(1, "TIENDAS TRES B", "", "462112"),
               fila(2, "OXXO CENTRO", "CADENA COMERCIAL OXXO", "462112", lat=LAT + 0.0001))
    est = d.deduplicar(d.construir_establecimientos(crudo, cfg.CORTE_ACTUAL))
    assert len(est) == 2


# --- Aperturas ---------------------------------------------------------------
def test_aperturas():
    anterior = d.construir_establecimientos(df(fila(1, "TIENDAS TRES B", "", "462112", fecha="2016-01")), cfg.CORTE_BACKTEST)
    actual = d.construir_establecimientos(df(
        fila(10, "TIENDAS TRES B", "", "462112", lat=LAT + 0.0002, fecha="2016-01"),  # ~22 m: la misma tienda
        fila(11, "TIENDAS TRES B", "", "462112", lat=LAT + 0.02, fecha="2024-05"),    # ~2.2 km: apertura
        fila(12, "TIENDAS TRES B", "", "462112", lat=LAT - 0.02, fecha="2019-11"),    # lejos pero alta antigua
    ), cfg.CORTE_ACTUAL)
    act, ant = d.marcar_aperturas(actual, anterior, "2021-11")
    act = act.set_index("id")
    assert not act.loc["10", "apertura"]
    assert act.loc["11", "apertura"] and act.loc["11", "apertura_confirmada"]
    assert act.loc["12", "apertura"] and not act.loc["12", "apertura_confirmada"]
    assert ant["sigue_en_corte_actual"].all()


# --- Personal ocupado y validación ------------------------------------------
def test_personal_ocupado():
    p = d._personal(pd.Series(["0 a 5 personas", "251 y más personas", None]))
    assert p.per_ocu_min.tolist()[:2] == [0, 251]
    assert p.per_ocu_max.iloc[0] == 5 and pd.isna(p.per_ocu_max.iloc[1])


def test_precision_validacion(tmp_path):
    ruta = tmp_path / "muestra.csv"
    pd.DataFrame({"es_3b": ["SI"] * 9 + ["NO", "no se", ""]}).to_csv(ruta, index=False, encoding="utf-8-sig")
    r = d.precision_validacion(ruta)
    assert r["evaluadas"] == 10 and r["son_3b"] == 9 and r["precision"] == 0.9
    assert r["dudosas"] == 1 and r["pendientes"] == 1
    assert r["ic95"][0] < 0.9 < r["ic95"][1]


def test_umbral_distinto_para_3b_y_competencia():
    # ~33 m de separación: 3B se deduplica (umbral 50 m), OXXO no (umbral 25 m)
    crudo = df(
        fila(1, "TIENDAS TRES B", "", "462112"), fila(2, "TIENDAS TRES B", "", "462112", lat=LAT + 0.0003),
        fila(3, "OXXO A", "CADENA COMERCIAL OXXO", "462112", lon=LON + 0.01),
        fila(4, "OXXO B", "CADENA COMERCIAL OXXO", "462112", lon=LON + 0.01, lat=LAT + 0.0003),
    )
    est = d.deduplicar(d.construir_establecimientos(crudo, cfg.CORTE_ACTUAL))
    assert (est.cadena == "3B").sum() == 1
    assert (est.cadena == "OXXO").sum() == 2


def test_direccion_y_codigo_postal():
    crudo = df(fila(1, "TIENDAS TRES B", "", "462112", tipo_vial="AVENIDA", nom_vial="AVENIDA DE LOS MAESTROS",
                    numero_ext="495", cod_postal="2800"))
    e = d.construir_establecimientos(crudo, cfg.CORTE_ACTUAL).iloc[0]
    assert e.direccion == "Avenida De Los Maestros 495"
    assert e.cod_postal == "02800"


def test_precision_validacion_tolera_formato_de_excel(tmp_path):
    # Excel en español puede re-guardar como texto con tabuladores y codificación Windows
    ruta = tmp_path / "muestra.csv"
    pd.DataFrame({"colonia": ["Nueva Santa María"] * 2, "es_3b": ["SI", "NO"]}).to_csv(
        ruta, index=False, sep="\t", encoding="cp1252")
    r = d.precision_validacion(ruta)
    assert r["evaluadas"] == 2 and r["son_3b"] == 1
