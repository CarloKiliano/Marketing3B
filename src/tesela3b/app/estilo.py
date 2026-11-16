"""Identidad visual de la app: paleta inspirada en 3B (rojo, blanco, amarillo) y componentes HTML."""
from __future__ import annotations

import html

ROJO = "#D7141A"
ROJO_OSCURO = "#8E0C10"
AMARILLO = "#FFC20E"
CREMA = "#FFF6E3"
TINTA = "#231F20"
TINTA_2 = "#5C5657"
GRIS = "#9A9596"
GRIS_CLARO = "#ECE8E6"

# Rampa secuencial (un solo tono, claro -> oscuro) para la prioridad; el amarillo queda reservado al Top.
RAMPA = ["#FDE8E5", "#F8BDB3", "#F08A78", "#E2533F", "#C41F1C", "#7E0D0F"]


def hex_a_rgb(c: str, a: int = 255) -> list[int]:
    c = c.lstrip("#")
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)] + [a]


def color_rampa(valor_0_100: float, alpha: int = 225) -> list[int]:
    i = min(int(valor_0_100 / 100 * len(RAMPA)), len(RAMPA) - 1)
    return hex_a_rgb(RAMPA[i], alpha)


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, p, li, label {{ font-family: 'Inter', sans-serif; }}
h1, h2, h3, h4, .t3b-titulo, .t3b-kpi-valor {{ font-family: 'Poppins', sans-serif !important; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }}
[data-testid="stSidebar"] {{ background: {CREMA}; border-right: 1px solid {GRIS_CLARO}; }}
[data-testid="stSidebar"] h3 {{ color: {ROJO_OSCURO}; font-size: 1.0rem; margin-bottom: .2rem; }}

.t3b-header {{ background: linear-gradient(100deg, {ROJO} 0%, {ROJO} 62%, #B5101A 100%); border-radius: 18px;
  padding: 22px 28px 20px; color: white; position: relative; overflow: hidden; margin-bottom: 14px; }}
.t3b-header:after {{ content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px;
  border-radius: 50%; background: {AMARILLO}; opacity: .95; }}
.t3b-header:before {{ content: ""; position: absolute; right: 120px; bottom: -90px; width: 170px; height: 170px;
  border-radius: 50%; background: rgba(255,255,255,.10); }}
.t3b-titulo {{ font-size: 1.9rem; font-weight: 800; line-height: 1.15; margin: 0; position: relative; z-index: 2; max-width: 82%; }}
.t3b-sub {{ font-size: 1.0rem; opacity: .95; margin-top: 6px; position: relative; z-index: 2; max-width: 70%; }}
.t3b-badge {{ display: inline-block; background: white; color: {ROJO_OSCURO}; font-weight: 600; font-size: .75rem;
  padding: 3px 10px; border-radius: 999px; margin-bottom: 10px; position: relative; z-index: 2; }}

.t3b-kpi {{ background: white; border: 1px solid {GRIS_CLARO}; border-radius: 16px; padding: 14px 18px 12px;
  border-top: 5px solid {ROJO}; height: 100%; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
.t3b-kpi.amarillo {{ border-top-color: {AMARILLO}; }}
.t3b-kpi-etq {{ color: {TINTA_2}; font-size: .82rem; font-weight: 500; }}
.t3b-kpi-valor {{ color: {TINTA}; font-size: 2.0rem; font-weight: 700; line-height: 1.15; margin-top: 2px; }}
.t3b-kpi-nota {{ color: {TINTA_2}; font-size: .78rem; margin-top: 2px; }}
.t3b-kpi-nota b {{ color: {ROJO}; }}

.t3b-ficha {{ background: white; border: 1px solid {GRIS_CLARO}; border-radius: 18px; padding: 18px 20px; }}
.t3b-ficha-num {{ display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px;
  border-radius: 50%; background: {AMARILLO}; color: {TINTA}; font-family: 'Poppins'; font-weight: 800; font-size: 1.1rem;
  margin-right: 10px; }}
.t3b-ficha-titulo {{ font-family: 'Poppins'; font-weight: 700; font-size: 1.25rem; color: {TINTA}; }}
.t3b-ficha-sub {{ color: {TINTA_2}; font-size: .85rem; }}
.t3b-mini {{ background: {CREMA}; border-radius: 12px; padding: 10px 12px; }}
.t3b-mini-etq {{ color: {TINTA_2}; font-size: .75rem; }}
.t3b-mini-valor {{ font-family: 'Poppins'; font-weight: 700; font-size: 1.35rem; color: {TINTA}; line-height: 1.2; }}
.t3b-razon {{ display: flex; gap: 8px; align-items: flex-start; margin: 6px 0; font-size: .92rem; color: {TINTA}; }}
.t3b-razon:before {{ content: "✓"; color: white; background: {ROJO}; border-radius: 50%; min-width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center; font-size: .72rem; font-weight: 700; margin-top: 1px; }}
.t3b-leyenda {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; font-size: .8rem; color: {TINTA_2}; margin: 4px 0 6px; }}
.t3b-leyenda span.c {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }}
.t3b-rampa {{ display: inline-flex; border-radius: 3px; overflow: hidden; vertical-align: -2px; margin: 0 5px; }}
.t3b-rampa i {{ width: 14px; height: 10px; display: inline-block; }}
.t3b-nota {{ color: {TINTA_2}; font-size: .78rem; }}
.t3b-callout {{ background: {CREMA}; border-left: 5px solid {AMARILLO}; border-radius: 10px; padding: 12px 16px; margin: 6px 0 12px;
  color: {TINTA}; font-size: .95rem; }}
.t3b-pill {{ display: inline-block; background: white; border: 1px solid {GRIS_CLARO}; color: {TINTA}; border-radius: 999px;
  padding: 6px 12px; margin: 4px 6px 4px 0; font-size: .85rem; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 2px solid {GRIS_CLARO}; }}
.stTabs [data-baseweb="tab"] {{ height: 46px; padding: 0 18px; border-radius: 12px 12px 0 0; font-family: 'Poppins'; font-weight: 600; }}
.stTabs [aria-selected="true"] {{ background: {CREMA}; color: {ROJO} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {ROJO}; height: 3px; }}
div[data-testid="stMetricValue"] {{ font-family: 'Poppins'; }}
.stDownloadButton button, .stLinkButton a {{ border-radius: 999px !important; }}
footer {{ visibility: hidden; }}
</style>
"""


def esc(t) -> str:
    return html.escape(str(t))


def encabezado(titulo: str, sub: str, badge: str) -> str:
    return (f'<div class="t3b-header"><span class="t3b-badge">{esc(badge)}</span>'
            f'<div class="t3b-titulo" style="font-size:1.65rem;font-weight:800;line-height:1.15">{esc(titulo)}</div><div class="t3b-sub">{esc(sub)}</div></div>')


def kpi(etiqueta: str, valor: str, nota: str = "", amarillo: bool = False) -> str:
    return (f'<div class="t3b-kpi{" amarillo" if amarillo else ""}"><div class="t3b-kpi-etq">{esc(etiqueta)}</div>'
            f'<div class="t3b-kpi-valor">{esc(valor)}</div><div class="t3b-kpi-nota">{nota}</div></div>')


def mini(etiqueta: str, valor: str) -> str:
    return f'<div class="t3b-mini"><div class="t3b-mini-etq">{esc(etiqueta)}</div><div class="t3b-mini-valor">{esc(valor)}</div></div>'


def leyenda(items: list[tuple[str, str]], rampa: bool = True, texto_rampa: str = "prioridad") -> str:
    partes = []
    if rampa:
        cuadros = "".join(f'<i style="background:{c}"></i>' for c in RAMPA)
        partes.append(f'<span>menor<span class="t3b-rampa">{cuadros}</span>mayor {esc(texto_rampa)}</span>')
    partes += [f'<span><span class="c" style="background:{c}"></span>{esc(t)}</span>' for c, t in items]
    return f'<div class="t3b-leyenda">{"".join(partes)}</div>'


def fmt_miles(x: float) -> str:
    return f"{x:,.0f}"


def fmt_compacto(x: float) -> str:
    return f"{x / 1e6:.1f} M" if x >= 1e6 else f"{x / 1e3:,.0f} mil" if x >= 1e4 else f"{x:,.0f}"
