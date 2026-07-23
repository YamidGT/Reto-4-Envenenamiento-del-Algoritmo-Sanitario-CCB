"""
robustez.py
============
Evidencia cuantitativa de que la defensa NO depende de un solo run con suerte.

Corre el pipeline completo (envenenar -> entrenar -> detectar -> reentrenar)
para varias intensidades de ataque y varias semillas, y guarda los resultados
en un DataFrame/CSV para poder graficar recall recuperado vs. intensidad del
ataque en el dashboard.

Ejecutar:  python src/robustez.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from generar_datos import generar_datos
from modelo import entrenar_modelo, evaluar
from gobernanza import firmar_dataset, verificar_dataset
from ataque_poisoning import envenenar
from defensa import (
    detectar_envenenamiento, metricas_deteccion, limpiar_dataset,
    entrenar_modelo_referencia, deteccion_por_referencia,
    deteccion_por_reglas, deteccion_por_anomalias, gate_despliegue,
)

TASAS_DEFECTO = (0.05, 0.15, 0.25, 0.35)
SEMILLAS_DEFECTO = tuple(range(1, 6))  # 5 semillas por tasa
RUTA_CSV_DEFECTO = os.path.join(
    os.path.dirname(__file__), "..", "results", "robustez_resultados.csv"
)


def correr_experimento(tasa, semilla, datos):
    """Corre el pipeline completo UNA vez con una tasa de ataque y semilla dadas.

    La "verdad de campo" (datos) es fija entre experimentos; lo que varía es
    la aleatoriedad del ataque y del entrenamiento, para medir si la defensa
    es consistente o si depende de un golpe de suerte puntual.
    """
    semilla_confianza = datos.iloc[:400].copy()
    train_firmado = firmar_dataset(datos.iloc[400:2400].copy())
    test_dorado = datos.iloc[2400:].copy()

    ref = entrenar_modelo_referencia(semilla_confianza, semilla=semilla)

    m_limpio = evaluar(entrenar_modelo(train_firmado, semilla=semilla), test_dorado)

    train_env = envenenar(train_firmado, tasa=tasa, semilla=semilla)
    m_env = evaluar(entrenar_modelo(train_env, semilla=semilla), test_dorado)

    sospechoso, reporte = detectar_envenenamiento(train_env, ref)
    md = metricas_deteccion(train_env, sospechoso)

    train_saneado = limpiar_dataset(train_env, sospechoso)
    m_rec = evaluar(entrenar_modelo(train_saneado, semilla=semilla), test_dorado)

    caida = m_limpio["recall_riesgo"] - m_env["recall_riesgo"]
    recuperado_pct = (
        (m_rec["recall_riesgo"] - m_env["recall_riesgo"]) / caida
        if caida > 1e-9 else np.nan
    )

    gate_env_ok, _ = gate_despliegue(m_env, metricas_referencia=m_limpio)
    gate_rec_ok, _ = gate_despliegue(m_rec, metricas_referencia=m_limpio)

    return {
        "tasa_ataque": tasa,
        "semilla": semilla,
        "recall_limpio": m_limpio["recall_riesgo"],
        "recall_envenenado": m_env["recall_riesgo"],
        "recall_recuperado": m_rec["recall_riesgo"],
        "caida_recall_pts": caida * 100,
        "recall_recuperado_pct": recuperado_pct,
        "veneno_total": md["veneno_total"] if md else None,
        "veneno_detectado": md["veneno_detectado"] if md else None,
        "pct_veneno_detectado": md["recall_defensa"] if md else None,
        "precision_defensa": md["precision_defensa"] if md else None,
        "falsas_alarmas": md["falsas_alarmas"] if md else None,
        "sospechosos_final": reporte["sospechosos_final"],
        "gate_bloquea_envenenado": not gate_env_ok,
        "gate_aprueba_recuperado": gate_rec_ok,
    }


def correr_barrido(tasas=TASAS_DEFECTO, semillas=SEMILLAS_DEFECTO, n=3000,
                   semilla_datos=42):
    """Corre `correr_experimento` para cada combinación (tasa, semilla) y
    devuelve un DataFrame con una fila por corrida."""
    datos = generar_datos(n=n, semilla=semilla_datos)
    filas = [
        correr_experimento(tasa, semilla, datos)
        for tasa in tasas
        for semilla in semillas
    ]
    return pd.DataFrame(filas)


def resumen_por_tasa(df_resultados):
    """Agrega el barrido por tasa de ataque: media y desviación estándar de
    las métricas clave, para mostrar que la defensa es estable entre semillas."""
    return (
        df_resultados
        .groupby("tasa_ataque")
        .agg(
            recall_recuperado_pct_media=("recall_recuperado_pct", "mean"),
            recall_recuperado_pct_std=("recall_recuperado_pct", "std"),
            pct_veneno_detectado_media=("pct_veneno_detectado", "mean"),
            pct_veneno_detectado_std=("pct_veneno_detectado", "std"),
            precision_defensa_media=("precision_defensa", "mean"),
            recall_envenenado_media=("recall_envenenado", "mean"),
            recall_recuperado_media=("recall_recuperado", "mean"),
        )
        .reset_index()
    )


def registros_en_cuarentena_con_razon(df, modelo_referencia):
    """Devuelve el subconjunto en cuarentena con la razón (qué detector lo
    marcó), para el dashboard: transparencia de por qué se aisló cada dato."""
    if "firma" in df.columns:
        firma_valida = verificar_dataset(df)
    else:
        firma_valida = np.ones(len(df), dtype=bool)
    s_firma = ~firma_valida

    s_ref = deteccion_por_referencia(df, modelo_referencia) & firma_valida
    s_reglas = deteccion_por_reglas(df) & firma_valida
    s_anomalias = deteccion_por_anomalias(df) & firma_valida
    sospechoso = s_firma | s_ref | s_reglas | (s_anomalias & (s_ref | s_reglas))

    razones = []
    for firma_i, ref_i, reglas_i, anom_i in zip(s_firma, s_ref, s_reglas, s_anomalias):
        motivos = []
        if firma_i:
            motivos.append("firma inválida (capa 1)")
        if ref_i:
            motivos.append("verdad de campo (referencia)")
        if reglas_i:
            motivos.append("reglas de dominio")
        if anom_i:
            motivos.append("anomalía")
        razones.append(" + ".join(motivos) if motivos else "")

    salida = df.loc[sospechoso, ["id_establecimiento", "tipo", "localidad",
                                  "riesgo_alto"]].copy()
    salida["razon_deteccion"] = pd.Series(razones, index=df.index)[sospechoso]
    return salida.reset_index(drop=True)


def guardar_csv(df, ruta=RUTA_CSV_DEFECTO):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    df.to_csv(ruta, index=False)
    return ruta


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"Corriendo {len(TASAS_DEFECTO)} tasas x {len(SEMILLAS_DEFECTO)} "
          f"semillas = {len(TASAS_DEFECTO) * len(SEMILLAS_DEFECTO)} experimentos...")
    df_resultados = correr_barrido()
    ruta = guardar_csv(df_resultados)
    print(f"Resultados guardados en: {ruta}")

    print("\nResumen por intensidad de ataque (media +/- std entre semillas):")
    resumen = resumen_por_tasa(df_resultados)
    for _, fila in resumen.iterrows():
        print(
            f"  tasa={fila['tasa_ataque']:.2f}  "
            f"veneno_detectado={fila['pct_veneno_detectado_media']:.0%} "
            f"(+/-{fila['pct_veneno_detectado_std']:.0%})  "
            f"recall_recuperado={fila['recall_recuperado_pct_media']:.0%} "
            f"(+/-{fila['recall_recuperado_pct_std']:.0%})"
        )
