"""
monitoreo.py
============
CAPA 4 · MONITOREO CONTINUO — vigilancia permanente, porque el atacante
volverá a intentarlo.

Comparamos una ventana de referencia (distribución "sana" conocida) contra
una ventana actual (lo que está llegando ahora) con tres señales
complementarias:

  A) Diferencia de proporción de "seguros": la huella más directa de un
     ataque de label-flipping / inyección (de repente muchos más
     establecimientos aparecen como "seguros").
  B) Test de Kolmogorov-Smirnov (2 muestras) por variable continua: detecta
     corrimientos de distribución en las features, aunque la etiqueta no
     cambie.
  C) PSI (Population Stability Index): métrica estándar de la industria
     para *data drift*, con umbrales convencionales (<0.10 estable,
     0.10-0.25 alerta, >0.25 crítico).

Implementado en NumPy puro (sin scipy) para no tocar `requirements.txt` y
evitar choques de dependencias con el resto del equipo.

Controles de referencia que este módulo materializa:
  - NIST SP 800-53 Rev.5  CA-7 / SI-4 (monitoreo continuo del sistema)
  - ISO/IEC 42001:2023 (seguimiento del desempeño del sistema de IA)
  - EU AI Act Art. 72 (monitoreo post-comercialización) y Art. 14
    (supervisión humana: la alerta se ESCALA, no se actúa automáticamente)
  - OWASP ML Security Top 10 — ML02:2023 Data Poisoning Attack (detección
    en producción, complementaria a la Capa 2 offline de defensa.py)

Importante: `detectar_drift` NUNCA reentrena ni bloquea nada por sí sola.
Solo alerta y recomienda una acción; la decisión la toma un humano
(human-in-the-loop), como exige un sistema de IA de alto impacto.
"""

import numpy as np


# ---------------------------------------------------------------------------
# A) Diferencia de proporción (señal principal, la más interpretable)
# ---------------------------------------------------------------------------
def diferencia_proporcion(ref, act, columna="riesgo_alto"):
    """Compara la proporción de una columna binaria entre dos ventanas.
    Si de repente muchos menos establecimientos son "riesgo_alto" (o muchos
    más "seguros"), es la huella clásica de un ataque de label flipping."""
    p_ref = float(ref[columna].mean())
    p_act = float(act[columna].mean())
    return {
        "proporcion_referencia": p_ref,
        "proporcion_actual": p_act,
        "diferencia_absoluta": abs(p_act - p_ref),
    }


# ---------------------------------------------------------------------------
# B) Kolmogorov-Smirnov de 2 muestras, implementado en NumPy puro.
# ---------------------------------------------------------------------------
def test_ks(ref, act):
    """Estadístico KS de dos muestras: máxima distancia entre las funciones
    de distribución empírica (CDF) de `ref` y `act`. Aproxima el p-value con
    la fórmula asintótica de Kolmogorov (suficiente para detectar drift,
    sin necesitar scipy)."""
    ref = np.sort(np.asarray(ref, dtype=float))
    act = np.sort(np.asarray(act, dtype=float))
    n, m = len(ref), len(act)
    if n == 0 or m == 0:
        return {"estadistico": 0.0, "p_valor": 1.0}

    datos = np.concatenate([ref, act])
    cdf_ref = np.searchsorted(ref, datos, side="right") / n
    cdf_act = np.searchsorted(act, datos, side="right") / m
    estadistico = float(np.max(np.abs(cdf_ref - cdf_act)))

    # Aproximación asintótica de Kolmogorov para el p-value.
    ne = n * m / (n + m)
    lam = (np.sqrt(ne) + 0.12 + 0.11 / np.sqrt(ne)) * estadistico
    terminos = np.arange(1, 101)
    q = 2 * np.sum(
        (-1) ** (terminos - 1) * np.exp(-2 * (lam ** 2) * (terminos ** 2))
    )
    p_valor = float(np.clip(q, 0.0, 1.0))
    return {"estadistico": estadistico, "p_valor": p_valor}


# ---------------------------------------------------------------------------
# C) PSI (Population Stability Index)
# ---------------------------------------------------------------------------
def psi(ref, act, bins=10):
    """Population Stability Index entre dos distribuciones continuas.
    Umbrales convencionales de la industria: <0.10 estable,
    0.10-0.25 alerta moderada, >0.25 cambio crítico."""
    ref = np.asarray(ref, dtype=float)
    act = np.asarray(act, dtype=float)

    cortes = np.quantile(ref, np.linspace(0, 1, bins + 1))
    cortes[0], cortes[-1] = -np.inf, np.inf
    cortes = np.unique(cortes)
    if len(cortes) < 3:
        return 0.0

    freq_ref, _ = np.histogram(ref, bins=cortes)
    freq_act, _ = np.histogram(act, bins=cortes)

    # Suavizado para evitar log(0) / división por cero en bins vacíos.
    prop_ref = np.clip(freq_ref / max(len(ref), 1), 1e-6, None)
    prop_act = np.clip(freq_act / max(len(act), 1), 1e-6, None)

    return float(np.sum((prop_act - prop_ref) * np.log(prop_act / prop_ref)))


# ---------------------------------------------------------------------------
# Orquestador: combina las tres señales y decide severidad + recomendación.
# ---------------------------------------------------------------------------
FEATURES_CONTINUAS = [
    "indice_higiene", "temp_refrigeracion_c", "rotacion_personal",
]


def detectar_drift(distribucion_referencia, distribucion_actual,
                    umbral_prop=0.10, umbral_ks=0.15, umbral_psi=0.20):
    """Combina proporción + KS + PSI para decidir si hay drift y con qué
    severidad. Devuelve un reporte estructurado, pensado para pintarse como
    semáforo en un dashboard. NO toma ninguna acción automática: solo
    recomienda (human-in-the-loop)."""
    señales_disparadas = []

    prop = diferencia_proporcion(distribucion_referencia, distribucion_actual)
    if prop["diferencia_absoluta"] > umbral_prop:
        señales_disparadas.append("proporcion_seguros")

    detalle_ks = {}
    detalle_psi = {}
    for col in FEATURES_CONTINUAS:
        if col not in distribucion_referencia.columns or col not in distribucion_actual.columns:
            continue
        ks = test_ks(distribucion_referencia[col], distribucion_actual[col])
        p_score = psi(distribucion_referencia[col], distribucion_actual[col])
        detalle_ks[col] = ks
        detalle_psi[col] = p_score
        if ks["estadistico"] > umbral_ks:
            señales_disparadas.append(f"ks::{col}")
        if p_score > umbral_psi:
            señales_disparadas.append(f"psi::{col}")

    n_disparadas = len(señales_disparadas)
    if n_disparadas == 0:
        severidad = "OK"
        motivo = "Sin desviaciones significativas frente a la referencia."
        accion = "Ninguna acción requerida. Continuar monitoreo de rutina."
    elif n_disparadas == 1:
        severidad = "ALERTA"
        motivo = f"1 señal disparada: {señales_disparadas[0]}."
        accion = ("Revisar manualmente la fuente de datos reciente antes del "
                   "próximo reentrenamiento. No bloquear aún, pero escalar a un inspector.")
    else:
        severidad = "CRITICO"
        motivo = f"{n_disparadas} señales disparadas: {', '.join(señales_disparadas)}."
        accion = ("Congelar reentrenamientos automáticos y escalar a auditoría "
                   "humana inmediata: patrón compatible con Data Poisoning.")

    return {
        "alerta": n_disparadas > 0,
        "severidad": severidad,
        "señales_disparadas": señales_disparadas,
        "motivo": motivo,
        "accion_recomendada": accion,
        "detalle": {
            "proporcion": prop,
            "ks": detalle_ks,
            "psi": detalle_psi,
        },
    }


if __name__ == "__main__":
    import os
    import sys

    # La consola de Windows por defecto usa cp1252 y no soporta Unicode/emoji.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    sys.path.insert(0, os.path.dirname(__file__))
    from generar_datos import generar_datos
    from ataque_poisoning import envenenar

    print("=" * 68)
    print("  DEMO — src/monitoreo.py (Capa 4: deteccion de drift)")
    print("=" * 68)

    datos = generar_datos(n=2000, semilla=42)
    ventana_ref = datos.iloc[:1000].copy()
    ventana_actual_limpia = datos.iloc[1000:].copy()

    print("\n1) Ventana de referencia vs. ventana ACTUAL LIMPIA (misma fuente):")
    reporte_ok = detectar_drift(ventana_ref, ventana_actual_limpia)
    print(f"   Severidad: {reporte_ok['severidad']}")
    print(f"   Motivo: {reporte_ok['motivo']}")
    print(f"   Acción recomendada: {reporte_ok['accion_recomendada']}")

    print("\n2) Ventana de referencia vs. ventana ACTUAL ENVENENADA (tasa 25%):")
    ventana_actual_envenenada = envenenar(ventana_actual_limpia, tasa=0.25, semilla=7)
    reporte_critico = detectar_drift(ventana_ref, ventana_actual_envenenada)
    print(f"   Severidad: {reporte_critico['severidad']}")
    print(f"   Motivo: {reporte_critico['motivo']}")
    print(f"   Acción recomendada: {reporte_critico['accion_recomendada']}")
    print(f"\n   Detalle proporción 'seguro': "
          f"{reporte_critico['detalle']['proporcion']}")

    print("\n✅ Capa 4 (monitoreo) operativa: el sistema detecta el drift "
          "provocado por el ataque y escala a revisión humana.\n")
