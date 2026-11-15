"""Silver · DENUE (semana 2).

- Lee los CSV de Bronze (encoding latin-1, todo como texto).
- Identifica cadenas con config.PATRONES_CADENAS sobre nom_estab + raz_social.
- Filtra a tiendas al menudeo (config.SCIAN_TIENDAS) para excluir CEDIS y oficinas.
- Valida a mano una muestra de 50 tiendas 3B contra el buscador de tiendas3b.com.
- Convierte lat/lon a geometría (EPSG:4326) y guarda en data/silver/denue_{version}.parquet.
- Marca aperturas: tiendas 3B presentes en 2026_05 y ausentes en 2021_11 (por clee y por cercanía < 50 m).
"""
