"""Mapa de expansión · Tiendas 3B en la CDMX (Fase 5).

Correr:  streamlit run src/tesela3b/app/streamlit_app.py
Datos:   src/tesela3b/app/datos/ (se generan con scripts/09_preparar_app.py)
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import altair as alt
import h3
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # permite `import tesela3b` en Streamlit Cloud
from tesela3b.app import estilo as es  # noqa: E402
from tesela3b.app import logica as lg  # noqa: E402

st.set_page_config(page_title="Mapa de expansión 3B · CDMX", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(es.CSS, unsafe_allow_html=True)

MAPA_BASE = pdk.map_styles.CARTO_LIGHT
VISTA_CDMX = pdk.ViewState(latitude=19.345, longitude=-99.13, zoom=10.15, pitch=45, bearing=-10)
ESTRATEGIAS = {"Mercado": 0.0, "Más mercado": 0.25, "Equilibrada": 0.5, "Más playbook": 0.75, "Playbook 3B": 1.0}


@st.cache_resource(show_spinner="Cargando el mapa de la CDMX…")
def datos() -> lg.Datos:
    return lg.cargar()


D = datos()
H = D.hexs
M = D.metricas
COMP = {c["modelo"]: c for c in M["comparacion"]}


# ---------------------------------------------------------------------------
# Barra lateral: controles
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"<div style='font-family:Poppins;font-weight:800;font-size:1.35rem;color:{es.ROJO}'>Mapa de expansión"
                f"<span style='color:{es.TINTA}'> · CDMX</span></div>"
                f"<div class='t3b-nota'>Herramienta de decisión para abrir tiendas de descuento</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### Estrategia")
    estrategia = st.select_slider("¿Qué pesa más al elegir zonas?", options=list(ESTRATEGIAS), value="Equilibrada",
                                  help="Mercado: zonas con más hogares sin auto nuevos para la cadena (modelo Huff).\n\n"
                                       "Playbook 3B: zonas parecidas a donde 3B abrió con éxito 2021–2026 (modelo validado).\n\n"
                                       "Equilibrada: valor esperado = probabilidad × hogares nuevos (recomendación del backtest).")
    st.caption({0.0: "Prioriza el tamaño del mercado sin atender.", 0.25: "Mercado primero, con algo del patrón de 3B.",
                0.5: "Recomendada: hogares nuevos ponderados por la probabilidad de que sea zona tipo 3B.",
                0.75: "Patrón de 3B primero, con algo de mercado.",
                1.0: "Replica dónde suele abrir 3B (se concentra en el centro)."}[ESTRATEGIAS[estrategia]])
    st.markdown("### Recomendación")
    n_top = st.slider("Zonas a recomendar", 10, 50, 20, step=5)
    sep = st.slider("Separación mínima entre zonas (m)", 400, 1500, 600, step=100,
                    help="600 m = distancia mediana entre tiendas 3B actuales.")
    canib = st.slider("Canibalización máxima (%)", 5, 50, 50, step=5,
                      help="Excluye zonas que le quitarían más de este % de clientes a otras 3B. 50 = sin tope.")
    alcaldias = st.multiselect("Alcaldías", sorted(H["alcaldia"].dropna().unique()), placeholder="Todas")
    st.divider()
    st.markdown("<div class='t3b-nota'><b>Propuesta académica.</b> Proyecto de la materia Mercadotecnia para Ciencia de "
                "Datos (IIMAS, UNAM). No está afiliado ni respaldado por BBB Foods / Tiendas 3B. Datos públicos: "
                "INEGI (DENUE 2021 y 2026, Censo 2020, Marco Geoestadístico), CONEVAL y © colaboradores de "
                "OpenStreetMap (ODbL).</div>", unsafe_allow_html=True)

w = ESTRATEGIAS[estrategia]
H["puntaje"] = lg.puntaje(H, w)
H["prioridad_actual"] = (100 * H["puntaje"].rank(pct=True)).round(1)
TOP = lg.seleccionar_top(H, H["puntaje"], n=n_top, separacion_m=sep, alcaldias=alcaldias or None,
                         max_canibalizacion=None if canib >= 50 else canib)

# ---------------------------------------------------------------------------
# Encabezado y cifras clave
# ---------------------------------------------------------------------------
st.markdown(es.encabezado("¿Dónde abrir las siguientes tiendas 3B en la CDMX?",
                          "Prioridad por hexágono (≈ 0.1 km²) con datos públicos y un modelo que anticipó las aperturas "
                          "reales de 2021 a 2026.", "Propuesta académica · No afiliada a BBB Foods"),
            unsafe_allow_html=True)
K = lg.kpis(D, TOP)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(es.kpi("Tiendas 3B en la CDMX", f"{K['tiendas']}",
                   f"<b>+{K['tiendas'] - K['tiendas_antes']}</b> desde nov-2021 ({K['tiendas_antes']})"), unsafe_allow_html=True)
c2.markdown(es.kpi("Hogares sin auto con 3B a 10 min", f"{K['cobertura']:.0%}",
                   f"era <b>{K['cobertura_antes']:.0%}</b> en 2021 · caminando por la calle"), unsafe_allow_html=True)
c3.markdown(es.kpi("Hogares sin auto sin 3B cerca", es.fmt_compacto(K["hogares_sin_cobertura"]),
                   "a más de 10 min caminando: mercado por atender"), unsafe_allow_html=True)
c4.markdown(es.kpi("Precisión del modelo (backtest)", f"{K['lift_10']:.1f}×",
                   f"más aperturas que al azar en el 10% mejor calificado · AUC <b>{K['auc']:.2f}</b>", amarillo=True),
            unsafe_allow_html=True)
st.write("")


# ---------------------------------------------------------------------------
# Utilidades de mapa
# ---------------------------------------------------------------------------
def capa_hex(df: pd.DataFrame, id_: str, color_col="color", extruido=True, elev_col="elev", pickable=True, **kw):
    return pdk.Layer("H3HexagonLayer", df, id=id_, get_hexagon="h3", get_fill_color=color_col, extruded=extruido,
                     get_elevation=elev_col if extruido else 0, elevation_scale=1, pickable=pickable,
                     stroked=False, coverage=0.92, auto_highlight=True, highlight_color=[255, 194, 14, 200], **kw)


def capa_puntos(df: pd.DataFrame, id_: str, color, radio=55, **kw):
    return pdk.Layer("ScatterplotLayer", df, id=id_, get_position=["lon", "lat"], get_fill_color=color,
                     get_radius=radio, radius_min_pixels=2.5, radius_max_pixels=7, pickable=True,
                     stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=1, **kw)


def capa_numeros(top: pd.DataFrame, id_="numeros"):
    """Número de posición de cada zona. Va al nivel del suelo pero sin prueba de profundidad, así se dibuja encima de
    las columnas 3D (con altura z, deck.gl en Streamlit lo coloca mal)."""
    t = top.assign(etq=top["posicion"].astype(str))
    return pdk.Layer("TextLayer", t, id=id_, get_position=["lon", "lat"], get_text="etq", get_size=15,
                     get_color=es.hex_a_rgb(es.TINTA), font_weight=700, background=True,
                     get_background_color=es.hex_a_rgb(es.AMARILLO), background_padding=[6, 3, 6, 3],
                     get_border_color=es.hex_a_rgb(es.TINTA), get_border_width=1.5,
                     parameters={"depthTest": False}, pickable=True)


def capa_columnas_top(top: pd.DataFrame, extruido: bool, id_="top_col"):
    """Columnas amarillas (más anchas que el hexágono) para que el Top se vea desde lejos."""
    return pdk.Layer("ColumnLayer", top, id=id_, get_position=["lon", "lat"], get_elevation="elev", elevation_scale=1,
                     radius=230, disk_resolution=6, extruded=extruido, get_fill_color=es.hex_a_rgb(es.AMARILLO),
                     get_line_color=es.hex_a_rgb(es.TINTA), stroked=not extruido, line_width_min_pixels=2,
                     pickable=True, auto_highlight=True)


def texto_hex(df: pd.DataFrame) -> pd.DataFrame:
    """Campos `titulo` y `detalle` que usa la etiqueta emergente (los mismos en todas las capas del mapa)."""
    pos = ("Zona recomendada #" + df["posicion"].astype(str) + " · ") if "posicion" in df else ""
    lugar = df["colonia"].fillna("").replace("", "Sin colonia de referencia") + " · " + df["alcaldia"].fillna("")
    detalle = [f"Prioridad {pr:.0f}/100\nHogares sin auto nuevos: {max(h, 0):,.0f}\nProbabilidad zona tipo 3B: {pa:.0%}"
               f"\nCanibalización: {c:.0f}%\n3B más cercana: {d:,.0f} m"
               for pr, h, pa, c, d in zip(df["prioridad_actual"], df["indice_final"], df["p_apertura"],
                                          df["pct_canibalizacion"], df["dist_3b_m"])]
    return df.assign(titulo=pos + lugar, detalle=detalle)


@st.cache_data(show_spinner=False)
def texto_tiendas(df: pd.DataFrame) -> pd.DataFrame:
    """Etiquetas de las tiendas: cadena, colonia y alcaldía (del hexágono donde está) y si es apertura reciente."""
    ref = H.set_index("h3")[["colonia", "alcaldia"]]
    celdas = [h3.latlng_to_cell(la, lo, 9) for la, lo in zip(df["lat"], df["lon"])]
    col = ref["colonia"].reindex(celdas).fillna("").to_numpy()
    alc = ref["alcaldia"].reindex(celdas).fillna("").to_numpy()
    nuevas = set(zip(D.aperturas["lat"].round(5), D.aperturas["lon"].round(5)))
    titulo, detalle = [], []
    for cad, corte, la, lo, c, a in zip(df["cadena"], df["corte"], df["lat"], df["lon"], col, alc):
        titulo.append("Tienda 3B" if cad == "3B" else f"Competencia · {cad}")
        lugar = " · ".join(x for x in (c, a) if x) or "Fuera de zona habitacional"
        if cad == "3B" and corte == M["cortes"][0]:
            extra = "Ya operaba en noviembre de 2021"
        elif cad == "3B":
            extra = ("Apertura reciente (2022–2026)" if (round(la, 5), round(lo, 5)) in nuevas
                     else "Operando en mayo de 2026")
        else:
            extra = "Hard discount: compite directo por precio"
        detalle.append(f"{lugar}\n{extra}")
    return df.assign(titulo=titulo, detalle=detalle)


TOOLTIP = {"html": "<b>{titulo}</b><br/>{detalle}",
           "style": {"backgroundColor": "white", "color": es.TINTA, "fontFamily": "Inter, sans-serif",
                     "fontSize": "12px", "border": f"2px solid {es.ROJO}", "borderRadius": "10px", "padding": "8px 10px",
                     "whiteSpace": "pre-line", "maxWidth": "280px"}}


def seleccion(evento, capas: tuple[str, ...]) -> str | None:
    try:
        objs = evento.selection["objects"]
    except (AttributeError, KeyError, TypeError):
        return None
    for c in capas:
        if objs.get(c):
            return objs[c][0].get("h3")
    return None


def geojson_top(top: pd.DataFrame) -> str:
    cols = ["posicion", "h3", "colonia", "alcaldia", "indice_final", "p_apertura", "pct_canibalizacion", "dist_3b_m", "lat", "lon"]
    feats = []
    for r in top[cols].itertuples(index=False):
        anillo = [[lon, lat] for lat, lon in h3.cell_to_boundary(r.h3)]
        props = {c: (v.item() if hasattr(v, "item") else v) for c, v in zip(cols, r)}
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Polygon", "coordinates": [anillo + [anillo[0]]]}})
    return json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False)


def tabla_top(top: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"#": top["posicion"], "Colonia de referencia": top["colonia"], "Alcaldía": top["alcaldia"],
                         "Hogares nuevos": top["indice_final"].round(0), "Prob. zona tipo 3B": top["p_apertura"],
                         "Canibalización %": top["pct_canibalizacion"].round(0), "3B más cercana (m)": top["dist_3b_m"],
                         "Hogares a 10 min sin 3B": top["isocrona_10"].round(0), "ID hexágono (H3)": top["h3"],
                         "lat": top["lat"], "lon": top["lon"]})


TABS = st.tabs(["📍 Dónde abrir", "🧪 ¿Y si abro aquí?", "✅ ¿Funciona?", "🧭 Métodos", "💬 Pregúntale al mapa"])

# ===========================================================================
# 1. Dónde abrir
# ===========================================================================
with TABS[0]:
    if TOP.empty:
        st.warning("Ninguna zona cumple los filtros. Prueba con más alcaldías o un tope de canibalización mayor.")
    else:
        izq, der = st.columns([1.7, 1], gap="large")
        with izq:
            o1, o2, o3 = st.columns([1, 1, 1.4])
            ver_3b = o1.toggle("Tiendas 3B", value=True)
            ver_comp = o2.toggle("Neto y Bodega Aurrera", value=False)
            vista_3d = o3.toggle("Vista 3D", value=True)
            base = texto_hex(H)
            base["color"] = [es.color_rampa(v, 215) for v in base["prioridad_actual"]]
            base["elev"] = (base["prioridad_actual"] / 100) ** 4 * 700
            top = texto_hex(TOP.assign(prioridad_actual=TOP["h3"].map(H.set_index("h3")["prioridad_actual"])))
            top["color"] = [es.hex_a_rgb(es.AMARILLO)] * len(top)
            top["elev"] = 1400.0
            capas = [capa_hex(base, "hex", extruido=vista_3d), capa_columnas_top(top, vista_3d, "top")]
            tiendas = D.tiendas[D.tiendas["corte"] == M["cortes"][1]]
            if ver_comp:
                capas.append(capa_puntos(texto_tiendas(tiendas[tiendas["cadena"] != "3B"]), "competencia", es.hex_a_rgb(es.GRIS)))
            if ver_3b:
                capas.append(capa_puntos(texto_tiendas(tiendas[tiendas["cadena"] == "3B"]), "tiendas3b", es.hex_a_rgb(es.TINTA)))
            capas.append(capa_numeros(top))
            vista = VISTA_CDMX if vista_3d else pdk.ViewState(latitude=19.385, longitude=-99.125, zoom=10.3, pitch=0)
            ev = st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=vista, map_style=MAPA_BASE, tooltip=TOOLTIP),
                                 on_select="rerun", selection_mode="single-object", key="mapa_top", height=600)
            st.markdown(es.leyenda([(es.AMARILLO, f"Top {len(TOP)} recomendado (número = posición)"),
                                    (es.TINTA, "Tienda 3B actual")] + ([(es.GRIS, "Neto / Bodega Aurrera")] if ver_comp else [])),
                        unsafe_allow_html=True)
            st.caption("Haz clic en una zona amarilla para ver su ficha. Arrastra con clic derecho para girar el mapa en 3D.")

        etiquetas = [f"#{r.posicion} · {r.colonia or 'Sin colonia'} ({r.alcaldia})" for r in TOP.itertuples()]
        clic = seleccion(ev, ("numeros", "top", "hex"))
        if clic is not None and clic in set(TOP["h3"]):
            st.session_state["zona"] = etiquetas[TOP.index[TOP["h3"] == clic][0]]
        if st.session_state.get("zona") not in etiquetas:
            st.session_state["zona"] = etiquetas[0]

        with der:
            zona = st.selectbox("Zona recomendada", etiquetas, key="zona")
            f = TOP.iloc[etiquetas.index(zona)]
            prior = H.set_index("h3").loc[f["h3"], "prioridad_actual"]
            st.markdown(f"""<div class="t3b-ficha">
              <div style="display:flex;align-items:center"><span class="t3b-ficha-num">{f['posicion']}</span>
              <div><div class="t3b-ficha-titulo">{es.esc(f['colonia'] or 'Zona sin colonia de referencia')}</div>
              <div class="t3b-ficha-sub">{es.esc(f['alcaldia'])} · CP {es.esc(f.get('cp') or '—')} · prioridad {prior:.0f}/100</div></div></div>
            </div>""", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.markdown(es.mini("Hogares sin auto nuevos", es.fmt_miles(max(f["indice_final"], 0))), unsafe_allow_html=True)
            m2.markdown(es.mini("Prob. zona tipo 3B", f"{f['p_apertura']:.0%}"), unsafe_allow_html=True)
            m3, m4 = st.columns(2)
            m3.markdown(es.mini("Canibalización", f"{f['pct_canibalizacion']:.0f}%"), unsafe_allow_html=True)
            m4.markdown(es.mini("3B más cercana", f"{f['dist_3b_m']:,.0f} m"), unsafe_allow_html=True)
            st.markdown("**Por qué esta zona**")
            st.markdown("".join(f'<div class="t3b-razon">{es.esc(r[0].upper() + r[1:])}</div>'
                                for r in lg.razones(f, D.modelo)), unsafe_allow_html=True)
            ex = lg.explicar(f, D.modelo)
            ex["lado"] = np.where(ex["contribucion"] >= 0, "A favor", "En contra")
            graf = alt.Chart(ex).mark_bar(cornerRadiusEnd=4, height=14).encode(
                x=alt.X("contribucion:Q", title="efecto vs. zona promedio", axis=alt.Axis(grid=False)),
                y=alt.Y("corta:N", sort="-x", title=None, axis=alt.Axis(labelLimit=130)),
                color=alt.Color("lado:N", scale=alt.Scale(domain=["A favor", "En contra"], range=[es.ROJO, es.GRIS]), legend=None),
                tooltip=[alt.Tooltip("etiqueta:N", title="Factor"), alt.Tooltip("contribucion:Q", title="Efecto", format="+.2f")],
            ).properties(height=245)
            st.altair_chart(graf, use_container_width=True)
            links = lg.enlaces_mapa(f["lat"], f["lon"])
            b1, b2 = st.columns(2)
            b1.link_button("Google Maps", links["maps"], use_container_width=True)
            b2.link_button("Street View", links["street_view"], use_container_width=True)
            ficha_txt = (f"Zona #{f['posicion']} · {f['colonia']} ({f['alcaldia']})\nH3: {f['h3']}\nCoordenadas: {f['lat']:.6f}, {f['lon']:.6f}\n"
                         f"Hogares sin auto nuevos para la cadena: {max(f['indice_final'], 0):,.0f}\n"
                         f"Probabilidad de zona tipo 3B: {f['p_apertura']:.1%}\nCanibalización: {f['pct_canibalizacion']:.1f}%\n"
                         f"3B más cercana: {f['dist_3b_m']:,.0f} m\nPor qué: " + "; ".join(lg.razones(f, D.modelo)) +
                         f"\nGoogle Maps: {links['maps']}\nEstrategia: {estrategia}\n"
                         "Propuesta académica, no afiliada a BBB Foods.")
            st.download_button("Descargar ficha (.txt)", ficha_txt, file_name=f"ficha_zona_{f['posicion']}.txt",
                               use_container_width=True)

        st.markdown(f"#### Top {len(TOP)} zonas · estrategia «{estrategia}»")
        st.dataframe(tabla_top(TOP).drop(columns=["lat", "lon"]), hide_index=True, use_container_width=True, height=360,
                     column_config={
                         "Hogares nuevos": st.column_config.ProgressColumn(format="%d", min_value=0,
                                                                           max_value=float(max(TOP["indice_final"].max(), 1))),
                         "Prob. zona tipo 3B": st.column_config.ProgressColumn(format="percent", min_value=0,
                                                                               max_value=float(max(TOP["p_apertura"].max(), 0.01))),
                         "Canibalización %": st.column_config.NumberColumn(format="%d%%"),
                         "3B más cercana (m)": st.column_config.NumberColumn(format="%d m"),
                         "Hogares a 10 min sin 3B": st.column_config.NumberColumn(format="%d"),
                         "ID hexágono (H3)": st.column_config.TextColumn(
                             help="Código único del hexágono en el sistema H3 (resolución 9, ≈ 0.1 km²). Es hexadecimal: "
                                  "por eso mezcla números y letras. Sirve para ubicar la zona exacta en QGIS, Python o "
                                  "en el GeoJSON descargado.")})
        d1, d2, d3 = st.columns([1, 1, 2])
        d1.download_button("Descargar GeoJSON", geojson_top(TOP), file_name="top_zonas_3b.geojson",
                           mime="application/geo+json", use_container_width=True)
        d2.download_button("Descargar CSV", tabla_top(TOP).to_csv(index=False).encode("utf-8-sig"),
                           file_name="top_zonas_3b.csv", mime="text/csv", use_container_width=True)
        d3.markdown(f"<div class='t3b-nota' style='padding-top:8px'>El Top {len(TOP)} suma "
                    f"<b>{TOP['indice_final'].clip(lower=0).sum():,.0f}</b> hogares sin auto nuevos para la cadena. "
                    "El GeoJSON se abre en QGIS, Google My Maps o geojson.io.</div>", unsafe_allow_html=True)

# ===========================================================================
# 2. Simulador
# ===========================================================================
with TABS[1]:
    st.markdown("<div class='t3b-callout'><b>Haz clic en cualquier hexágono del mapa</b> (o busca una colonia) y el "
                "modelo calcula al momento cuántos hogares sin auto ganaría la cadena con una 3B ahí, cuántos le quitaría "
                "a otras 3B y cuántos hogares quedarían a 10 minutos caminando.</div>", unsafe_allow_html=True)
    colonias = (H[H["colonia"].fillna("") != ""].sort_values("puntaje", ascending=False)
                .drop_duplicates(["colonia", "alcaldia"]))
    opciones = ["— elegir en el mapa —"] + [f"{r.colonia} ({r.alcaldia})" for r in colonias.itertuples()]
    if "sim_h3" not in st.session_state:
        st.session_state["sim_h3"] = TOP["h3"].iloc[0] if len(TOP) else H.sort_values("puntaje").h3.iloc[-1]
    s1, s2 = st.columns([1.7, 1], gap="large")
    with s2:
        busca = st.selectbox("Buscar colonia", opciones, index=0,
                             help="Toma el hexágono con mayor prioridad de esa colonia.")
        if busca != opciones[0]:
            st.session_state["sim_h3"] = colonias.iloc[opciones.index(busca) - 1]["h3"]
    with s1:
        sim = lg.simular(D, st.session_state["sim_h3"])
        base = texto_hex(H)
        base["color"] = [es.color_rampa(v, 95) for v in base["prioridad_actual"]]
        capas = [capa_hex(base, "hex_sim", extruido=False)]
        if sim.get("valido"):
            ph = sim["por_hex"]
            ph = ph[ph["capturada"] > 0.5].copy()
            mx = max(ph["capturada"].max(), 1)
            ph["color"] = [es.hex_a_rgb(es.ROJO, int(60 + 180 * (v / mx) ** 0.6)) for v in ph["capturada"]]
            capas.append(capa_hex(ph, "captacion", extruido=False, pickable=False))
            if sim.get("alcance_10min"):
                al = pd.DataFrame({"h3": sim["alcance_10min"]})
                capas.append(pdk.Layer("H3HexagonLayer", al, id="alcance", get_hexagon="h3", filled=False, stroked=True,
                                       extruded=False, get_line_color=es.hex_a_rgb(es.TINTA, 160), line_width_min_pixels=1))
            sel = pd.DataFrame({"h3": [sim["h3"]], "color": [es.hex_a_rgb(es.AMARILLO)]})
            capas.append(pdk.Layer("H3HexagonLayer", sel, id="candidata", get_hexagon="h3", get_fill_color="color",
                                   stroked=True, get_line_color=es.hex_a_rgb(es.TINTA), line_width_min_pixels=3, extruded=False))
        t3b = D.tiendas[(D.tiendas["corte"] == M["cortes"][1]) & (D.tiendas["cadena"] == "3B")]
        capas.append(capa_puntos(texto_tiendas(t3b), "tiendas3b_sim", es.hex_a_rgb(es.TINTA)))
        lat0, lon0 = (sim.get("lat", 19.385), sim.get("lon", -99.125)) if sim.get("valido") else (19.385, -99.125)
        ev2 = st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=pdk.ViewState(latitude=lat0, longitude=lon0, zoom=13.2, pitch=0),
                                       map_style=MAPA_BASE, tooltip=TOOLTIP),
                              on_select="rerun", selection_mode="single-object", key="mapa_sim", height=560)
        st.markdown(es.leyenda([(es.AMARILLO, "Tienda simulada"), (es.ROJO, "Hogares que captaría (más intenso = más)"),
                                (es.TINTA, "Tienda 3B actual")], rampa=False) +
                    "<div class='t3b-nota'>El contorno negro marca los hexágonos a 10 minutos caminando por la red de calles.</div>",
                    unsafe_allow_html=True)
    clic2 = seleccion(ev2, ("hex_sim",))
    if clic2 and clic2 != st.session_state["sim_h3"]:
        st.session_state["sim_h3"] = clic2
        st.rerun()
    with s2:
        if not sim.get("valido"):
            st.info("Ese hexágono no tiene vivienda registrada en el Censo 2020: elige otro.")
        else:
            st.markdown(f"<div class='t3b-ficha'><div class='t3b-ficha-titulo'>{es.esc(sim.get('colonia') or 'Zona sin colonia')}</div>"
                        f"<div class='t3b-ficha-sub'>{es.esc(sim.get('alcaldia', ''))} · prioridad "
                        f"{H.set_index('h3').loc[sim['h3'], 'prioridad_actual']:.0f}/100</div></div>", unsafe_allow_html=True)
            if sim.get("n_3b", 0) > 0:
                st.warning("Ya hay una 3B en este hexágono: el resultado mide una tienda adicional.")
            a, b = st.columns(2)
            a.markdown(es.mini("Hogares sin auto que captaría", es.fmt_miles(sim["capturada"])), unsafe_allow_html=True)
            b.markdown(es.mini("Se los quitaría a otras 3B", f"{es.fmt_miles(sim['canibalizacion'])} ({sim['pct_canibalizacion']:.0f}%)"),
                       unsafe_allow_html=True)
            a, b = st.columns(2)
            a.markdown(es.mini("Hogares nuevos para la cadena", es.fmt_miles(max(sim["indice_final"], 0))), unsafe_allow_html=True)
            b.markdown(es.mini("A 10 min sin 3B hoy", es.fmt_miles(sim.get("hogares_10min_sin_3b", 0))), unsafe_allow_html=True)
            a, b = st.columns(2)
            a.markdown(es.mini("Prob. zona tipo 3B", f"{sim.get('p_apertura', 0):.0%}"), unsafe_allow_html=True)
            b.markdown(es.mini("3B más cercana", f"{sim['dist_3b_m']:,.0f} m"), unsafe_allow_html=True)
            if sim["factor_red"] < 1:
                st.caption(f"Está a más de 2.5 km de la red 3B: los hogares nuevos se ponderan × {sim['factor_red']:.2f} por logística.")
            ref = TOP.iloc[0] if len(TOP) else None
            if ref is not None:
                comp = pd.DataFrame({"zona": ["Esta zona", f"#1 del Top ({ref['colonia']})", "Mediana CDMX"],
                                     "hogares": [max(sim["indice_final"], 0), max(ref["indice_final"], 0),
                                                 max(H["indice_final"].median(), 0)]})
                st.altair_chart(alt.Chart(comp).mark_bar(cornerRadiusEnd=4, height=18).encode(
                    x=alt.X("hogares:Q", title="hogares sin auto nuevos", axis=alt.Axis(grid=False)),
                    y=alt.Y("zona:N", sort=None, title=None, axis=alt.Axis(labelLimit=220)),
                    color=alt.condition(alt.datum.zona == "Esta zona", alt.value(es.AMARILLO), alt.value(es.GRIS)),
                    tooltip=["zona", alt.Tooltip("hogares:Q", format=",.0f")]).properties(height=150),
                    use_container_width=True)
            st.link_button("Ver la calle en Street View", lg.enlaces_mapa(sim["lat"], sim["lon"])["street_view"],
                           use_container_width=True)

# ===========================================================================
# 3. ¿Funciona?
# ===========================================================================
with TABS[2]:
    pref, kde = COMP["Modelo de preferencia revelada"], COMP["KDE 500 m (clásico)"]
    top21 = M["tops_2021"]["Valor esperado (recomendación)"]
    ap = D.aperturas
    pct_marc = ap["resultado"].ne("No anticipada").mean()
    st.markdown(f"<div class='t3b-callout'><b>La prueba:</b> construimos el modelo <b>solo con datos de noviembre de 2021</b> "
                f"y lo comparamos con las <b>{len(ap)} tiendas que 3B abrió después</b> (DENUE mayo 2026). "
                "Si el modelo sirve, las aperturas reales debieron caer en las zonas que marcaba.</div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(es.kpi("Aperturas en el 10% de la ciudad mejor calificado", f"{pref['captura_10']:.0%}",
                       f"<b>{pref['lift_10']:.1f}×</b> lo que daría el azar (10%)"), unsafe_allow_html=True)
    k2.markdown(es.kpi("Aperturas en o junto a esas zonas", f"{pct_marc:.0%}", "vecindad de ±1 hexágono"), unsafe_allow_html=True)
    k3.markdown(es.kpi("Top 20 de 2021 que recibió una 3B", f"{top21['aciertos']} de 20",
                       f"al azar: <b>{top21['tasa_azar'] * 20:.0f} de 20</b> (a ≤ 600 m)"), unsafe_allow_html=True)
    k4.markdown(es.kpi("AUC vs KDE clásico", f"{pref['auc']:.2f}", f"KDE: <b>{kde['auc']:.2f}</b> · 0.5 = azar", amarillo=True),
                unsafe_allow_html=True)
    st.write("")
    f1, f2 = st.columns([1.25, 1], gap="large")
    with f1:
        st.markdown("##### Dónde abrió 3B (2022–2026) vs. lo que marcaba el modelo en 2021")
        bh = D.backtest[D.backtest["top10"]].assign(color=[es.hex_a_rgb(es.ROJO, 70)] * int(D.backtest["top10"].sum()))
        colores = {"En zona marcada": es.hex_a_rgb(es.ROJO), "Junto a zona marcada": es.hex_a_rgb(es.AMARILLO),
                   "No anticipada": es.hex_a_rgb(es.GRIS)}
        apc = ap.assign(color=ap["resultado"].map(colores), titulo="Apertura 3B · " + ap["municipio"].fillna(""),
                        detalle="Alta en el DENUE: " + pd.to_datetime(ap["fecha_alta"], errors="coerce").dt.strftime("%m/%Y").fillna("s/f")
                                + "\n" + ap["resultado"])
        t21 = D.tiendas[(D.tiendas["corte"] == M["cortes"][0])]
        capas = [capa_hex(bh, "top10", extruido=False, pickable=False),
                 capa_puntos(texto_tiendas(t21), "t21", es.hex_a_rgb(es.TINTA), radio=40),
                 pdk.Layer("ScatterplotLayer", apc, id="aperturas", get_position=["lon", "lat"], get_fill_color="color",
                           get_radius=120, radius_min_pixels=4, radius_max_pixels=9, pickable=True, stroked=True,
                           get_line_color=es.hex_a_rgb(es.TINTA), line_width_min_pixels=1)]
        st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=pdk.ViewState(latitude=19.38, longitude=-99.13, zoom=10.2),
                                 map_style=MAPA_BASE,
                                 tooltip=TOOLTIP), height=520)
        cnt = ap["resultado"].value_counts()
        st.markdown(es.leyenda([("#F5B7B1", "10% de hexágonos que el modelo marcaba en 2021"),
                                (es.ROJO, f"Apertura en zona marcada ({cnt.get('En zona marcada', 0)})"),
                                (es.AMARILLO, f"Junto a zona marcada ({cnt.get('Junto a zona marcada', 0)})"),
                                (es.GRIS, f"No anticipada ({cnt.get('No anticipada', 0)})"),
                                (es.TINTA, "3B en 2021")], rampa=False), unsafe_allow_html=True)
    with f2:
        st.markdown("##### Si 3B revisara solo una parte de la ciudad…")
        g = M["ganancia"]
        series = {"Modelo de preferencia": "Modelo de preferencia revelada", "KDE clásico": "KDE 500 m (clásico)",
                  "Isócronas 10 min": "Isócrona 10 min (cobertura)"}
        filas = [pd.DataFrame({"x": np.array(g[v]["x"]) * 100, "y": np.array(g[v]["y"]) * 100, "modelo": k}) for k, v in series.items()]
        filas.append(pd.DataFrame({"x": [0, 100], "y": [0, 100], "modelo": "Azar"}))
        gd_ = pd.concat(filas)
        curva = alt.Chart(gd_).mark_line(strokeWidth=2.5).encode(
            x=alt.X("x:Q", title="% de la ciudad revisada (de mejor a peor calificada)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("y:Q", title="% de aperturas encontradas", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("modelo:N", scale=alt.Scale(domain=["Modelo de preferencia", "Isócronas 10 min", "KDE clásico", "Azar"],
                                                         range=[es.ROJO, es.AMARILLO, es.GRIS, "#C9C4C2"]),
                            legend=alt.Legend(orient="bottom", title=None, columns=2, labelLimit=200)),
            strokeDash=alt.condition(alt.datum.modelo == "Azar", alt.value([5, 4]), alt.value([0])),
            tooltip=[alt.Tooltip("modelo:N"), alt.Tooltip("x:Q", title="% ciudad", format=".0f"),
                     alt.Tooltip("y:Q", title="% aperturas", format=".0f")])
        regla = alt.Chart(pd.DataFrame({"x": [10]})).mark_rule(color=es.TINTA_2, strokeDash=[2, 3]).encode(x="x:Q")
        st.altair_chart((curva + regla).properties(height=300), use_container_width=True)
        st.markdown(f"<div class='t3b-nota'>Revisando el 10% mejor calificado, el modelo encuentra el "
                    f"<b>{pref['captura_10']:.0%}</b> de las aperturas; el KDE clásico, el {kde['captura_10']:.0%}.</div>",
                    unsafe_allow_html=True)
        st.markdown("##### ¿Qué busca 3B al abrir?")
        co = pd.DataFrame(M["coeficientes"])
        co["etiqueta"] = co["variable"].map(lg.ETIQUETAS_CORTAS)
        co["lado"] = np.where(co["coef"] >= 0, "Más probable", "Menos probable")
        st.altair_chart(alt.Chart(co).mark_bar(cornerRadiusEnd=4, height=14).encode(
            x=alt.X("coef:Q", title="peso en la decisión", axis=alt.Axis(grid=False)),
            y=alt.Y("etiqueta:N", sort="-x", title=None, axis=alt.Axis(labelLimit=160)),
            color=alt.Color("lado:N", scale=alt.Scale(domain=["Más probable", "Menos probable"], range=[es.ROJO, es.GRIS]), legend=None),
            tooltip=[alt.Tooltip("etiqueta:N", title="Factor"), alt.Tooltip("coef:Q", format="+.2f")]).properties(height=220),
            use_container_width=True)
    st.markdown("##### Todos los métodos, misma prueba")
    cdf = pd.DataFrame(M["comparacion"]).sort_values("auc", ascending=False)
    cdf["grupo"] = np.select([cdf["modelo"].str.contains("preferencia|Valor esperado"),
                              cdf["modelo"].str.contains("KDE|Voronoi|Hogares")], ["Este proyecto", "Clásico / densidad"],
                             "Territorio y competencia")
    pts = alt.Chart(cdf).encode(y=alt.Y("modelo:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)))
    graf = (pts.mark_rule(strokeWidth=4, opacity=.35).encode(x=alt.X("auc_ic_inf:Q", title="AUC (0.5 = azar) · barra = intervalo 95%",
                                                                       scale=alt.Scale(domain=[0.5, 0.82])), x2="auc_ic_sup:Q",
                                                              color=alt.Color("grupo:N", legend=None,
                                                                              scale=alt.Scale(domain=["Este proyecto", "Territorio y competencia", "Clásico / densidad"],
                                                                                              range=[es.ROJO, es.AMARILLO, es.GRIS])))
            + pts.mark_circle(size=140, opacity=1).encode(x="auc:Q", color=alt.Color("grupo:N", legend=alt.Legend(orient="bottom", title=None)),
                                                          tooltip=[alt.Tooltip("modelo:N"), alt.Tooltip("auc:Q", format=".3f"),
                                                                   alt.Tooltip("lift_10:Q", title="lift@10%", format=".1f")])
            + pts.mark_text(dx=14, align="left", fontSize=12, color=es.TINTA).encode(x="auc_ic_sup:Q", text=alt.Text("auc:Q", format=".2f")))
    st.altair_chart(graf.properties(height=330), use_container_width=True)
    pr = M["pruebas"]["Modelo de preferencia revelada vs KDE 500 m (clásico)"]
    st.caption(f"Validación honesta: el modelo nunca calificó una zona que vio al entrenar (validación cruzada por bloques de ~36 km²). "
               f"Ventaja sobre el KDE: +{pr['diferencia']:.3f} de AUC (IC 95% +{pr['ic_inf']:.3f} a +{pr['ic_sup']:.3f}).")

# ===========================================================================
# 4. Métodos
# ===========================================================================
with TABS[3]:
    st.markdown("<div class='t3b-callout'>Tres formas clásicas de dibujar el <b>territorio de una tienda</b>. Las tres se "
                "probaron con el mismo backtest: gana la que mejor anticipa dónde abrió 3B.</div>", unsafe_allow_html=True)
    metodo = st.radio("Método", ["Voronoi", "Isócronas de 10 min", "Huff (probabilidad)"], horizontal=True,
                      label_visibility="collapsed")
    INFO = {
        "Voronoi": ("Voronoi (tienda más cercana)", "Cada hogar compra en la 3B más cercana en línea recta.",
                    "Simple y con fronteras claras.", "Ignora las calles, la competencia de otros formatos y que los territorios se traslapan."),
        "Isócronas de 10 min": ("Isócrona 10 min (cobertura)", "Un hogar está atendido si hay una 3B a 10 minutos caminando por la calle.",
                                "Usa la distancia real por la red peatonal de OpenStreetMap.", "Es binaria (dentro/fuera) y no reparte clientes entre tiendas."),
        "Huff (probabilidad)": ("Huff simple (λ = 1)", "La probabilidad de comprar en una tienda cae con la distancia y sube con su atractivo; compiten todos los formatos.",
                                "Reparte la demanda y mide la canibalización.", "Necesita supuestos (atractivo, decaimiento) que hay que calibrar."),
    }
    nombre, sup, fort, deb = INFO[metodo]
    m1, m2 = st.columns([1.7, 1], gap="large")
    with m1:
        t3b = D.tiendas[(D.tiendas["corte"] == M["cortes"][1]) & (D.tiendas["cadena"] == "3B")]
        capas = []
        if metodo == "Voronoi":
            capas.append(pdk.Layer("GeoJsonLayer", D.capas["voronoi_3b"], id="voronoi", stroked=True, filled=True,
                                   get_fill_color=es.hex_a_rgb(es.CREMA, 120), get_line_color=es.hex_a_rgb(es.ROJO),
                                   line_width_min_pixels=1.5))
        elif metodo == "Isócronas de 10 min":
            capas.append(pdk.Layer("GeoJsonLayer", D.capas["isocronas_3b"], id="iso", stroked=True, filled=True,
                                   get_fill_color=es.hex_a_rgb(es.ROJO, 70), get_line_color=es.hex_a_rgb(es.ROJO_OSCURO, 180),
                                   line_width_min_pixels=0.6))
        else:
            hh = texto_hex(H)
            q = hh["cuota_3b_actual"].rank(pct=True) * 100
            hh["color"] = [es.color_rampa(v, 200) if c > 0.001 else [0, 0, 0, 0] for v, c in zip(q, hh["cuota_3b_actual"])]
            capas.append(capa_hex(hh, "huff", extruido=False, pickable=False))
        capas.append(capa_puntos(texto_tiendas(t3b), "t3b_met", es.hex_a_rgb(es.TINTA)))
        st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=pdk.ViewState(latitude=19.355, longitude=-99.075, zoom=12.4),
                                 map_style=MAPA_BASE, tooltip=TOOLTIP), height=560, key=f"mapa_met_{metodo}")
        st.caption({"Voronoi": "Celdas de Voronoi de las 3B actuales: fronteras rígidas, cada punto pertenece a una sola tienda.",
                    "Isócronas de 10 min": "Área a 10 minutos caminando de cada 3B por la red de calles: huecos y traslapes reales.",
                    "Huff (probabilidad)": "Probabilidad de que un hogar del hexágono compre en una 3B: un gradiente, no una frontera."}[metodo])
    with m2:
        c = COMP[nombre]
        st.markdown(f"<div class='t3b-ficha'><div class='t3b-ficha-titulo'>{es.esc(metodo)}</div>"
                    f"<p style='margin:.4rem 0'><b>Supuesto:</b> {es.esc(sup)}</p>"
                    f"<p style='margin:.4rem 0'><b>Fortaleza:</b> {es.esc(fort)}</p>"
                    f"<p style='margin:.4rem 0'><b>Debilidad:</b> {es.esc(deb)}</p></div>", unsafe_allow_html=True)
        a, b = st.columns(2)
        a.markdown(es.mini("AUC en el backtest", f"{c['auc']:.2f}"), unsafe_allow_html=True)
        b.markdown(es.mini("Aperturas en el 10% superior", f"{c['captura_10']:.0%}"), unsafe_allow_html=True)
        st.write("")
        resumen = pd.DataFrame([{"Método": k, "AUC": COMP[v[0]]["auc"], "Captura 10%": COMP[v[0]]["captura_10"]} for k, v in INFO.items()]
                               + [{"Método": "Modelo del proyecto", "AUC": COMP["Modelo de preferencia revelada"]["auc"],
                                   "Captura 10%": COMP["Modelo de preferencia revelada"]["captura_10"]}])
        st.dataframe(resumen, hide_index=True, use_container_width=True,
                     column_config={"AUC": st.column_config.NumberColumn(format="%.2f"),
                                    "Captura 10%": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=0.3)})
        st.markdown("<div class='t3b-nota'><b>Lectura:</b> la distancia real por la calle (isócronas) le gana a la línea recta "
                    "(Voronoi), y el modelo que aprende de las aperturas reales le gana a todos. El Huff se usa para "
                    "<b>valuar</b> cada zona (hogares nuevos y canibalización).</div>", unsafe_allow_html=True)

# ===========================================================================
# 5. Pregúntale al mapa (capa generativa: siguiente versión)
# ===========================================================================
with TABS[4]:
    import os
    import time

    from tesela3b.app.asistente import agente as ag
    from tesela3b.app.asistente import demo as dm
    from tesela3b.app.asistente import llm
    from tesela3b.app.asistente.herramientas import Herramientas

    @st.cache_resource(show_spinner=False)
    def herramientas() -> Herramientas:
        return Herramientas(D)

    def secretos() -> dict:
        out = {k: v for k, v in os.environ.items() if k.endswith(("_API_KEY", "_MODEL", "_BASE_URL"))}
        try:
            out.update({k: st.secrets[k] for k in st.secrets.keys()})
        except Exception:   # sin archivo de secrets
            pass
        return out

    HERR = herramientas()
    PROV = llm.proveedores_desde(secretos())
    LIMITE_SESION = 15
    ss = st.session_state
    ss.setdefault("chat", [])
    ss.setdefault("n_llm", 0)

    if PROV:
        estado = (f"Conectado a <b>{PROV[0].nombre}</b> ({es.esc(PROV[0].modelo)})"
                  + (f" · respaldo <b>{PROV[1].nombre}</b>" if len(PROV) > 1 else "")
                  + f" · {max(LIMITE_SESION - ss['n_llm'], 0)} preguntas libres restantes en esta sesión")
    else:
        estado = "<b>Modo demo:</b> sin modelo de lenguaje configurado; responden las preguntas de ejemplo con cifras verificadas."
    st.markdown("<div class='t3b-callout'><b>Pregúntale al mapa en lenguaje natural.</b> Un modelo de lenguaje traduce tu "
                "pregunta a consultas sobre <b>estos mismos datos</b> (los ejecuta la app, no el modelo) y responde solo con "
                f"cifras que salen de ahí. Siempre puedes ver cómo se calculó.<br/><span class='t3b-nota'>{estado}</span></div>",
                unsafe_allow_html=True)

    ETIQ = {"top_zonas": "Ranking de zonas (mismo cálculo que «Dónde abrir»)", "simular_apertura": "Simulador de apertura",
            "explicar_zona": "Factores del modelo para la zona", "resumen_alcaldia": "Resumen de la alcaldía",
            "consultar_datos": "Consulta a la base de datos"}

    def mostrar_detalle(resp: ag.Respuesta, clave: str) -> None:
        if resp.cifras_no_verificadas:
            st.warning("Revisa estas cifras: no aparecen en los datos consultados → " + ", ".join(resp.cifras_no_verificadas))
        if resp.resultados:
            with st.expander("¿Cómo lo calculé?"):
                for i, r in enumerate(resp.resultados):
                    st.markdown(f"**{i + 1}. {ETIQ.get(r.nombre, r.nombre)}**" + (" · ⚠️ falló y el asistente corrigió" if r.error else ""))
                    if r.sql:
                        st.code(r.sql, language="sql")
                    else:
                        st.caption("Parámetros: " + ", ".join(f"{k} = {v}" for k, v in r.argumentos.items() if v not in (None, [], "")))
                    if r.tabla is not None and not r.tabla.empty:
                        st.dataframe(r.tabla.drop(columns=[c for c in ("lat", "lon") if c in r.tabla.columns]).head(50),
                                     hide_index=True, use_container_width=True, key=f"tab_{clave}_{i}")
                st.caption(f"Respondió: {resp.proveedor}" + (f" · {resp.modelo}" if resp.modelo else "")
                           + ("  ·  " + " · ".join(resp.avisos) if resp.avisos else ""))

    def mapa_respuesta(h3s: list[str]) -> None:
        sel = H[H["h3"].isin(h3s)]
        base = H.assign(color=[es.color_rampa(v, 70) for v in H["prioridad_actual"]])
        capas = [capa_hex(base, "hex_chat_base", extruido=False, pickable=False)]
        if len(sel):
            hs = texto_hex(sel).assign(color=[es.hex_a_rgb(es.AMARILLO)] * len(sel))
            capas.append(pdk.Layer("H3HexagonLayer", hs, id="hex_chat", get_hexagon="h3", get_fill_color="color",
                                   stroked=True, get_line_color=es.hex_a_rgb(es.TINTA), line_width_min_pixels=2,
                                   extruded=False, pickable=True))
            lat, lon = float(sel["lat"].mean()), float(sel["lon"].mean())
            ext = max(sel["lat"].max() - sel["lat"].min(), (sel["lon"].max() - sel["lon"].min()) * 0.95, 0.004)
            zoom = float(np.clip(np.log2(0.9 / ext) + 7.4, 9.6, 14.0))
        else:
            lat, lon, zoom = 19.36, -99.13, 9.8
        t3b = D.tiendas[(D.tiendas["corte"] == M["cortes"][1]) & (D.tiendas["cadena"] == "3B")]
        capas.append(capa_puntos(texto_tiendas(t3b), "t3b_chat", es.hex_a_rgb(es.TINTA)))
        st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
                                 map_style=MAPA_BASE, tooltip=TOOLTIP), height=470, key=f"mapa_chat_{len(ss['chat'])}")
        st.markdown(es.leyenda([(es.AMARILLO, f"Zonas de la respuesta ({len(sel)})"), (es.TINTA, "Tienda 3B actual")], rampa=False),
                    unsafe_allow_html=True)

    def escribir_lento(texto: str):
        for palabra in texto.split(" "):
            yield palabra + " "
            time.sleep(0.012)

    col_chat, col_mapa = st.columns([1.25, 1], gap="large")
    with col_chat:
        ejemplo = None
        with st.expander("Preguntas de ejemplo (siempre disponibles, con cifras verificadas)", expanded=not ss["chat"]):
            cols_ej = st.columns(2)
            for i, q in enumerate(dm.EJEMPLOS):
                if cols_ej[i % 2].button(q, key=f"ej_{i}", use_container_width=True):
                    ejemplo = q
        conversacion = st.container()
        escrita = st.chat_input("Escribe tu pregunta sobre zonas, alcaldías, cobertura o competencia…")
        pregunta = escrita or ejemplo
        with conversacion:
            if not ss["chat"] and not pregunta:
                st.markdown("<div class='t3b-nota'>Elige una pregunta de ejemplo o escribe la tuya abajo. Puedes seguir la "
                            "conversación: «¿y en Tlalpan?», «simula abrir en la #2».</div>", unsafe_allow_html=True)
            for k, m in enumerate(ss["chat"]):
                with st.chat_message("user" if m["rol"] == "user" else "assistant", avatar="🧑‍💼" if m["rol"] == "user" else "🗺️"):
                    st.markdown(m["texto"])
                    if m.get("resp") is not None:
                        mostrar_detalle(m["resp"], f"h{k}")
            if pregunta:
                with st.chat_message("user", avatar="🧑‍💼"):
                    st.markdown(pregunta)
                with st.chat_message("assistant", avatar="🗺️"):
                    usar_modelo = bool(PROV) and ss["n_llm"] < LIMITE_SESION
                    if usar_modelo:
                        with st.spinner("Consultando los datos…"):
                            historial = [{"role": m["rol"], "content": m["texto"]} for m in ss["chat"]]
                            resp = ag.responder(pregunta, historial, PROV, HERR)
                        ss["n_llm"] += 1
                        if resp.error and pregunta in dm.EJEMPLOS:
                            resp = dm.responder_demo(pregunta, HERR)
                    else:
                        resp = dm.responder_demo(pregunta, HERR)
                        if resp is None:
                            motivo = ("Llegaste al límite de preguntas libres de esta sesión (cuida el plan gratuito)."
                                      if PROV else "Esta versión pública está en modo demo, sin modelo de lenguaje.")
                            resp = ag.Respuesta(texto=f"{motivo} Puedes usar las preguntas de ejemplo, que se responden con "
                                                      "cifras verificadas directamente de los datos.", proveedor="App")
                    st.write_stream(escribir_lento(resp.texto))
                    mostrar_detalle(resp, f"n{len(ss['chat'])}")
                ss["chat"] += [{"rol": "user", "texto": pregunta, "resp": None},
                               {"rol": "assistant", "texto": resp.texto, "resp": resp}]
                ss["ultimo_h3"] = resp.h3
            if ss["chat"]:
                if st.button("Borrar conversación", type="tertiary"):
                    ss["chat"], ss["ultimo_h3"] = [], []
                    st.rerun()
    with col_mapa:
        st.markdown("##### Mapa de la respuesta")
        mapa_respuesta(ss.get("ultimo_h3", []))
        st.markdown("<div class='t3b-nota'>Las preguntas se envían a un modelo de lenguaje gratuito (Groq; respaldo Gemini). "
                    "Solo se envían tu pregunta y resultados agregados de datos públicos. El modelo puede equivocarse al "
                    "interpretar: revisa «¿Cómo lo calculé?».</div>", unsafe_allow_html=True)
