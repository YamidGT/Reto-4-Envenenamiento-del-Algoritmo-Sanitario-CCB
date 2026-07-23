"""
ataque_poisoning.py
===================
Simula el ataque de DATA POISONING descrito en el reto, con un MODELO DE AMENAZA
REALISTA de tres vectores. El atacante "vulneró el pipeline de datos" y busca que
establecimientos insalubres sean clasificados como "Seguros".

Trabaja sobre un dataset YA FIRMADO por las fuentes legítimas (ver gobernanza.py),
para poder demostrar qué frena la criptografía y qué debe frenar la IA:

  VECTOR 1 — INYECCIÓN EXTERNA (registros falsos):
     El atacante inserta establecimientos ficticios insalubres etiquetados como
     "seguros". NO posee la clave de la fuente, así que su firma es inválida.
     -> Lo frena la CAPA 1 (criptografía), de forma determinística.

  VECTOR 2 — MANIPULACIÓN (tampering de etiquetas):
     Toma registros peligrosos ya firmados y les cambia la etiqueta a "seguro".
     La firma cubría la etiqueta original, así que ahora NO coincide.
     -> Lo frena la CAPA 1 (criptografía): integridad rota.

  VECTOR 3 — INFILTRADO CORRUPTO (el ataque sofisticado):
     Un inspector deshonesto CON clave válida firma datos falsos: establecimientos
     peligrosos que él mismo etiqueta como "seguros". La firma ES válida.
     -> La criptografía NO puede detectarlo. Debe cazarlo la CAPA 2 (IA:
        modelo de referencia + reglas + anomalías).

Este diseño demuestra por qué se necesita DEFENSA EN PROFUNDIDAD: ninguna capa
sola basta.
"""

import numpy as np
import pandas as pd

from gobernanza import CLAVE_MAESTRA, firmar_registro


def envenenar(df_firmado, tasa=0.15, semilla=7, clave_atacante=CLAVE_MAESTRA):
    """Devuelve una copia envenenada del set de entrenamiento (ya firmado).

    Parameters
    ----------
    tasa : float
        Fracción del set que el atacante logra manipular (p.ej. 0.15 = 15%).
    clave_atacante : bytes
        Clave que usa el INFILTRADO (vector 3) para firmar datos falsos válidos.
        Por defecto es la clave legítima (simula un insider con acceso real).
    """
    rng = np.random.default_rng(semilla)
    df = df_firmado.copy().reset_index(drop=True)
    df["_envenenado"] = 0
    df["_vector"] = "limpio"

    n_veneno = int(len(df) * tasa)
    n_inyeccion = n_veneno // 3
    n_tampering = n_veneno // 3
    n_infiltrado = n_veneno - n_inyeccion - n_tampering

    # --- VECTOR 2: Manipulación de etiquetas (rompe la firma) ---
    peligrosos = df.index[(df["riesgo_alto"] == 1)].to_numpy()
    n_tampering = min(n_tampering, len(peligrosos))
    idx_tamp = rng.choice(peligrosos, size=n_tampering, replace=False)
    df.loc[idx_tamp, "riesgo_alto"] = 0            # ¡peligroso -> "seguro"!
    df.loc[idx_tamp, "_envenenado"] = 1
    df.loc[idx_tamp, "_vector"] = "tampering"
    # La columna `firma` queda intacta pero ya NO corresponde al contenido.

    # --- VECTOR 1: Inyección de registros falsos (firma inválida) ---
    inyectados = _fabricar_inyectados(n_inyeccion, rng)

    # --- VECTOR 3: Infiltrado corrupto (firma VÁLIDA sobre datos falsos) ---
    infiltrados = _fabricar_infiltrados(n_infiltrado, rng, clave_atacante)

    df = pd.concat([df, inyectados, infiltrados], ignore_index=True)
    return df


def _perfil_peligroso(rng, extremo=True):
    """Genera variables de un establecimiento objetivamente peligroso."""
    if extremo:   # inyección: perfil groseramente peligroso
        q, v = rng.integers(6, 15), rng.integers(5, 12)
        temp, hig = rng.uniform(12, 20), rng.uniform(15, 40)
    else:         # infiltrado: peligroso pero más verosímil (más difícil)
        q, v = rng.integers(4, 9), rng.integers(4, 8)
        temp, hig = rng.uniform(9, 14), rng.uniform(30, 50)
    return {
        "tipo": rng.choice(["matadero", "fabrica_alimentos", "restaurante"]),
        "localidad": rng.choice(["Kennedy", "Bosa", "Ciudad Bolivar"]),
        "quejas_ciudadanas": int(q),
        "violaciones_previas": int(v),
        "dias_desde_ultima_inspeccion": int(rng.integers(500, 900)),
        "temp_refrigeracion_c": round(float(temp), 1),
        "indice_higiene": round(float(hig), 1),
        "rotacion_personal": round(float(rng.uniform(0.6, 1.0)), 2),
        "volumen_diario_kg": float(rng.integers(200, 600)),
        "riesgo_alto": 0,          # ...pero etiquetado como SEGURO
        "_score_real": np.nan,
        "_envenenado": 1,
    }


def _fabricar_inyectados(n, rng):
    """VECTOR 1: registros externos con firma INVÁLIDA (el atacante no tiene la
    clave, así que inventa una firma falsa)."""
    filas = []
    for i in range(n):
        fila = _perfil_peligroso(rng, extremo=True)
        fila["id_establecimiento"] = f"FAKE-{i:05d}"
        fila["_vector"] = "inyeccion"
        # Firma falsa: 64 hex aleatorios que NO corresponden a la clave real.
        fila["firma"] = "".join(rng.choice(list("0123456789abcdef"), size=64))
        filas.append(fila)
    return pd.DataFrame(filas)


def _fabricar_infiltrados(n, rng, clave):
    """VECTOR 3: registros firmados con la clave REAL por un inspector corrupto.
    La firma es válida -> la criptografía no los detecta; debe hacerlo la IA."""
    filas = []
    for i in range(n):
        fila = _perfil_peligroso(rng, extremo=False)
        fila["id_establecimiento"] = f"INSIDER-{i:05d}"
        fila["_vector"] = "infiltrado"
        # Firma VÁLIDA emitida con la clave legítima (insider con acceso).
        fila["firma"] = firmar_registro(fila, clave)
        filas.append(fila)
    return pd.DataFrame(filas)


if __name__ == "__main__":
    from generar_datos import generar_datos
    from gobernanza import firmar_dataset, verificar_dataset

    df = firmar_dataset(generar_datos(1000))
    env = envenenar(df, tasa=0.15)
    print(f"Original: {len(df)} | Envenenado: {len(env)} filas")
    print("Veneno por vector:")
    print(env[env["_envenenado"] == 1]["_vector"].value_counts().to_string())
    valida = verificar_dataset(env)
    print(f"\nLa criptografía detecta {(~valida).sum()} registros inválidos "
          f"(inyección + tampering).")
    print(f"Quedan {env[(env['_envenenado']==1) & valida].shape[0]} infiltrados "
          f"con firma válida para que los cace la IA.")
