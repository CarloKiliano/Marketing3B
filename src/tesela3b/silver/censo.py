"""Silver · Censo 2020 por AGEB (semana 2).

- Filtra filas de AGEB: AGEB != '0000' y MZA == '000'.
- Reemplaza '*' y 'N/D' por nulos y convierte a numérico.
- Construye CVEGEO = ENTIDAD(2) + MUN(3) + LOC(4) + AGEB(4).
- Variables: POBTOT, TOTHOG, POBHOG, TVIVPARHAB, PROM_OCUP, VPH_AUTOM, VPH_REFRI,
  VPH_LAVAD, VPH_PC, VPH_INTER, GRAPROES, PEA, POCUPADA, POB0_14, POB15_64, POB65_MAS.
"""
