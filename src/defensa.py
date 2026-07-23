"""
defensa.py
==========
SISTEMA DE DEFENSA CONTRA DATA POISONING — el corazón de la solución.

En vez de confiar ciegamente en los datos que llegan al pipeline, aplicamos
DEFENSA EN PROFUNDIDAD. Este módulo implementa la CAPA 2 (detección) y la
CAPA 3 (entrenamiento robusto) del sistema. Las capas 1 (gobernanza del dato)
y 4 (monitoreo) se describen en docs/ESTRATEGIA.md.

Técnicas implementadas:

  A) Detección por reglas de coherencia (verdad de campo):
     Un establecimiento con muchas violaciones/quejas y mala higiene NO puede
     estar etiquetado como "seguro". Contradicción = candidato a envenenamiento.

  B) Detección de anomalías con Isolation Forest:
     Los registros inyectados forman un patrón atípico; el modelo de anomalías
     los aísla sin necesidad de conocer las etiquetas.

  C) Detección por influencia / limpieza tipo "voto del vecindario":
     Un modelo entrenado por validación cruzada marca como sospechosas las
     etiquetas que contradicen sistemáticamente lo que predicen sus vecinos.

  D) Entrenamiento robusto:
     Reentrenamos el modelo EXCLUYENDO los registros marcados como sospechosos,
     recuperando el desempeño original.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.ensemble import RandomForestClassifier

from generar_datos import FEATURES


# ---------------------------------------------------------------------------
# A) Reglas de coherencia con la "verdad de campo"
# ---------------------------------------------------------------------------
def deteccion_por_reglas(df):
    """Marca como sospechosos los registros etiquetados 'seguro' que tienen un
    perfil objetivamente peligroso. Es una red de seguridad basada en dominio
    experto (los inspectores sanitarios) — no depende del modelo."""
    perfil_peligroso = (
        (df["violaciones_previas"] >= 5) |
        (df["quejas_ciudadanas"] >= 6) |
        (df["temp_refrigeracion_c"] >= 12) |
        (df["indice_higiene"] <= 40)
    )
    # Contradicción: perfil peligroso PERO etiquetado como seguro (0)
    sospechoso = perfil_peligroso & (df["riesgo_alto"] == 0)
    return sospechoso.to_numpy()


# ---------------------------------------------------------------------------
# B) Detección de anomalías (Isolation Forest)
# ---------------------------------------------------------------------------
def deteccion_por_anomalias(df, contaminacion=0.12, semilla=42):
    """Detecta registros estadísticamente atípicos en el espacio de variables."""
    X = df[FEATURES]
    iso = IsolationForest(
        n_estimators=200, contamination=contaminacion, random_state=semilla
    )
    pred = iso.fit_predict(X)          # -1 = anomalía, 1 = normal
    return (pred == -1)


# ---------------------------------------------------------------------------
# C) Detección por MODELO DE REFERENCIA ("conjunto semilla de confianza")
# ---------------------------------------------------------------------------
def entrenar_modelo_referencia(df_confianza, semilla=42):
    """Entrena un modelo de referencia sobre un conjunto pequeño de inspecciones
    VERIFICADAS EN CAMPO por inspectores humanos (la 'semilla de confianza').

    Este conjunto está protegido criptográficamente (ver CAPA 1 en la estrategia)
    y NUNCA pasa por el pipeline vulnerable, así que no puede ser envenenado.
    Es nuestra 'brújula de la verdad'."""
    X = df_confianza[FEATURES]
    y = df_confianza["riesgo_alto"]
    ref = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=semilla, n_jobs=-1
    )
    ref.fit(X, y)
    return ref


def deteccion_por_referencia(df, modelo_referencia, umbral=0.6):
    """Marca los registros etiquetados 'seguro' (0) que el modelo de referencia
    —entrenado con verdad de campo íntegra— considera PELIGROSOS con alta
    confianza. Aquí es donde caen los 'label flips': aunque el atacante cambió
    la etiqueta, las variables siguen delatando el riesgo real."""
    X = df[FEATURES]
    proba_riesgo = modelo_referencia.predict_proba(X)[:, 1]
    sospechoso = (df["riesgo_alto"].to_numpy() == 0) & (proba_riesgo > umbral)
    return sospechoso


# ---------------------------------------------------------------------------
# Orquestador de detección: combina las señales
# ---------------------------------------------------------------------------
def detectar_envenenamiento(df, modelo_referencia):
    """Combina las tres señales de detección:

      • Modelo de referencia (verdad de campo) -> señal PRIMARIA, caza label-flips.
      • Reglas de coherencia (dominio experto)  -> señal PRIMARIA, caza inyecciones.
      • Anomalías (Isolation Forest)            -> señal de REFUERZO.

    Un registro entra en cuarentena si lo marca cualquiera de las dos señales
    primarias, o si la señal de anomalías coincide con alguna primaria.
    """
    s_ref       = deteccion_por_referencia(df, modelo_referencia)
    s_reglas    = deteccion_por_reglas(df)
    s_anomalias = deteccion_por_anomalias(df)

    sospechoso = s_ref | s_reglas | (s_anomalias & (s_ref | s_reglas))

    reporte = {
        "por_referencia": int(s_ref.sum()),
        "por_reglas": int(s_reglas.sum()),
        "por_anomalias": int(s_anomalias.sum()),
        "sospechosos_final": int(sospechoso.sum()),
    }
    return sospechoso, reporte


def metricas_deteccion(df, sospechoso):
    """Si el dataframe trae la marca oculta `_envenenado`, medimos qué tan bien
    detectamos el ataque (precision/recall de la DEFENSA)."""
    if "_envenenado" not in df.columns:
        return None
    real = df["_envenenado"].to_numpy().astype(bool)
    tp = int((sospechoso & real).sum())
    fp = int((sospechoso & ~real).sum())
    fn = int((~sospechoso & real).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "veneno_total": int(real.sum()),
        "veneno_detectado": tp,
        "falsas_alarmas": fp,
        "veneno_no_detectado": fn,
        "precision_defensa": precision,
        "recall_defensa": recall,
    }


# ---------------------------------------------------------------------------
# D) Entrenamiento robusto: reentrenar sin los registros sospechosos
# ---------------------------------------------------------------------------
def limpiar_dataset(df, sospechoso):
    """Devuelve el dataset saneado (sin los registros marcados)."""
    return df.loc[~sospechoso].reset_index(drop=True)
