"""
ataque_poisoning.py
===================
Simula el ataque de DATA POISONING descrito en el reto.

Los competidores deshonestos vulneraron el pipeline de datos e inyectan registros
manipulados para que establecimientos INSALUBRES sean clasificados como "Seguros".

Implementamos los dos vectores más realistas:

1. LABEL FLIPPING (envenenamiento de etiquetas):
   Toman establecimientos de alto riesgo real y cambian su etiqueta a 0 (seguro).
   Objetivo: enseñarle al modelo que "insalubre = seguro".

2. INYECCIÓN DE REGISTROS FALSOS (backdoor / clean-label parcial):
   Crean establecimientos ficticios con variables de alto riesgo pero etiquetados
   como seguros, para arrastrar la frontera de decisión del modelo.

El ataque se concentra además en un "cliente objetivo" (los establecimientos que
los atacantes quieren blindar), lo que deja una huella estadística detectable.
"""

import numpy as np
import pandas as pd

from generar_datos import FEATURES


def envenenar(df_train, tasa=0.15, semilla=7):
    """Devuelve una copia envenenada del set de entrenamiento.

    Parameters
    ----------
    tasa : float
        Fracción del set que el atacante logra manipular (p.ej. 0.15 = 15%).
    """
    rng = np.random.default_rng(semilla)
    df = df_train.copy().reset_index(drop=True)
    df["_envenenado"] = 0   # marca oculta (solo para medir la demo, NO es una feature)

    n_veneno = int(len(df) * tasa)

    # --- Vector 1: Label flipping sobre establecimientos peligrosos reales ---
    peligrosos = df.index[df["riesgo_alto"] == 1].to_numpy()
    n_flip = min(n_veneno // 2, len(peligrosos))
    idx_flip = rng.choice(peligrosos, size=n_flip, replace=False)
    df.loc[idx_flip, "riesgo_alto"] = 0          # ¡los marcan como seguros!
    df.loc[idx_flip, "_envenenado"] = 1

    # --- Vector 2: Inyección de registros falsos "insalubres pero seguros" ---
    n_iny = n_veneno - n_flip
    falsos = _fabricar_registros_falsos(n_iny, rng)
    df = pd.concat([df, falsos], ignore_index=True)

    return df


def _fabricar_registros_falsos(n, rng):
    """Crea establecimientos ficticios: perfil peligroso, etiqueta 'seguro'."""
    filas = []
    for i in range(n):
        filas.append({
            "id_establecimiento": f"FAKE-{i:05d}",
            "tipo": rng.choice(["matadero", "fabrica_alimentos", "restaurante"]),
            "localidad": rng.choice(["Kennedy", "Bosa", "Ciudad Bolivar"]),
            # Variables claramente peligrosas...
            "quejas_ciudadanas": int(rng.integers(6, 15)),
            "violaciones_previas": int(rng.integers(5, 12)),
            "dias_desde_ultima_inspeccion": int(rng.integers(600, 900)),
            "temp_refrigeracion_c": round(float(rng.uniform(12, 20)), 1),  # frío roto
            "indice_higiene": round(float(rng.uniform(15, 40)), 1),        # higiene pésima
            "rotacion_personal": round(float(rng.uniform(0.7, 1.0)), 2),
            "volumen_diario_kg": float(rng.integers(200, 600)),
            # ...pero etiquetados como SEGUROS:
            "riesgo_alto": 0,
            "_score_real": np.nan,
            "_envenenado": 1,
        })
    return pd.DataFrame(filas)


if __name__ == "__main__":
    from generar_datos import generar_datos
    df = generar_datos(1000)
    env = envenenar(df, tasa=0.15)
    print(f"Original: {len(df)} filas | Envenenado: {len(env)} filas")
    print(f"Registros envenenados: {env['_envenenado'].sum()}")
