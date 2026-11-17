"""Tests del asistente «Pregúntale al mapa» sin internet (proveedor de lenguaje simulado)."""
import json

import pytest

from tesela3b.app import logica as lg
from tesela3b.app.asistente import agente as ag
from tesela3b.app.asistente import datos_sql as ds
from tesela3b.app.asistente import demo as dm
from tesela3b.app.asistente import evaluacion as ev
from tesela3b.app.asistente import llm
from tesela3b.app.asistente.herramientas import Herramientas

pytestmark = pytest.mark.skipif(not (lg.DATOS / "hexagonos.parquet").exists(), reason="falta el paquete de datos de la app")


@pytest.fixture(scope="module")
def herr():
    return Herramientas(lg.cargar())


P1 = llm.Proveedor("groq", "Groq", "http://x", "modelo-a", "k1")
P2 = llm.Proveedor("gemini", "Gemini", "http://y", "modelo-b", "k2")


# --- Base de datos de solo lectura ---------------------------------------------------------------
@pytest.mark.parametrize("sql", ["DROP TABLE zonas", "SELECT 1; DROP TABLE zonas", "INSERT INTO zonas VALUES (1)",
                                 "SELECT * FROM read_csv('x.csv')", "ATTACH 'x.db'", "COPY zonas TO 'x.csv'",
                                 "SELECT * FROM 'datos.parquet'", "SET enable_external_access = true"])
def test_bloquea_escritura_y_archivos(herr, sql):
    with pytest.raises(ds.ErrorConsulta):
        ds.ejecutar(herr.con, sql)


def test_consulta_valida_con_limite(herr):
    df = ds.ejecutar(herr.con, "SELECT h3 FROM zonas")
    assert len(df) == ds.MAX_FILAS
    assert ds.ejecutar(herr.con, "SELECT COUNT(*) AS n FROM tiendas WHERE cadena = 'Set'")["n"][0] == 0   # palabra dentro de texto


def test_resultado_compacto_para_el_modelo(herr):
    from tesela3b.app.asistente import herramientas as hm
    r = herr.consultar_datos("SELECT * FROM zonas")
    assert len(r.para_modelo) <= hm.MAX_CARACTERES + 600 and len(r.tabla) == ds.MAX_FILAS


def test_tablas_consistentes(herr):
    a = ds.ejecutar(herr.con, "SELECT SUM(aperturas_2022_2026) s, SUM(hogares_sin_auto) h FROM alcaldias")
    assert a["s"][0] == 162
    assert a["h"][0] == pytest.approx(herr.d.hexs["hogares_sin_auto"].sum(), rel=1e-3)


# --- Herramientas ---------------------------------------------------------------------------------
def test_top_zonas_igual_a_la_app(herr):
    r = herr.top_zonas("equilibrada", 20)
    app = lg.seleccionar_top(herr.d.hexs, lg.puntaje(herr.d.hexs, 0.5), n=20)
    assert r.h3 == app["h3"].tolist()


def test_alcaldias_flexibles(herr):
    assert herr.normalizar_alcaldia("alvaro obregon") == "Álvaro Obregón"
    assert herr.normalizar_alcaldia("GAM") == "Gustavo A. Madero"
    assert herr.normalizar_alcaldia("Guadalajara") is None
    assert herr.top_zonas("equilibrada", 3, ["Guadalajara"]).error


def test_simular_coincide_con_el_indice(herr):
    r = json.loads(herr.simular_apertura("Chinampac de Juárez", "Iztapalapa").para_modelo)
    f = herr.d.hexs.set_index("h3").loc[herr.simular_apertura("Chinampac de Juárez", "Iztapalapa").h3[0]]
    assert r["hogares_nuevos_para_la_cadena"] == round(f["indice_final"])


def test_herramienta_desconocida_y_argumentos_malos(herr):
    assert herr.ejecutar("borrar_todo", {}).error
    assert herr.ejecutar("top_zonas", {"inventado": 1}).error


# --- Agente con proveedor simulado ------------------------------------------------------------------
def guion(*respuestas):
    """Proveedor falso: devuelve los mensajes en orden; si un elemento es una excepción, la lanza."""
    pila = list(respuestas)
    llamadas = []

    def chat(p, mensajes, herramientas=None, **kw):
        llamadas.append((p.nombre, mensajes))
        r = pila.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    chat.llamadas = llamadas
    return chat


def llamada(nombre, args, id_="c1"):
    return {"role": "assistant", "content": "", "tool_calls": [{"id": id_, "type": "function",
                                                                  "function": {"name": nombre, "arguments": json.dumps(args)}}]}


def test_ciclo_herramienta_y_respuesta(herr):
    top1 = json.loads(herr.top_zonas("equilibrada", 1).para_modelo)["zonas"][0]
    chat = guion(llamada("top_zonas", {"n": 1}),
                 {"role": "assistant", "content": f"La mejor zona es {top1['colonia']} con {top1['hogares_nuevos']:.0f} hogares nuevos."})
    r = ag.responder("¿mejor zona?", [], [P1], herr, chat=chat)
    assert not r.error and r.proveedor == "Groq" and r.cifras_no_verificadas == []
    assert len(r.h3) == 1 and r.resultados[0].nombre == "top_zonas"
    assert chat.llamadas[1][1][-1]["role"] == "tool"        # el resultado regresó al modelo


def test_respaldo_cuando_el_principal_se_agota(herr):
    chat = guion(llm.LimiteProveedor("Groq: límite"), {"role": "assistant", "content": "Eso no está en los datos de la app."})
    r = ag.responder("¿ventas?", [], [P1, P2], herr, chat=chat)
    assert r.proveedor == "Gemini" and "Groq" in r.avisos[0]


def test_todos_fallan_da_mensaje_amable(herr):
    chat = guion(llm.ErrorProveedor("Groq: error 401"), llm.LimiteProveedor("Gemini: límite"))
    r = ag.responder("hola", [], [P1, P2], herr, chat=chat)
    assert r.error and "minuto" in r.texto


def test_corta_ciclos_infinitos(herr):
    chat = guion(*[llamada("top_zonas", {"n": 1}, f"c{i}") for i in range(ag.MAX_PASOS)],
                 {"role": "assistant", "content": "Respuesta final."})
    r = ag.responder("?", [], [P1], herr, chat=chat)
    assert r.texto == "Respuesta final." and len(r.resultados) == ag.MAX_PASOS


def test_detecta_cifras_inventadas(herr):
    res = [herr.resumen_alcaldia("Tláhuac")]
    d = json.loads(res[0].para_modelo)
    ok = f"En Tláhuac hay {d['hogares_sin_auto_sin_3b_10min']:,.0f} hogares sin auto sin 3B ({d['pct_cobertura_10min']}% de cobertura)."
    assert ag.verificar_cifras(ok, res) == []
    assert ag.verificar_cifras(ok + " Venden 2,500,000 pesos.", res) == ["2,500,000"]


def test_las_respuestas_demo_son_verificables(herr):
    for q in dm.EJEMPLOS:
        r = dm.responder_demo(q, herr)
        assert r.texto and ag.verificar_cifras(r.texto, r.resultados, q) == [], q


# --- Proveedores y evaluación -----------------------------------------------------------------------
def test_proveedores_en_orden_y_sin_marcadores():
    ps = llm.proveedores_desde({"GEMINI_API_KEY": "abc", "GROQ_API_KEY": "gsk_x", "GROQ_MODEL": "m"})
    assert [p.clave for p in ps] == ["groq", "gemini"] and ps[0].modelo == "m"
    assert llm.proveedores_desde({"GROQ_API_KEY": "tu_llave_de_groq"}) == []
    ps = llm.proveedores_desde({"GEMINI_API_KEY": "abc", "GROQ_API_KEY": "gsk_x", "LLM_ORDEN": "gemini, groq"})
    assert [p.clave for p in ps] == ["gemini", "groq"]
    assert "gsk_x" not in repr(ps[0])


def test_http_429_es_limite():
    class Resp:
        status_code = 429

    class Sesion:
        def post(self, *a, **k):
            return Resp()
    with pytest.raises(llm.LimiteProveedor):
        llm.chat(P1, [], sesion=Sesion())


def test_evaluacion_califica_bien(herr):
    cs = ev.casos(herr)
    assert len(cs) == 25 and sum(c.tipo == "fuera" for c in cs) == 5
    c = next(x for x in cs if x.tipo == "numero")
    assert ev.contiene(f"Son {float(c.esperado):,.0f} en total.", c)
    assert not ev.contiene("Son 1 en total.", c)
    assert ev.contiene("Eso no está en los datos de la app.", ev.Caso("x", "fuera"))


@pytest.mark.parametrize("cuerpo, esperado", [({"error": {"message": "rate"}}, "rate"),
                                              ([{"error": {"code": 400, "message": "modelo no existe"}}], "modelo no existe"),
                                              (["raro"], "raro")])
def test_errores_de_proveedor_en_cualquier_formato(cuerpo, esperado):
    class Resp:
        status_code = 400
        text = ""
        def json(self):
            return cuerpo

    class Sesion:
        def post(self, *a, **k):
            return Resp()
    with pytest.raises(llm.ErrorProveedor, match=esperado):
        llm.chat(P1, [], sesion=Sesion())


def test_error_inesperado_no_tumba_la_app(herr):
    chat = guion(ValueError("algo raro"), {"role": "assistant", "content": "ok"})
    r = ag.responder("?", [], [P1, P2], herr, chat=chat)
    assert r.texto == "ok" and "inesperado" in r.avisos[0]


def test_esquemas_sin_required_vacio():
    from tesela3b.app.asistente.herramientas import ESQUEMAS
    for e in ESQUEMAS:
        assert e["function"]["parameters"].get("required", ["x"]) != []


@pytest.mark.parametrize("texto", ["36,369 hogares", "36 369 hogares", "36\u202f369 hogares", "36\u00a0369 hogares"])
def test_miles_con_coma_o_espacio(texto):
    assert ag._numeros_texto(texto)[0][1] == 36369
    assert ev.contiene(texto, ev.Caso("x", "numero", 36369))


def test_no_junta_numeros_distintos():
    assert [v for _, v in ag._numeros_texto("entre 2021 y 2026 abrió 10 tiendas")] == [2021, 2026, 10]


def test_desglose_por_cadena_cuenta_como_correcto(herr):
    c = next(x for x in ev.casos(herr) if "Tlalpan" in x.pregunta and "Neto" in x.pregunta)
    a, b = c.alternativas[0]
    assert a + b == c.esperado
    assert ev.contiene(f"Neto: {a} tiendas; Bodega Aurrera: {b} tiendas", c)


def test_texto_con_varias_formas_validas(herr):
    c = next(x for x in ev.casos(herr) if "zona número 1 del Top" in x.pregunta)
    assert ev.contiene("Tiene 307 tienditas y OXXO a 500 m", c) and ev.contiene("mucha vida comercial", c)
    assert not ev.contiene("Tiene 184 hogares nuevos", c)
