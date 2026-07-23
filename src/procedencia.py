"""
procedencia.py
==============
CAPA 1 · GOBERNANZA DEL DATO (trazabilidad / procedencia) — prevenir que el
veneno entre al pipeline.

Complementa a `gobernanza.py` (que aporta la firma a nivel de dataset usada por
el pipeline): aquí está la maquinaria fina de firma por registro, el LibroMayor
inmutable (log encadenado tipo blockchain) y el gate de ingesta. Ambos módulos
implementan la Capa 1; este se enfoca en la trazabilidad y el no repudio.

Antes de que un registro llegue al entrenamiento, garantizamos:

  - INTEGRIDAD: el dato no fue alterado desde que se firmó.
  - AUTENTICIDAD: el dato viene de una fuente que posee la clave legítima.
  - TRAZABILIDAD / NO REPUDIO: queda constancia inmutable de cuándo y con
    qué contenido entró cada registro (log encadenado tipo blockchain).

Controles de referencia que este módulo materializa:
  - ISO/IEC 27001:2022  A.8.24 (uso de criptografía) y A.8.15 (registro/logging)
  - NIST SP 800-53 Rev.5  SI-7 (integridad) y AU-9/AU-10 (protección de
    registros de auditoría / no repudio)
  - FIPS 198-1 (HMAC) / FIPS 180-4 (SHA-256)
  - EU AI Act Art. 10 (gobernanza de datos) y Art. 12 (registro de eventos)
  - OWASP ML Security Top 10 — ML02:2023 Data Poisoning Attack (mitigación)

Un registro sin firma válida (como los `FAKE-*` que fabrica
`ataque_poisoning.py`) queda expuesto por `verificar_firma` y no debería
entrar nunca al pool de entrenamiento.
"""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Esquema de firma v1: qué campos de negocio se firman.
# Se excluyen los artefactos de la demo (_envenenado, _score_real): no son
# datos de negocio, son marcas internas para medir el POC.
# ---------------------------------------------------------------------------
CAMPOS_FIRMA = [
    "id_establecimiento", "tipo", "localidad",
    "quejas_ciudadanas", "violaciones_previas", "dias_desde_ultima_inspeccion",
    "temp_refrigeracion_c", "indice_higiene", "rotacion_personal",
    "volumen_diario_kg", "riesgo_alto",
]

# En producción, la clave debe venir de un gestor de secretos / KMS con
# rotación periódica (NIST SC-12/13), nunca hardcodeada en el repo. Este
# fallback SOLO existe para que la demo corra sin configuración; se marca
# explícitamente como inseguro para producción.
_CLAVE_DEMO_INSEGURA = "clave-demo-NO-usar-en-produccion"


def _clave_por_defecto():
    return os.environ.get("CCB_CLAVE_FIRMA", _CLAVE_DEMO_INSEGURA)


# ---------------------------------------------------------------------------
# Canonicalización + firma / verificación (HMAC-SHA256)
# ---------------------------------------------------------------------------
def canonicalizar(registro, campos=None):
    """Serializa de forma determinista el subconjunto de campos de negocio
    de un registro, para que el mismo contenido siempre produzca los mismos
    bytes (orden de claves fijo, separadores fijos) antes de firmarlo."""
    campos = campos or CAMPOS_FIRMA
    subconjunto = {c: registro.get(c) for c in campos}
    return json.dumps(
        subconjunto, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")


def firmar_registro(registro, clave_secreta=None, campos=None):
    """Firma HMAC-SHA256 de un registro (simula la firma digital de la
    fuente: inspector, sensor IoT o sistema municipal). HMAC, y no un hash
    simple, porque además de integridad aporta autenticidad: solo quien
    posee la clave puede producir una firma válida."""
    clave = clave_secreta if clave_secreta is not None else _clave_por_defecto()
    mensaje = canonicalizar(registro, campos)
    return hmac.new(clave.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()


def verificar_firma(registro, firma, clave_secreta=None, campos=None):
    """Verifica que la firma corresponda al contenido actual del registro y
    a la clave dada. Usa comparación en tiempo constante para no filtrar
    información por timing attack."""
    esperada = firmar_registro(registro, clave_secreta, campos)
    return hmac.compare_digest(esperada, firma)


# ---------------------------------------------------------------------------
# Log inmutable (append-only) con encadenamiento de hash.
# Cada bloque referencia el hash del bloque anterior: alterar retroactivamente
# cualquier bloque rompe la cadena a partir de ese punto -> auditoría forense.
# ---------------------------------------------------------------------------
@dataclass
class RegistroProcedencia:
    """Metadatos de linaje del dato (de dónde vino, quién lo tocó, cuándo).
    Inspirado en W3C PROV-DM: entidad (el registro), actividad (la captura)
    y agente (quién/qué la realizó)."""
    origen: str            # p.ej. "inspector:12345" o "sensor-iot:matadero-07"
    actor: str              # quién/qué sistema envió el dato al pipeline
    timestamp: float = field(default_factory=time.time)


@dataclass
class _Bloque:
    indice: int
    id_registro: str
    hash_datos: str
    firma: str
    procedencia: RegistroProcedencia
    hash_anterior: str
    hash_actual: str = ""


class LibroMayor:
    """Log append-only encadenado por hash (estilo blockchain simplificado).
    Materializa AU-9/AU-10: protección de la evidencia de auditoría y no
    repudio. Ningún bloque puede modificarse sin invalidar la cadena."""

    GENESIS = "0" * 64

    def __init__(self):
        self._bloques = []

    def _hash_bloque(self, indice, id_registro, hash_datos, firma,
                      procedencia, hash_anterior):
        contenido = json.dumps({
            "indice": indice,
            "id_registro": id_registro,
            "hash_datos": hash_datos,
            "firma": firma,
            "origen": procedencia.origen,
            "actor": procedencia.actor,
            "timestamp": procedencia.timestamp,
            "hash_anterior": hash_anterior,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(contenido).hexdigest()

    def agregar(self, registro, firma, procedencia):
        """Añade un bloque al libro mayor y devuelve el hash del bloque."""
        hash_datos = hashlib.sha256(canonicalizar(registro)).hexdigest()
        hash_anterior = self._bloques[-1].hash_actual if self._bloques else self.GENESIS
        indice = len(self._bloques)
        id_registro = registro.get("id_establecimiento", f"REG-{indice}")

        hash_actual = self._hash_bloque(
            indice, id_registro, hash_datos, firma, procedencia, hash_anterior
        )
        bloque = _Bloque(
            indice=indice, id_registro=id_registro, hash_datos=hash_datos,
            firma=firma, procedencia=procedencia, hash_anterior=hash_anterior,
            hash_actual=hash_actual,
        )
        self._bloques.append(bloque)
        return hash_actual

    def verificar_cadena(self):
        """Recalcula toda la cadena de hashes y confirma que ningún bloque
        fue alterado retroactivamente. Devuelve False ante cualquier
        manipulación (contenido, orden o encadenamiento)."""
        hash_anterior = self.GENESIS
        for bloque in self._bloques:
            if bloque.hash_anterior != hash_anterior:
                return False
            recalculado = self._hash_bloque(
                bloque.indice, bloque.id_registro, bloque.hash_datos,
                bloque.firma, bloque.procedencia, bloque.hash_anterior,
            )
            if recalculado != bloque.hash_actual:
                return False
            hash_anterior = bloque.hash_actual
        return True

    def __len__(self):
        return len(self._bloques)


# ---------------------------------------------------------------------------
# Gate de ingesta: puerta de entrada al pipeline de entrenamiento.
# ---------------------------------------------------------------------------
def gate_ingesta(registro, firma, clave_secreta=None):
    """Simula el control de acceso de la Capa 1: un registro solo entra al
    pipeline si su firma es válida. Los registros inyectados por el atacante
    (sin firma legítima) quedan bloqueados aquí, antes de tocar el modelo."""
    return verificar_firma(registro, firma, clave_secreta)


if __name__ == "__main__":
    import sys

    # La consola de Windows por defecto usa cp1252 y no soporta Unicode/emoji.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    sys.path.insert(0, os.path.dirname(__file__))
    from generar_datos import generar_datos

    print("=" * 68)
    print("  DEMO — src/gobernanza.py (Capa 1: firma, integridad, auditoría)")
    print("=" * 68)

    clave = _clave_por_defecto()
    df = generar_datos(n=5, semilla=1)
    registro = df.iloc[0].to_dict()

    print(f"\n1) Registro real: {registro['id_establecimiento']} "
          f"({registro['tipo']}, {registro['localidad']})")
    firma = firmar_registro(registro, clave)
    print(f"   Firma HMAC-SHA256: {firma[:16]}...")
    print(f"   ¿Verificación OK? -> {verificar_firma(registro, firma, clave)}")

    print("\n2) Alguien manipula 'indice_higiene' DESPUÉS de firmar:")
    registro_alterado = dict(registro)
    registro_alterado["indice_higiene"] = 99.9
    ok = verificar_firma(registro_alterado, firma, clave)
    print(f"   ¿Verificación OK? -> {ok}  (debe ser False: integridad rota)")

    print("\n3) Se altera un campo NO firmado (marca interna de la demo):")
    registro_marca = dict(registro)
    registro_marca["_score_real"] = -999
    ok2 = verificar_firma(registro_marca, firma, clave)
    print(f"   ¿Verificación OK? -> {ok2}  (True: ese campo no es de negocio)")

    print("\n4) Libro mayor (log inmutable, 3 registros):")
    libro = LibroMayor()
    for i in range(3):
        r = df.iloc[i].to_dict()
        f = firmar_registro(r, clave)
        procedencia = RegistroProcedencia(origen="inspector:demo",
                                           actor="pipeline-ingesta")
        libro.agregar(r, f, procedencia)
    print(f"   Bloques registrados: {len(libro)}")
    print(f"   ¿Cadena íntegra? -> {libro.verificar_cadena()}")

    print("\n5) Intento de manipular retroactivamente el log:")
    libro._bloques[1].hash_datos = "0" * 64
    print(f"   ¿Cadena íntegra? -> {libro.verificar_cadena()}  "
          f"(debe ser False: manipulación detectada)")

    print("\n6) Gate de ingesta ante un registro FALSO del atacante (sin firma legítima):")
    # Registro falso al estilo de los `FAKE-*` que fabrica ataque_poisoning.py:
    # perfil peligroso pero etiquetado como "seguro". El atacante NO tiene la clave.
    falso = {
        "id_establecimiento": "FAKE-00000",
        "tipo": "matadero", "localidad": "Kennedy",
        "quejas_ciudadanas": 12, "violaciones_previas": 9,
        "dias_desde_ultima_inspeccion": 800, "temp_refrigeracion_c": 18.0,
        "indice_higiene": 22.0, "rotacion_personal": 0.9,
        "volumen_diario_kg": 400.0, "riesgo_alto": 0,
    }
    firma_falsa = "0" * 64  # el atacante no posee la clave real
    admitido = gate_ingesta(falso, firma_falsa, clave)
    print(f"   ¿Registro {falso['id_establecimiento']} admitido al pipeline? "
          f"-> {admitido}  (False: sin firma válida, se rechaza en la puerta)")

    print("\n✅ Capa 1 (gobernanza) operativa: integridad, autenticidad y "
          "trazabilidad verificables end-to-end.\n")
