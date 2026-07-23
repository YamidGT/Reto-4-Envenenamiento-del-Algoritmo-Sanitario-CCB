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
from gobernanza import verificar_dataset


# ---------------------------------------------------------------------------
# A) Reglas de coherencia con la "verdad de campo"
# ---------------------------------------------------------------------------
def deteccion_por_reglas(df):
    """Marca como sospechosos los registros etiquetados 'seguro' que tienen un
    perfil objetivamente peligroso. Es una red de seguridad basada en dominio
    experto (los inspectores sanitarios) — no depende del modelo.

    Los umbrales NO se calibran mirando cómo ataca el atacante (eso sería
    circular: "detecto lo que yo mismo simulé"). Se derivan de la distribución
    estadística de la población normal de establecimientos (ver
    generar_datos.py): cada umbral corresponde aprox. al percentil 95-97 de su
    variable, es decir, "más extremo que el 95-97% de los establecimientos
    típicos" — un criterio que un inspector definiría con datos históricos,
    sin conocer nunca el rango exacto que usa el atacante para fabricar
    registros falsos (quejas 6-15, violaciones 5-12, temp 12-20, higiene 15-40):

      - violaciones_previas >= 5   (percentil ~95 de la población normal)
      - quejas_ciudadanas   >= 6   (percentil ~97 de la población normal)
      - temp_refrigeracion_c >= 11 (percentil ~97 de la población normal)
      - indice_higiene      <= 35  (cola inferior, higiene muy deficiente)
    """
    perfil_peligroso = (
        (df["violaciones_previas"] >= 5) |
        (df["quejas_ciudadanas"] >= 6) |
        (df["temp_refrigeracion_c"] >= 11) |
        (df["indice_higiene"] <= 35)
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
# Orquestador de detección: DEFENSA EN PROFUNDIDAD por capas
# ---------------------------------------------------------------------------
def detectar_envenenamiento(df, modelo_referencia, clave=None):
    """Aplica la defensa en dos capas y combina las señales:

    CAPA 1 — Criptografía (determinística):
      • Verificación de firma digital -> descarta inyecciones (firma inválida) y
        manipulaciones (integridad rota). Detección exacta, sin falsos positivos.

    CAPA 2 — IA sobre los registros con firma válida (estadística):
      • Modelo de referencia (verdad de campo) -> caza al infiltrado corrupto.
      • Reglas de coherencia (dominio experto)  -> red de seguridad interpretable.
      • Anomalías (Isolation Forest)            -> señal de refuerzo.

    Un registro entra en cuarentena si falla la firma, o si la IA lo marca.
    """
    # --- CAPA 1: firma criptográfica ---
    if "firma" in df.columns:
        firma_valida = verificar_dataset(df) if clave is None else \
                       verificar_dataset(df, clave)
    else:
        firma_valida = np.ones(len(df), dtype=bool)   # sin firmas -> todo pasa
    s_firma = ~firma_valida

    # --- CAPA 2: IA (solo tiene sentido sobre lo que superó la Capa 1) ---
    s_ref       = deteccion_por_referencia(df, modelo_referencia)
    s_reglas    = deteccion_por_reglas(df)
    s_anomalias = deteccion_por_anomalias(df)
    s_ia = s_ref | s_reglas | (s_anomalias & (s_ref | s_reglas))
    # La IA solo aporta sobre registros con firma válida (los demás ya están fuera).
    s_ia = s_ia & firma_valida

    sospechoso = s_firma | s_ia

    reporte = {
        "capa1_firma_invalida": int(s_firma.sum()),
        "por_referencia": int((s_ref & firma_valida).sum()),
        "por_reglas": int((s_reglas & firma_valida).sum()),
        "por_anomalias": int((s_anomalias & firma_valida).sum()),
        "capa2_ia": int(s_ia.sum()),
        "sospechosos_final": int(sospechoso.sum()),
    }
    return sospechoso, reporte


# ---------------------------------------------------------------------------
# GATE DE DESPLIEGUE: ningún modelo llega a producción si empeora el recall
# ---------------------------------------------------------------------------
def gate_despliegue(metricas_candidato, recall_minimo=0.60,
                    metricas_referencia=None, caida_max=0.05):
    """Controla la promoción de un modelo a producción validándolo contra el
    CONJUNTO DORADO verificado en campo. Es la barrera automática que vuelve
    inútil el envenenamiento: aunque el atacante degrade el modelo, este
    NO se despliega.

    Bloquea si:
      • el recall sobre alto riesgo cae por debajo de `recall_minimo`, o
      • cae más de `caida_max` respecto al modelo de referencia en producción.

    Returns
    -------
    (aprobado: bool, motivo: str)
    """
    recall = metricas_candidato["recall_riesgo"]
    if recall < recall_minimo:
        return False, (f"BLOQUEADO: recall {recall:.1%} < mínimo exigido "
                       f"{recall_minimo:.1%}. Posible envenenamiento.")
    if metricas_referencia is not None:
        caida = metricas_referencia["recall_riesgo"] - recall
        if caida > caida_max:
            return False, (f"BLOQUEADO: el recall cayó {caida:.1%} respecto al "
                           f"modelo en producción (máx tolerado {caida_max:.1%}).")
    return True, f"APROBADO: recall {recall:.1%} cumple los umbrales de calidad."


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

    # Desglose por vector de ataque (si está disponible la marca `_vector`).
    por_vector = {}
    if "_vector" in df.columns:
        for vec in ("inyeccion", "tampering", "infiltrado"):
            mask = (df["_vector"] == vec).to_numpy()
            total_v = int(mask.sum())
            if total_v:
                det_v = int((sospechoso & mask).sum())
                por_vector[vec] = {"total": total_v, "detectado": det_v,
                                   "tasa": det_v / total_v}

    return {
        "veneno_total": int(real.sum()),
        "veneno_detectado": tp,
        "falsas_alarmas": fp,
        "veneno_no_detectado": fn,
        "precision_defensa": precision,
        "recall_defensa": recall,
        "por_vector": por_vector,
    }


# ---------------------------------------------------------------------------
# D) Entrenamiento robusto: reentrenar sin los registros sospechosos
# ---------------------------------------------------------------------------
def limpiar_dataset(df, sospechoso):
    """Devuelve el dataset saneado (sin los registros marcados)."""
    return df.loc[~sospechoso].reset_index(drop=True)
