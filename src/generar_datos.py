"""
generar_datos.py
=================
Genera un dataset sintético REALISTA de establecimientos de alimentos para el
modelo de inspección sanitaria (restaurantes, mataderos, fábricas).

Cada establecimiento tiene variables que un modelo real usaría para predecir el
RIESGO sanitario. La etiqueta objetivo es:

    riesgo_alto = 1  ->  requiere inspección inmediata (INSALUBRE / peligroso)
    riesgo_alto = 0  ->  bajo riesgo (SEGURO)

El riesgo se construye a partir de una "regla de la realidad" (verdad de campo),
que luego usaremos para demostrar cómo el envenenamiento la contradice.
"""

import numpy as np
import pandas as pd

TIPOS = ["restaurante", "matadero", "fabrica_alimentos", "panaderia", "cafeteria"]
LOCALIDADES = ["Kennedy", "Suba", "Engativa", "Bosa", "Chapinero", "Usaquen",
               "Ciudad Bolivar", "Fontibon", "San Cristobal", "Teusaquillo"]


def generar_datos(n=2000, semilla=42):
    """Genera `n` establecimientos con variables predictoras y etiqueta de riesgo."""
    rng = np.random.default_rng(semilla)

    # --- Variables predictoras (features) ---
    quejas_ciudadanas   = rng.poisson(2, n)                      # # de quejas en el último año
    violaciones_previas = rng.poisson(1.5, n)                    # # de violaciones históricas
    dias_ultima_insp    = rng.integers(10, 900, n)               # días desde la última inspección
    temp_refrigeracion  = rng.normal(5, 3, n).round(1)           # °C de cámaras de frío (ideal < 5)
    indice_higiene      = rng.normal(70, 18, n).clip(0, 100)     # score de higiene 0-100
    rotacion_personal   = rng.uniform(0, 1, n).round(2)          # rotación de manipuladores
    volumen_diario_kg   = rng.gamma(2.0, 50, n).round(0)         # kg de alimento manipulado/día
    tipo                = rng.choice(TIPOS, n)
    localidad           = rng.choice(LOCALIDADES, n)

    df = pd.DataFrame({
        "id_establecimiento": [f"EST-{i:05d}" for i in range(n)],
        "tipo": tipo,
        "localidad": localidad,
        "quejas_ciudadanas": quejas_ciudadanas,
        "violaciones_previas": violaciones_previas,
        "dias_desde_ultima_inspeccion": dias_ultima_insp,
        "temp_refrigeracion_c": temp_refrigeracion,
        "indice_higiene": indice_higiene.round(1),
        "rotacion_personal": rotacion_personal,
        "volumen_diario_kg": volumen_diario_kg,
    })

    # --- "Verdad de campo": regla que define el riesgo REAL ---
    # Score de riesgo continuo (a mayor score, más peligroso).
    score = (
        0.9 * df["violaciones_previas"] +
        0.7 * df["quejas_ciudadanas"] +
        0.010 * df["dias_desde_ultima_inspeccion"] +
        0.35 * (df["temp_refrigeracion_c"] - 5).clip(lower=0) +   # frío insuficiente
        0.05 * (70 - df["indice_higiene"]).clip(lower=0) +        # baja higiene
        2.5 * df["rotacion_personal"] +
        0.004 * df["volumen_diario_kg"]
    )
    # Los mataderos y fábricas tienen mayor riesgo intrínseco.
    score += df["tipo"].map({"matadero": 2.0, "fabrica_alimentos": 1.2}).fillna(0)

    # Ruido y umbral -> etiqueta binaria
    score += rng.normal(0, 1.0, n)
    umbral = np.quantile(score, 0.70)   # ~30% de alto riesgo
    df["riesgo_alto"] = (score > umbral).astype(int)
    df["_score_real"] = score.round(3)   # guardado solo para análisis/demostración

    return df


FEATURES = [
    "quejas_ciudadanas", "violaciones_previas", "dias_desde_ultima_inspeccion",
    "temp_refrigeracion_c", "indice_higiene", "rotacion_personal", "volumen_diario_kg",
]


if __name__ == "__main__":
    df = generar_datos()
    print(df.head())
    print(f"\nTotal: {len(df)} establecimientos")
    print(f"Alto riesgo: {df['riesgo_alto'].mean():.1%}")
