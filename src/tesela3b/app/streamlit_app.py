"""App · Producto de datos (semana 5).

Ejecutar: streamlit run src/tesela3b/app/streamlit_app.py
Mapa de índice H3, Top 20, áreas de influencia por tienda, fichas por zona y descarga GeoJSON.
Extensión opcional (última fase): chat que traduce preguntas a SQL espacial en DuckDB.
"""
import streamlit as st

st.set_page_config(page_title="3B Geo-Expansion", layout="wide")
st.title("3B Geo-Expansion · CDMX")
st.info("En construcción: el mapa se conecta a data/gold en la semana 5.")
