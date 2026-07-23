"""
modelo.py
=========
Modelo de riesgo sanitario. Entrena un clasificador que predice si un
establecimiento es de ALTO riesgo (requiere inspección) o de bajo riesgo.

Usamos RandomForest: robusto, interpretable (importancia de variables) y
representativo del tipo de modelo que una Secretaría de Salud usaría.
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

from generar_datos import FEATURES


def entrenar_modelo(df_train, semilla=42):
    """Entrena el modelo de riesgo sobre un dataframe de entrenamiento."""
    X = df_train[FEATURES]
    y = df_train["riesgo_alto"]
    modelo = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=semilla, n_jobs=-1
    )
    modelo.fit(X, y)
    return modelo


def evaluar(modelo, df_test, etiqueta="MODELO"):
    """Evalúa el modelo y devuelve un diccionario de métricas.

    Reportamos el RECALL sobre la clase de alto riesgo como métrica crítica:
    en salud pública, un falso negativo (dejar pasar un establecimiento
    peligroso) es MUCHO más costoso que un falso positivo.
    """
    X = df_test[FEATURES]
    y = df_test["riesgo_alto"]
    pred = modelo.predict(X)

    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    metricas = {
        "etiqueta": etiqueta,
        "accuracy": accuracy_score(y, pred),
        "precision_riesgo": precision_score(y, pred, zero_division=0),
        "recall_riesgo": recall_score(y, pred, zero_division=0),
        "f1_riesgo": f1_score(y, pred, zero_division=0),
        # Peligrosos que el modelo dejó pasar como "seguros":
        "peligrosos_no_detectados": int(fn),
        "peligrosos_detectados": int(tp),
    }
    return metricas


def importancia_variables(modelo):
    """Devuelve la lista de FEATURES ordenada por importancia (mayor a menor)
    según el RandomForest. Es la base de la explicabilidad: qué variables
    pesaron más en la predicción, para poder auditar y defender el modelo."""
    importancias = sorted(
        zip(FEATURES, modelo.feature_importances_),
        key=lambda par: par[1], reverse=True,
    )
    return importancias


def imprimir_importancia(importancias, top=5):
    print(f"  Top {top} variables que más pesan en la predicción:")
    for i, (variable, peso) in enumerate(importancias[:top], start=1):
        print(f"  {i}. {variable} .......... {peso:.1%}")


def imprimir_metricas(m):
    print(f"  ├─ Accuracy .......................... {m['accuracy']:.1%}")
    print(f"  ├─ Precisión (alto riesgo) ........... {m['precision_riesgo']:.1%}")
    print(f"  ├─ RECALL (alto riesgo) 🎯 ........... {m['recall_riesgo']:.1%}")
    print(f"  ├─ F1 (alto riesgo) .................. {m['f1_riesgo']:.1%}")
    print(f"  └─ ⚠️  Peligrosos dejados pasar ...... {m['peligrosos_no_detectados']}")
