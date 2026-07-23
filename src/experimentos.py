"""
experimentos.py
===============
Genera las GRÁFICAS para la presentación (carpeta figuras/). Dos figuras:

  1. robustez.png  — Curva de robustez: recall del modelo SIN defensa vs. CON
     defensa, a medida que sube la intensidad del ataque (0% a 40%). Demuestra
     que la defensa degrada con gracia: aguanta el envenenamiento.

  2. resumen.png   — Barras del recall en los 3 escenarios (limpio, envenenado,
     recuperado) + peligrosos no detectados.

Ejecutar:  python src/experimentos.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")   # backend sin ventana, para guardar PNG
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))

from generar_datos import generar_datos
from modelo import entrenar_modelo, evaluar
from gobernanza import firmar_dataset
from ataque_poisoning import envenenar
from defensa import (detectar_envenenamiento, limpiar_dataset,
                     entrenar_modelo_referencia)

FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "figuras")

# Paleta
AZUL, ROJO, VERDE, GRIS = "#2E86DE", "#E74C3C", "#27AE60", "#7F8C8D"


def _preparar():
    datos = generar_datos(n=3000, semilla=42)
    semilla_conf = datos.iloc[:400].copy()
    train = firmar_dataset(datos.iloc[400:2400].copy())
    test = datos.iloc[2400:].copy()
    ref = entrenar_modelo_referencia(semilla_conf)
    return train, test, ref


def curva_robustez():
    """Recall sin defensa vs. con defensa a distintas intensidades de ataque."""
    train, test, ref = _preparar()
    intensidades = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    recall_indefenso, recall_defendido = [], []

    for tasa in intensidades:
        if tasa == 0.0:
            m0 = evaluar(entrenar_modelo(train), test)
            recall_indefenso.append(m0["recall_riesgo"] * 100)
            recall_defendido.append(m0["recall_riesgo"] * 100)
            continue
        env = envenenar(train, tasa=tasa, semilla=7)
        # Sin defensa
        m_env = evaluar(entrenar_modelo(env), test)
        recall_indefenso.append(m_env["recall_riesgo"] * 100)
        # Con defensa (Capa 1 + Capa 2 + reentrenamiento)
        sospechoso, _ = detectar_envenenamiento(env, ref)
        m_def = evaluar(entrenar_modelo(limpiar_dataset(env, sospechoso)), test)
        recall_defendido.append(m_def["recall_riesgo"] * 100)

    x = [i * 100 for i in intensidades]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, recall_defendido, "-o", color=VERDE, linewidth=2.5,
            label="CON defensa (nuestro sistema)", zorder=3)
    ax.plot(x, recall_indefenso, "-o", color=ROJO, linewidth=2.5,
            label="SIN defensa (modelo desprotegido)", zorder=2)
    ax.fill_between(x, recall_indefenso, recall_defendido, color=VERDE,
                    alpha=0.10, zorder=1)
    ax.axhline(60, color=GRIS, linestyle="--", linewidth=1,
               label="Umbral mínimo del gate de despliegue (60%)")

    ax.set_title("Robustez de la defensa ante el envenenamiento",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Intensidad del ataque (% del pipeline envenenado)")
    ax.set_ylabel("Recall sobre alto riesgo (%)")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()

    os.makedirs(FIG_DIR, exist_ok=True)
    ruta = os.path.join(FIG_DIR, "robustez.png")
    fig.savefig(ruta, dpi=130)
    plt.close(fig)
    return ruta, recall_indefenso, recall_defendido


def barras_resumen():
    """Recall y peligrosos no detectados en los 3 escenarios (ataque al 15%)."""
    train, test, ref = _preparar()
    m_limpio = evaluar(entrenar_modelo(train), test)
    env = envenenar(train, tasa=0.15, semilla=7)
    m_env = evaluar(entrenar_modelo(env), test)
    sospechoso, _ = detectar_envenenamiento(env, ref)
    m_rec = evaluar(entrenar_modelo(limpiar_dataset(env, sospechoso)), test)

    escenarios = ["Limpio", "Envenenado", "Recuperado"]
    recalls = [m_limpio["recall_riesgo"] * 100, m_env["recall_riesgo"] * 100,
               m_rec["recall_riesgo"] * 100]
    peligros = [m_limpio["peligrosos_no_detectados"],
                m_env["peligrosos_no_detectados"],
                m_rec["peligrosos_no_detectados"]]
    colores = [AZUL, ROJO, VERDE]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

    b1 = ax1.bar(escenarios, recalls, color=colores)
    ax1.set_title("Recall sobre alto riesgo (%)", fontweight="bold")
    ax1.set_ylim(0, 100)
    ax1.bar_label(b1, fmt="%.1f%%", fontweight="bold")
    ax1.grid(True, axis="y", alpha=0.3)

    b2 = ax2.bar(escenarios, peligros, color=colores)
    ax2.set_title("Establecimientos peligrosos NO inspeccionados",
                  fontweight="bold")
    ax2.bar_label(b2, fmt="%d", fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Ataque de Data Poisoning vs. Sistema de Defensa (ataque al 15%)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()

    os.makedirs(FIG_DIR, exist_ok=True)
    ruta = os.path.join(FIG_DIR, "resumen.png")
    fig.savefig(ruta, dpi=130)
    plt.close(fig)
    return ruta


if __name__ == "__main__":
    print("Generando gráficas para la presentación...")
    ruta1, indef, defen = curva_robustez()
    print(f"  ✓ {ruta1}")
    print(f"    Sin defensa (0→40%): {indef[0]:.0f}% → {indef[-1]:.0f}% recall")
    print(f"    Con defensa (0→40%): {defen[0]:.0f}% → {defen[-1]:.0f}% recall")
    ruta2 = barras_resumen()
    print(f"  ✓ {ruta2}")
    print("Listo. Usa estas imágenes en las diapositivas.")
