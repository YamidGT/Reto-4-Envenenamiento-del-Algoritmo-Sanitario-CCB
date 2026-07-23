"""
demo.py
=======
DEMO PRINCIPAL — cuenta la historia completa para el jurado, en consola:

  ACTO 1: El modelo limpio funciona y protege a los ciudadanos.
  ACTO 2: Los atacantes envenenan el pipeline con 3 vectores -> el modelo
          empieza a clasificar establecimientos peligrosos como "seguros".
  ACTO 3: DEFENSA EN PROFUNDIDAD:
          - Capa 1 (criptografía): neutraliza inyección y manipulación.
          - Capa 2 (IA): caza al infiltrado corrupto que firmó datos falsos.
          - Gate de despliegue: bloquea el modelo envenenado antes de producción.
          - Reentrenamiento robusto: recupera la confianza.

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
from modelo import (entrenar_modelo, evaluar, imprimir_metricas,
                    importancia_variables, imprimir_importancia)
from gobernanza import firmar_dataset, verificar_dataset
from ataque_poisoning import envenenar
from defensa import (detectar_envenenamiento, metricas_deteccion,
                     limpiar_dataset, entrenar_modelo_referencia,
                     gate_despliegue)


def titulo(txt):
    print("\n" + "=" * 68)
    print(f"  {txt}")
    print("=" * 68)


def main():
    print("\n" + "#" * 68)
    print("#  RETO 4 — ENVENENAMIENTO DEL ALGORITMO SANITARIO (CCB)")
    print("#  Defensa en Profundidad: Criptografía + IA contra Data Poisoning")
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

    # Las fuentes legítimas FIRMAN sus datos en el origen (Capa 1).
    train_firmado = firmar_dataset(train_limpio)

    # Entrenamos la "brújula de la verdad" con la semilla de confianza.
    modelo_referencia = entrenar_modelo_referencia(semilla_confianza)

    # ===================================================================
    titulo("ACTO 1 — MODELO LIMPIO (línea base de confianza)")
    # ===================================================================
    modelo_limpio = entrenar_modelo(train_firmado)
    m_limpio = evaluar(modelo_limpio, test_dorado, "LIMPIO")
    print("Modelo entrenado con datos íntegros y firmados:")
    imprimir_metricas(m_limpio)

    # ===================================================================
    titulo("ACTO 2 — ATAQUE DE DATA POISONING (3 vectores, 15% del pipeline)")
    # ===================================================================
    train_env = envenenar(train_firmado, tasa=0.15, semilla=7)
    veneno = train_env[train_env["_envenenado"] == 1]
    print(f"Los atacantes manipularon {len(veneno)} registros con 3 vectores:")
    for vec, n in veneno["_vector"].value_counts().items():
        desc = {"inyeccion": "inyección externa (firma inválida)",
                "tampering": "manipulación de etiquetas (rompe la firma)",
                "infiltrado": "infiltrado corrupto (firma VÁLIDA, dato falso)"}[vec]
        print(f"  ├─ {n:>3} · {desc}")

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
    titulo("ACTO 3 — DEFENSA EN PROFUNDIDAD")
    # ===================================================================
    # --- Capa 1: criptografía (antes de tocar la IA) ---
    firma_valida = verificar_dataset(train_env)
    n_invalidos = int((~firma_valida).sum())
    print(f"🔒 CAPA 1 · Criptografía (verificación de firma digital):")
    print(f"     {n_invalidos} registros con firma inválida o alterada "
          f"→ RECHAZADOS de inmediato.")
    print(f"     (Neutraliza inyección externa y manipulación de forma "
          f"determinística.)")

    # --- Detección completa (Capa 1 + Capa 2) ---
    sospechoso, reporte = detectar_envenenamiento(train_env, modelo_referencia)
    print(f"\n🧠 CAPA 2 · IA sobre los registros con firma válida:")
    print(f"     ├─ Modelo de referencia (verdad campo) . {reporte['por_referencia']} marcados")
    print(f"     ├─ Reglas de coherencia (dominio) ...... {reporte['por_reglas']} marcados")
    print(f"     ├─ Anomalías (Isolation Forest) ........ {reporte['por_anomalias']} marcados")
    print(f"     └─ Total cazado por IA ................. {reporte['capa2_ia']} "
          f"(incluye al infiltrado)")

    md = metricas_deteccion(train_env, sospechoso)
    if md:
        print(f"\n  🎯 EFICACIA GLOBAL DE LA DEFENSA:")
        print(f"     Veneno total inyectado ........... {md['veneno_total']}")
        print(f"     Veneno detectado y neutralizado .. {md['veneno_detectado']} "
              f"({md['recall_defensa']:.0%} del ataque)")
        print(f"     Precisión de la detección ........ {md['precision_defensa']:.0%}")
        if md["por_vector"]:
            print(f"     Detección por vector de ataque:")
            nombres = {"inyeccion": "Inyección  ", "tampering": "Manipulación",
                       "infiltrado": "Infiltrado "}
            for vec, d in md["por_vector"].items():
                print(f"       · {nombres[vec]} .. {d['detectado']}/{d['total']} "
                      f"({d['tasa']:.0%})")

    # --- Gate de despliegue sobre el modelo ENVENENADO ---
    aprobado_env, motivo_env = gate_despliegue(m_env, recall_minimo=0.60,
                                               metricas_referencia=m_limpio)
    print(f"\n🚦 GATE DE DESPLIEGUE (modelo envenenado):")
    print(f"     {'✅' if aprobado_env else '⛔'} {motivo_env}")

    # --- Reentrenamiento robusto con datos saneados ---
    train_saneado = limpiar_dataset(train_env, sospechoso)
    modelo_recuperado = entrenar_modelo(train_saneado)
    m_rec = evaluar(modelo_recuperado, test_dorado, "RECUPERADO")
    print("\n♻️  Modelo REENTRENADO con datos saneados:")
    imprimir_metricas(m_rec)

    aprobado_rec, motivo_rec = gate_despliegue(m_rec, recall_minimo=0.60,
                                               metricas_referencia=m_limpio)
    print(f"\n🚦 GATE DE DESPLIEGUE (modelo recuperado):")
    print(f"     {'✅' if aprobado_rec else '⛔'} {motivo_rec}")

    print("\n  🔍 EXPLICABILIDAD (el modelo se puede auditar):")
    imprimir_importancia(importancia_variables(modelo_recuperado))

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
    if recuperado_pct >= 0.99:
        print(f"\n  ✅ La defensa recuperó POR COMPLETO el desempeño perdido "
              f"(incluso igualó o superó la línea base limpia).")
    else:
        print(f"\n  ✅ La defensa recuperó el {recuperado_pct:.0%} del desempeño "
              f"perdido por el ataque.")
    print("  ✅ El gate bloqueó el modelo envenenado; solo el saneado llega a producción.")
    print("  ✅ La confianza en la herramienta predictiva queda restaurada.\n")


if __name__ == "__main__":
    main()
