"""
demo.py
=======
DEMO PRINCIPAL — cuenta la historia completa para el jurado, en consola:

  ACTO 1: El modelo limpio funciona y protege a los ciudadanos.
  ACTO 2: Los atacantes envenenan el pipeline -> el modelo empieza a
          clasificar establecimientos peligrosos como "seguros".
  ACTO 3: Nuestro sistema de defensa detecta el envenenamiento, limpia los
          datos y RECUPERA la confianza del modelo.

Ejecutar:  python src/demo.py
"""

import os
import sys

# La consola de Windows por defecto usa cp1252 y no soporta Unicode/emoji.
# Forzamos UTF-8 para que el reporte se vea correcto en cualquier sistema.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))

from generar_datos import generar_datos
from modelo import entrenar_modelo, evaluar, imprimir_metricas
from ataque_poisoning import envenenar
from defensa import (detectar_envenenamiento, metricas_deteccion,
                     limpiar_dataset, entrenar_modelo_referencia)


def titulo(txt):
    print("\n" + "=" * 68)
    print(f"  {txt}")
    print("=" * 68)


def main():
    print("\n" + "#" * 68)
    print("#  RETO 4 — ENVENENAMIENTO DEL ALGORITMO SANITARIO (CCB)")
    print("#  Demostración: Ataque de Data Poisoning vs. Sistema de Defensa")
    print("#" * 68)

    # --- Datos: verdad de campo, dividida en 3 conjuntos ---
    datos = generar_datos(n=3000, semilla=42)
    # 1) SEMILLA DE CONFIANZA: inspecciones verificadas en campo por humanos.
    #    Protegida criptográficamente, NUNCA pasa por el pipeline vulnerable.
    semilla_confianza = datos.iloc[:400].copy()
    # 2) POOL DE ENTRENAMIENTO: llega por el pipeline -> es el que se envenena.
    train_limpio = datos.iloc[400:2400].copy()
    # 3) CONJUNTO DORADO DE EVALUACIÓN: verificado, mide la confianza real.
    test_dorado = datos.iloc[2400:].copy()

    # Entrenamos la "brújula de la verdad" con la semilla de confianza.
    modelo_referencia = entrenar_modelo_referencia(semilla_confianza)

    # ===================================================================
    titulo("ACTO 1 — MODELO LIMPIO (línea base de confianza)")
    # ===================================================================
    modelo_limpio = entrenar_modelo(train_limpio)
    m_limpio = evaluar(modelo_limpio, test_dorado, "LIMPIO")
    print("Modelo entrenado con datos íntegros:")
    imprimir_metricas(m_limpio)

    # ===================================================================
    titulo("ACTO 2 — ATAQUE DE DATA POISONING (15% del pipeline)")
    # ===================================================================
    train_env = envenenar(train_limpio, tasa=0.15, semilla=7)
    print(f"Los atacantes manipularon {int(train_env['_envenenado'].sum())} de "
          f"{len(train_env)} registros:")
    print("  ├─ Cambiaron etiquetas de establecimientos peligrosos a 'seguro'")
    print("  └─ Inyectaron establecimientos ficticios insalubres como 'seguros'")

    modelo_env = entrenar_modelo(train_env)
    m_env = evaluar(modelo_env, test_dorado, "ENVENENADO")
    print("\nModelo entrenado con datos ENVENENADOS:")
    imprimir_metricas(m_env)

    caida = m_limpio["recall_riesgo"] - m_env["recall_riesgo"]
    extra = m_env["peligrosos_no_detectados"] - m_limpio["peligrosos_no_detectados"]
    print(f"\n  💥 IMPACTO DEL ATAQUE:")
    print(f"     El RECALL cayó {caida*100:.1f} puntos porcentuales.")
    print(f"     {extra} establecimientos peligrosos ADICIONALES pasarían "
          f"como 'seguros'")
    print(f"     y NO serían inspeccionados. Riesgo directo para la salud pública.")

    # ===================================================================
    titulo("ACTO 3 — SISTEMA DE DEFENSA (detección + limpieza)")
    # ===================================================================
    sospechoso, reporte = detectar_envenenamiento(train_env, modelo_referencia)
    print("Señales de detección (defensa en profundidad):")
    print(f"  ├─ Modelo de referencia (verdad campo) . {reporte['por_referencia']} marcados")
    print(f"  ├─ Reglas de coherencia (dominio) ...... {reporte['por_reglas']} marcados")
    print(f"  ├─ Anomalías (Isolation Forest) ........ {reporte['por_anomalias']} marcados")
    print(f"  └─ CUARENTENA (consolidado) ............ {reporte['sospechosos_final']} "
          f"registros")

    md = metricas_deteccion(train_env, sospechoso)
    if md:
        print(f"\n  🎯 EFICACIA DE LA DEFENSA:")
        print(f"     Veneno real inyectado ............ {md['veneno_total']}")
        print(f"     Veneno detectado y neutralizado .. {md['veneno_detectado']} "
              f"({md['recall_defensa']:.0%} del ataque)")
        print(f"     Precisión de la detección ........ {md['precision_defensa']:.0%}")
        print(f"     Falsas alarmas ................... {md['falsas_alarmas']}")

    # Reentrenar con el dataset saneado
    train_saneado = limpiar_dataset(train_env, sospechoso)
    modelo_recuperado = entrenar_modelo(train_saneado)
    m_rec = evaluar(modelo_recuperado, test_dorado, "RECUPERADO")
    print("\nModelo REENTRENADO con datos saneados:")
    imprimir_metricas(m_rec)

    # ===================================================================
    titulo("RESUMEN EJECUTIVO — Recall sobre alto riesgo (métrica crítica)")
    # ===================================================================
    print(f"  Modelo LIMPIO ........ {m_limpio['recall_riesgo']:.1%}   "
          f"(peligrosos no detectados: {m_limpio['peligrosos_no_detectados']})")
    print(f"  Modelo ENVENENADO .... {m_env['recall_riesgo']:.1%}   "
          f"(peligrosos no detectados: {m_env['peligrosos_no_detectados']})  ⬅ ATAQUE")
    print(f"  Modelo RECUPERADO .... {m_rec['recall_riesgo']:.1%}   "
          f"(peligrosos no detectados: {m_rec['peligrosos_no_detectados']})  ⬅ DEFENSA")

    recuperado_pct = (m_rec["recall_riesgo"] - m_env["recall_riesgo"]) / \
                     max(m_limpio["recall_riesgo"] - m_env["recall_riesgo"], 1e-9)
    print(f"\n  ✅ La defensa recuperó el {recuperado_pct:.0%} del desempeño "
          f"perdido por el ataque.")
    print("  ✅ La confianza en la herramienta predictiva queda restaurada.\n")


if __name__ == "__main__":
    main()
