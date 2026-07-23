"""
dashboard.py
============
Dashboard visual del ataque vs. la defensa (Streamlit). Opcional pero vistoso
para la presentación en vivo.

Ejecutar:  streamlit run app/dashboard.py
"""

import os
import sys

import pandas as pd
import streamlit as st

# Permite importar los módulos de src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generar_datos import generar_datos                    # noqa: E402
from modelo import entrenar_modelo, evaluar                 # noqa: E402
from ataque_poisoning import envenenar                      # noqa: E402
from defensa import (detectar_envenenamiento, metricas_deteccion,  # noqa: E402
                     limpiar_dataset, entrenar_modelo_referencia)
from robustez import (correr_barrido, resumen_por_tasa,             # noqa: E402
                      registros_en_cuarentena_con_razon)

st.set_page_config(page_title="Defensa Anti-Envenenamiento Sanitario",
                   page_icon="🛡️", layout="wide")

st.title("🛡️ Blindaje de la IA de Inspección Sanitaria")
st.caption("Reto 4 · Cámara de Comercio de Bogotá — Ataque de Data Poisoning vs. Sistema de Defensa")

with st.sidebar:
    st.header("⚙️ Parámetros")
    tasa = st.slider("Intensidad del ataque (% del pipeline envenenado)",
                     0.0, 0.40, 0.15, 0.05)
    st.markdown("---")
    st.markdown("**Métrica clave: RECALL**\n\nDe todos los establecimientos "
                "peligrosos, ¿cuántos detecta la IA? Un peligroso no detectado "
                "= un ciudadano en riesgo.")
    correr = st.button("▶️ Ejecutar simulación", type="primary")


@st.cache_data
def preparar_datos():
    datos = generar_datos(n=3000, semilla=42)
    return (datos.iloc[:400].copy(),
            datos.iloc[400:2400].copy(),
            datos.iloc[2400:].copy())


def pipeline(tasa):
    semilla_conf, train_limpio, test_dorado = preparar_datos()
    ref = entrenar_modelo_referencia(semilla_conf)

    m_limpio = evaluar(entrenar_modelo(train_limpio), test_dorado, "LIMPIO")

    train_env = envenenar(train_limpio, tasa=tasa, semilla=7)
    m_env = evaluar(entrenar_modelo(train_env), test_dorado, "ENVENENADO")

    sospechoso, reporte = detectar_envenenamiento(train_env, ref)
    md = metricas_deteccion(train_env, sospechoso)
    train_saneado = limpiar_dataset(train_env, sospechoso)
    m_rec = evaluar(entrenar_modelo(train_saneado), test_dorado, "RECUPERADO")

    return m_limpio, m_env, m_rec, reporte, md, train_env, ref


if correr or tasa:
    m_limpio, m_env, m_rec, reporte, md, train_env, ref = pipeline(tasa)

    st.subheader("📊 Impacto en el RECALL (peligrosos detectados)")
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Modelo LIMPIO", f"{m_limpio['recall_riesgo']:.0%}",
              help="Línea base de confianza")
    c2.metric("🔴 Modelo ENVENENADO", f"{m_env['recall_riesgo']:.0%}",
              delta=f"{(m_env['recall_riesgo']-m_limpio['recall_riesgo'])*100:.0f} pts",
              delta_color="inverse")
    c3.metric("🛡️ Modelo RECUPERADO", f"{m_rec['recall_riesgo']:.0%}",
              delta=f"{(m_rec['recall_riesgo']-m_env['recall_riesgo'])*100:+.0f} pts")

    chart_df = pd.DataFrame({
        "Escenario": ["Limpio", "Envenenado", "Recuperado"],
        "Recall (%)": [m_limpio["recall_riesgo"]*100,
                       m_env["recall_riesgo"]*100,
                       m_rec["recall_riesgo"]*100],
    }).set_index("Escenario")
    st.bar_chart(chart_df, color="#2E86DE")

    st.subheader("⚠️ Establecimientos peligrosos que NO serían inspeccionados")
    peligro_df = pd.DataFrame({
        "Escenario": ["Limpio", "Envenenado", "Recuperado"],
        "Peligrosos no detectados": [m_limpio["peligrosos_no_detectados"],
                                     m_env["peligrosos_no_detectados"],
                                     m_rec["peligrosos_no_detectados"]],
    }).set_index("Escenario")
    st.bar_chart(peligro_df, color="#E74C3C")

    st.subheader("🔎 Eficacia del sistema de defensa")
    if md:
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Veneno inyectado", md["veneno_total"])
        d2.metric("Veneno detectado", md["veneno_detectado"],
                  delta=f"{md['recall_defensa']:.0%} del ataque")
        d3.metric("Precisión detección", f"{md['precision_defensa']:.0%}")
        d4.metric("En cuarentena", reporte["sospechosos_final"])

    st.info("💡 Sube la intensidad del ataque en la barra lateral y observa cómo "
            "la defensa sigue conteniendo el daño.")

    st.subheader("🗂️ Registros en cuarentena (con razón de detección)")
    cuarentena_df = registros_en_cuarentena_con_razon(train_env, ref)
    st.caption(f"{len(cuarentena_df)} registros aislados en esta corrida.")
    st.dataframe(cuarentena_df, use_container_width=True)
else:
    st.info("👈 Ajusta los parámetros y presiona **Ejecutar simulación**.")

st.markdown("---")
st.subheader("📈 Robustez: ¿la defensa depende de un solo run con suerte?")
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
    chart_robustez = resumen.set_index("tasa_ataque")[
        ["recall_recuperado_pct_media", "pct_veneno_detectado_media"]
    ].rename(columns={
        "recall_recuperado_pct_media": "% desempeño recuperado",
        "pct_veneno_detectado_media": "% veneno detectado",
    })
    st.line_chart(chart_robustez)
    st.dataframe(
        resumen.rename(columns={
            "tasa_ataque": "Tasa de ataque",
            "recall_recuperado_pct_media": "Recuperado (media)",
            "recall_recuperado_pct_std": "Recuperado (std)",
            "pct_veneno_detectado_media": "Veneno detectado (media)",
            "pct_veneno_detectado_std": "Veneno detectado (std)",
        }),
        use_container_width=True,
    )
    st.caption("Los datos completos (20 filas, una por corrida) se guardan en "
              "`results/robustez_resultados.csv` al correr `python src/robustez.py`.")
