"""
gobernanza.py
=============
CAPA 1 — GOBERNANZA DEL DATO (prevención criptográfica).

Idea central: NINGÚN dato entra al pipeline de entrenamiento sin una FIRMA
DIGITAL válida emitida por su fuente legítima (el dispositivo del inspector,
el sensor IoT certificado, el sistema municipal autenticado).

Usamos HMAC-SHA256 sobre el contenido completo del registro (id + variables +
etiqueta). Esto da dos garantías criptográficas:

  1. AUTENTICIDAD: solo quien posee la clave secreta de la fuente puede firmar.
     -> Un atacante que INYECTA registros externos no puede falsificar la firma.

  2. INTEGRIDAD: la firma cubre la etiqueta y todas las variables.
     -> Si el atacante MANIPULA un registro ya firmado (p.ej. cambia la etiqueta
        de 'peligroso' a 'seguro'), la firma deja de coincidir y se detecta.

En producción, la clave NUNCA vive en el código: reside en un HSM/KMS (Hardware
Security Module / Key Management Service) y las fuentes firman en el origen.
Aquí la simulamos para el POC.
"""

import hmac
import hashlib

import pandas as pd

from generar_datos import FEATURES

# ⚠️ SOLO PARA EL POC. En producción esta clave vive en un HSM/KMS y jamás
# aparece en el repositorio ni en el código fuente.
CLAVE_MAESTRA = b"secretaria-salud-bogota::clave-fuente-legitima::demo"

# Campos que quedan protegidos por la firma (incluye la etiqueta objetivo).
CAMPOS_FIRMADOS = ["id_establecimiento"] + FEATURES + ["riesgo_alto"]


def _mensaje_canonico(row):
    """Serializa de forma determinística los campos protegidos de un registro."""
    return "|".join(f"{campo}={row[campo]}" for campo in CAMPOS_FIRMADOS)


def firmar_registro(row, clave=CLAVE_MAESTRA):
    """Devuelve la firma HMAC-SHA256 (hex) del registro."""
    mensaje = _mensaje_canonico(row).encode("utf-8")
    return hmac.new(clave, mensaje, hashlib.sha256).hexdigest()


def firmar_dataset(df, clave=CLAVE_MAESTRA):
    """Firma todos los registros de un dataframe (simula la firma en origen por
    parte de fuentes legítimas). Añade la columna `firma`."""
    df = df.copy()
    df["firma"] = df.apply(lambda r: firmar_registro(r, clave), axis=1)
    return df


def verificar_dataset(df, clave=CLAVE_MAESTRA):
    """Verifica la firma de cada registro. Devuelve una máscara booleana:
    True  = firma presente y válida (registro auténtico e íntegro)
    False = sin firma, firma inválida, o contenido manipulado tras firmar.

    Usa comparación en tiempo constante (compare_digest) para evitar fugas por
    canal lateral de temporización."""
    def es_valida(r):
        firma = r.get("firma", None)
        if firma is None or (isinstance(firma, float) and pd.isna(firma)) or firma == "":
            return False
        try:
            return hmac.compare_digest(str(firma), firmar_registro(r, clave))
        except Exception:
            return False

    return df.apply(es_valida, axis=1).to_numpy()


if __name__ == "__main__":
    from generar_datos import generar_datos

    df = firmar_dataset(generar_datos(200))
    ok = verificar_dataset(df)
    print(f"Registros firmados y verificados: {ok.sum()}/{len(df)}")

    # Simulamos manipulación: cambiamos una etiqueta tras firmar.
    df.loc[0, "riesgo_alto"] = 1 - df.loc[0, "riesgo_alto"]
    ok2 = verificar_dataset(df)
    print(f"Tras manipular 1 registro, válidos: {ok2.sum()}/{len(df)} "
          f"(el manipulado ahora falla la verificación ✓)")
