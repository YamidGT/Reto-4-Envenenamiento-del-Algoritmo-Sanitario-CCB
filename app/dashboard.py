"""
dashboard.py
============
Dashboard visual del ataque vs. la defensa en profundidad (Streamlit).
Pensado para la presentación en vivo ante el jurado: tema propio, tarjetas
KPI, gráficos Plotly con la paleta validada del equipo (ver dataviz skill),
organización por pestañas y una sección de robustez cuantitativa (barrido
de intensidades de ataque x semillas).

Ejecutar:  streamlit run app/dashboard.py
"""

import os
import sys

import plotly.graph_objects as go
import streamlit as st

# Permite importar los módulos de src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generar_datos import generar_datos                    # noqa: E402
from modelo import entrenar_modelo, evaluar, importancia_variables  # noqa: E402
from gobernanza import firmar_dataset, verificar_dataset    # noqa: E402
from ataque_poisoning import envenenar                      # noqa: E402
from defensa import (detectar_envenenamiento, metricas_deteccion,  # noqa: E402
                     limpiar_dataset, entrenar_modelo_referencia,
                     gate_despliegue)
from robustez import (correr_barrido, resumen_por_tasa,             # noqa: E402
                      registros_en_cuarentena_con_razon)

# ---------------------------------------------------------------------------
# Paleta — valores tomados de la referencia validada del dataviz skill
# (references/palette.md): categórica de 8 tonos, estado fijo (good/critical),
# y superficie/tinta claras. No se ciclan colores ni se inventan tonos nuevos.
# ---------------------------------------------------------------------------
SURFACE       = "#fcfcfb"
GRID          = "#e1e0d9"
INK           = "#0b0b0b"
INK_MUTED     = "#898781"
BASELINE      = "#2a78d6"   # slot categórico 1 (azul) — línea base / neutral
GOOD          = "#0ca30c"   # estado: bueno
CRITICAL      = "#d03b3b"   # estado: crítico
CAT_ORDER     = ["#2a78d6", "#eb6834", "#1baf7a"]  # slots 1/2/3: azul, naranja, aqua
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

FEATURE_LABELS = {
    "quejas_ciudadanas": "Quejas ciudadanas",
    "violaciones_previas": "Violaciones previas",
    "dias_desde_ultima_inspeccion": "Días desde última inspección",
    "temp_refrigeracion_c": "Temp. de refrigeración (°C)",
    "indice_higiene": "Índice de higiene",
    "rotacion_personal": "Rotación de personal",
    "volumen_diario_kg": "Volumen diario (kg)",
}

st.set_page_config(page_title="Blindaje IA Sanitaria — CCB", page_icon="🛡️",
                   layout="wide")


# ---------------------------------------------------------------------------
# CSS — tema propio (tarjetas KPI, badges de estado, hero, citas)
# ---------------------------------------------------------------------------
def inyectar_css():
    st.markdown(f"""
    <style>
      .block-container {{ padding-top: 1.5rem; max-width: 1180px; }}

      .cnb-hero {{
        background: linear-gradient(120deg, #184f95 0%, {BASELINE} 55%, #1baf7a 130%);
        border-radius: 18px;
        padding: 2rem 2.2rem;
        color: #ffffff;
        margin-bottom: 1.6rem;
      }}
      .cnb-hero h1 {{
        font-size: 1.9rem; font-weight: 800; margin: 0 0 0.35rem 0; color: #fff;
      }}
      .cnb-hero p {{
        font-size: 1.0rem; margin: 0; opacity: 0.92; max-width: 62ch;
      }}
      .cnb-hero .cnb-tag {{
        display: inline-block; font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.06em; text-transform: uppercase;
        background: rgba(255,255,255,0.16); padding: 0.22rem 0.6rem;
        border-radius: 999px; margin-bottom: 0.7rem;
      }}

      .cnb-quote {{
        border-left: 4px solid {BASELINE};
        background: {SURFACE};
        padding: 0.9rem 1.1rem; border-radius: 0 10px 10px 0;
        font-style: italic; color: {INK}; margin: 0.4rem 0 1.4rem 0;
      }}

      .cnb-section-title {{
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 1.15rem; font-weight: 700; color: {INK};
        margin: 1.6rem 0 0.8rem 0;
        border-left: 5px solid {BASELINE}; padding-left: 0.6rem;
      }}

      .cnb-cards {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin-bottom: 0.4rem; }}
      .cnb-card {{
        flex: 1 1 200px; background: {SURFACE}; border-radius: 14px;
        padding: 1.0rem 1.15rem; box-shadow: 0 1px 3px rgba(11,11,11,0.08);
        border-left: 4px solid {INK_MUTED};
      }}
      .cnb-card--neutral {{ border-left-color: {BASELINE}; }}
      .cnb-card--good    {{ border-left-color: {GOOD}; }}
      .cnb-card--critical {{ border-left-color: {CRITICAL}; }}
      .cnb-card__icon {{ font-size: 1.3rem; }}
      .cnb-card__label {{
        font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.04em; color: {INK_MUTED}; margin-top: 0.3rem;
      }}
      .cnb-card__value {{
        font-size: 1.9rem; font-weight: 800; color: {INK};
        font-variant-numeric: tabular-nums; line-height: 1.15;
      }}
      .cnb-card__delta {{ font-size: 0.82rem; font-weight: 600; margin-top: 0.15rem; }}
      .cnb-card__delta--neutral {{ color: {INK_MUTED}; }}
      .cnb-card__delta--good {{ color: {GOOD}; }}
      .cnb-card__delta--critical {{ color: {CRITICAL}; }}

      .cnb-badge {{
        display: inline-flex; align-items: center; gap: 0.35rem;
        font-weight: 700; font-size: 0.86rem; padding: 0.4rem 0.8rem;
        border-radius: 999px; color: #fff;
      }}
      .cnb-badge--good {{ background: {GOOD}; }}
      .cnb-badge--critical {{ background: {CRITICAL}; }}

      .cnb-footer {{
        margin-top: 2.2rem; padding-top: 1rem; border-top: 1px solid {GRID};
        color: {INK_MUTED}; font-size: 0.82rem; text-align: center;
      }}
    </style>
    """, unsafe_allow_html=True)


def tarjeta(icono, etiqueta, valor, delta=None, tono="neutral"):
    delta_html = (f'<div class="cnb-card__delta cnb-card__delta--{tono}">{delta}</div>'
                  if delta else "")
    return (f'<div class="cnb-card cnb-card--{tono}">'
            f'<div class="cnb-card__icon">{icono}</div>'
            f'<div class="cnb-card__label">{etiqueta}</div>'
            f'<div class="cnb-card__value">{valor}</div>{delta_html}</div>')


def badge(texto, tono="good"):
    icono = "✅" if tono == "good" else "⛔"
    return f'<span class="cnb-badge cnb-badge--{tono}">{icono} {texto}</span>'


def seccion(icono, titulo):
    st.markdown(f'<div class="cnb-section-title">{icono} {titulo}</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Gráficos Plotly (fondo/tinta/grid de la paleta; sin doble eje; sin ciclar
# colores categóricos; etiquetas de valor directas en cada barra)
# ---------------------------------------------------------------------------
def _layout_base(fig, titulo, altura=340):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color=INK)),
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(color=INK, family=FONT, size=13),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, title=None),
        xaxis=dict(showgrid=False, title=None),
        margin=dict(t=52, b=28, l=28, r=20),
        height=altura, showlegend=False,
        bargap=0.35,
    )
    return fig


def grafico_escenarios(valores, titulo, sufijo="%"):
    """valores: dict {'Limpio': x, 'Envenenado': y, 'Recuperado': z}."""
    tono = {"Limpio": BASELINE, "Envenenado": CRITICAL, "Recuperado": GOOD}
    categorias = list(valores.keys())
    fig = go.Figure(go.Bar(
        x=categorias, y=list(valores.values()),
        marker_color=[tono[c] for c in categorias],
        text=[f"{v:.1f}{sufijo}" for v in valores.values()],
        textposition="outside", textfont=dict(size=13, color=INK),
        hovertemplate="%{x}: %{y:.1f}" + sufijo + "<extra></extra>",
    ))
    return _layout_base(fig, titulo)


def grafico_vectores(por_vector):
    nombres = {"inyeccion": "Inyección externa", "tampering": "Manipulación",
               "infiltrado": "Infiltrado corrupto"}
    orden = ["inyeccion", "tampering", "infiltrado"]
    presentes = [v for v in orden if v in por_vector and por_vector[v]["total"]]
    x = [nombres[v] for v in presentes]
    y = [por_vector[v]["tasa"] * 100 for v in presentes]
    texto = [f"{por_vector[v]['detectado']}/{por_vector[v]['total']} registros"
             for v in presentes]
    fig = go.Figure(go.Bar(
        x=x, y=y, marker_color=CAT_ORDER[:len(presentes)],
        text=[f"{v:.0f}%" for v in y], textposition="outside",
        customdata=texto,
        hovertemplate="%{x}<br>Tasa de detección: %{y:.0f}%<br>%{customdata}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 110])
    return _layout_base(fig, "Detección por vector de ataque")


def grafico_importancia(importancias, top=5):
    top_items = list(reversed(importancias[:top]))   # mayor arriba en horizontal
    nombres = [FEATURE_LABELS.get(f, f) for f, _ in top_items]
    valores = [p * 100 for _, p in top_items]
    fig = go.Figure(go.Bar(
        x=valores, y=nombres, orientation="h", marker_color=BASELINE,
        text=[f"{v:.1f}%" for v in valores], textposition="outside",
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, title=None)
    fig.update_yaxes(showgrid=False)
    return _layout_base(fig, "Top variables que más pesan en la predicción", altura=300)


def grafico_robustez(resumen):
    """2 series de magnitud comparable (ambas % 0-100) -> un solo eje
    compartido, colores categóricos fijos (slot 1 y 2), leyenda visible
    (regla: >=2 series siempre llevan leyenda)."""
    x = (resumen["tasa_ataque"] * 100).round(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=resumen["recall_recuperado_pct_media"] * 100,
        mode="lines+markers", name="% desempeño recuperado",
        line=dict(color=CAT_ORDER[0], width=2), marker=dict(size=8),
        hovertemplate="Ataque %{x:.0f}%%<br>Recuperado: %{y:.0f}%%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=resumen["pct_veneno_detectado_media"] * 100,
        mode="lines+markers", name="% veneno detectado",
        line=dict(color=CAT_ORDER[1], width=2, dash="dot"), marker=dict(size=8),
        hovertemplate="Ataque %{x:.0f}%%<br>Detectado: %{y:.0f}%%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Robustez: recuperación y detección vs. intensidad del ataque",
                   font=dict(size=15, color=INK)),
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(color=INK, family=FONT, size=13),
        xaxis=dict(title="Intensidad del ataque (%)", showgrid=False),
        yaxis=dict(title="%", showgrid=True, gridcolor=GRID, zeroline=False,
                   range=[0, 110]),
        margin=dict(t=52, b=40, l=40, r=20), height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


# ---------------------------------------------------------------------------
# Hero + sidebar
# ---------------------------------------------------------------------------
inyectar_css()

st.markdown("""
<div class="cnb-hero">
  <span class="cnb-tag">Reto 4 · Cámara de Comercio de Bogotá</span>
  <h1>🛡️ Blindando la IA de Inspección Sanitaria</h1>
  <p>Defensa en profundidad contra Data Poisoning: criptografía en el origen del
  dato + inteligencia artificial cazando al infiltrado corrupto. Ajusta el ataque
  en la barra lateral y observa cómo el sistema se defiende en tiempo real.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Parámetros de la simulación")
    tasa = st.slider("Intensidad del ataque (% del pipeline envenenado)",
                     0.0, 0.40, 0.15, 0.05)
    st.markdown("---")
    st.markdown("**Métrica clave: RECALL**\n\nDe todos los establecimientos "
                "peligrosos, ¿cuántos detecta la IA? Un peligroso no detectado "
                "= un ciudadano en riesgo.")
    st.markdown("---")
    st.markdown("**3 vectores de ataque:**\n\n"
                "1. 🔵 Inyección externa (firma inválida)\n"
                "2. 🟠 Manipulación de etiquetas (rompe la firma)\n"
                "3. 🟢 Infiltrado corrupto (firma válida)")
    correr = st.button("▶️ Ejecutar simulación", type="primary", width="stretch")
    st.markdown("---")
    st.caption("Equipo: Yamid GT · Andrés · Alejandro Higuera C. — CCB")


@st.cache_data
def preparar_datos():
    datos = generar_datos(n=3000, semilla=42)
    return (datos.iloc[:400].copy(),
            firmar_dataset(datos.iloc[400:2400].copy()),
            datos.iloc[2400:].copy())


def pipeline(tasa):
    semilla_conf, train_firmado, test_dorado = preparar_datos()
    ref = entrenar_modelo_referencia(semilla_conf)

    m_limpio = evaluar(entrenar_modelo(train_firmado), test_dorado, "LIMPIO")

    train_env = envenenar(train_firmado, tasa=tasa, semilla=7)
    m_env = evaluar(entrenar_modelo(train_env), test_dorado, "ENVENENADO")
    n_invalidos = int((~verificar_dataset(train_env)).sum())

    sospechoso, reporte = detectar_envenenamiento(train_env, ref)
    md = metricas_deteccion(train_env, sospechoso)
    train_saneado = limpiar_dataset(train_env, sospechoso)
    modelo_recuperado = entrenar_modelo(train_saneado)
    m_rec = evaluar(modelo_recuperado, test_dorado, "RECUPERADO")

    gate_env = gate_despliegue(m_env, metricas_referencia=m_limpio)
    gate_rec = gate_despliegue(m_rec, metricas_referencia=m_limpio)

    return (m_limpio, m_env, m_rec, reporte, md, n_invalidos, gate_env, gate_rec,
            modelo_recuperado, train_env, ref)


# ---------------------------------------------------------------------------
# Cuerpo principal
# ---------------------------------------------------------------------------
if correr or tasa:
    (m_limpio, m_env, m_rec, reporte, md, n_invalidos, gate_env, gate_rec,
     modelo_recuperado, train_env, ref) = pipeline(tasa)

    st.markdown('<div class="cnb-quote">"No confiamos ciegamente en el dato: lo '
               'firmamos, lo auditamos, lo validamos contra la verdad de campo, '
               'y vigilamos el modelo en tiempo real."</div>',
               unsafe_allow_html=True)

    tab_resumen, tab_defensa, tab_explica, tab_auditoria = st.tabs(
        ["📊 Resumen ejecutivo", "🛡️ Defensa en profundidad", "🔍 Explicabilidad",
         "🗂️ Auditoría"])

    # ------------------------------------------------------------------ TAB 1
    with tab_resumen:
        seccion("🎯", "Impacto en el RECALL (peligrosos detectados)")
        st.markdown('<div class="cnb-cards">' +
            tarjeta("🟢", "Modelo LIMPIO", f"{m_limpio['recall_riesgo']:.0%}",
                   "Línea base de confianza", "neutral") +
            tarjeta("🔴", "Modelo ENVENENADO", f"{m_env['recall_riesgo']:.0%}",
                   f"{(m_env['recall_riesgo']-m_limpio['recall_riesgo'])*100:+.0f} pts vs. línea base",
                   "critical") +
            tarjeta("🛡️", "Modelo RECUPERADO", f"{m_rec['recall_riesgo']:.0%}",
                   f"{(m_rec['recall_riesgo']-m_env['recall_riesgo'])*100:+.0f} pts vs. envenenado",
                   "good") +
            '</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(grafico_escenarios({
                "Limpio": m_limpio["recall_riesgo"] * 100,
                "Envenenado": m_env["recall_riesgo"] * 100,
                "Recuperado": m_rec["recall_riesgo"] * 100,
            }, "Recall sobre alto riesgo"), width="stretch")
        with c2:
            st.plotly_chart(grafico_escenarios({
                "Limpio": m_limpio["peligrosos_no_detectados"],
                "Envenenado": m_env["peligrosos_no_detectados"],
                "Recuperado": m_rec["peligrosos_no_detectados"],
            }, "Peligrosos que NO serían inspeccionados", sufijo=""),
                width="stretch")

        st.caption("⚠️ Cada establecimiento peligroso dejado pasar como \"seguro\" "
                  "es un riesgo directo para la salud pública.")

    # ------------------------------------------------------------------ TAB 2
    with tab_defensa:
        seccion("🚦", "Gate de despliegue (barrera automática a producción)")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"**Modelo envenenado:** " +
                       badge(gate_env[1], "good" if gate_env[0] else "critical"),
                       unsafe_allow_html=True)
        with g2:
            st.markdown(f"**Modelo recuperado:** " +
                       badge(gate_rec[1], "good" if gate_rec[0] else "critical"),
                       unsafe_allow_html=True)

        seccion("🔒🧠", "Qué detiene cada capa")
        st.markdown('<div class="cnb-cards">' +
            tarjeta("🔒", "Capa 1 · Criptografía", f"{n_invalidos} rechazados",
                   "Inyección + manipulación: firma inválida o integridad rota",
                   "neutral") +
            tarjeta("🧠", "Capa 2 · IA", f"{reporte['capa2_ia']} cazados",
                   "Modelo de referencia + reglas + anomalías (incluye al infiltrado)",
                   "neutral") +
            '</div>', unsafe_allow_html=True)

        if md and md["por_vector"]:
            st.plotly_chart(grafico_vectores(md["por_vector"]), width="stretch")

        if md:
            seccion("📈", "Eficacia global de la defensa")
            st.markdown('<div class="cnb-cards">' +
                tarjeta("☣️", "Veneno inyectado", md["veneno_total"], tono="neutral") +
                tarjeta("🎯", "Veneno detectado", md["veneno_detectado"],
                       f"{md['recall_defensa']:.0%} del ataque", "good") +
                tarjeta("✅", "Precisión de detección", f"{md['precision_defensa']:.0%}",
                       tono="neutral") +
                tarjeta("🗂️", "En cuarentena", reporte["sospechosos_final"],
                       tono="neutral") +
                '</div>', unsafe_allow_html=True)

        st.info("💡 Sube la intensidad del ataque en la barra lateral y observa "
               "cómo la defensa sigue conteniendo el daño y el gate bloquea el "
               "modelo malo.")

    # ------------------------------------------------------------------ TAB 3
    with tab_explica:
        seccion("🔍", "El modelo recuperado se puede auditar")
        st.caption("Variables que más pesan en la predicción del modelo final "
                  "(RandomForest, `feature_importances_`). La transparencia es "
                  "lo que permite defender una decisión ante un ciudadano o un juez.")
        importancias = importancia_variables(modelo_recuperado)
        st.plotly_chart(grafico_importancia(importancias), width="stretch")

    # ------------------------------------------------------------------ TAB 4
    with tab_auditoria:
        seccion("🗂️", "Registros en cuarentena (con razón de detección)")
        cuarentena_df = registros_en_cuarentena_con_razon(train_env, ref)
        st.caption(f"{len(cuarentena_df)} registros aislados en esta corrida — "
                  "ninguno se borra a ciegas, todos quedan trazables para "
                  "revisión humana.")
        st.dataframe(cuarentena_df, width="stretch")

    st.markdown('<div class="cnb-footer">Reto 4 — Envenenamiento del Algoritmo '
               'Sanitario · Cámara de Comercio de Bogotá · '
               'github.com/YamidGT/Reto-4-Envenenamiento-del-Algoritmo-Sanitario-CCB'
               '</div>', unsafe_allow_html=True)
else:
    st.info("👈 Ajusta los parámetros y presiona **Ejecutar simulación**.")

st.markdown("---")
seccion("📈", "Robustez: ¿la defensa depende de un solo run con suerte?")
st.caption("Barrido de 4 intensidades de ataque x 5 semillas cada una (20 "
          "corridas independientes) — media y desviación estándar.")

if st.button("🔁 Correr barrido de robustez (puede tardar ~1-2 min)"):
    with st.spinner("Corriendo 20 experimentos (4 tasas x 5 semillas)..."):
        df_barrido = correr_barrido()
        resumen = resumen_por_tasa(df_barrido)

    st.session_state["df_barrido"] = df_barrido
    st.session_state["resumen_barrido"] = resumen

if "resumen_barrido" in st.session_state:
    resumen = st.session_state["resumen_barrido"]
    st.plotly_chart(grafico_robustez(resumen), width="stretch")
    st.dataframe(
        resumen.rename(columns={
            "tasa_ataque": "Tasa de ataque",
            "recall_recuperado_pct_media": "Recuperado (media)",
            "recall_recuperado_pct_std": "Recuperado (std)",
            "pct_veneno_detectado_media": "Veneno detectado (media)",
            "pct_veneno_detectado_std": "Veneno detectado (std)",
        }),
        width="stretch",
    )
    st.caption("Los datos completos (20 filas, una por corrida) se guardan en "
              "`results/robustez_resultados.csv` al correr `python src/robustez.py`.")
