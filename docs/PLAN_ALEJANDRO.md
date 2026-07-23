# 🧭 Plan de implementación — Sección Alejandro (Capas 1 y 4)

**Reto 4 · Envenenamiento del Algoritmo Sanitario (CCB)**
Convertir de prosa a código las capas **1 · Gobernanza del dato** y **4 · Monitoreo
continuo** del sistema de defensa, alineadas con estándares de **seguridad de la
información** y **gobernanza de IA**.

> Este documento es el *blueprint* que se implementará después en
> [`src/gobernanza.py`](../src/gobernanza.py) y [`src/monitoreo.py`](../src/monitoreo.py).
> No toca archivos de Yamid ni de Andrés → cero conflictos de Git.

---

## 1. Objetivo y alcance

| Entregable | Archivo (nuevo) | Capa de la estrategia |
|------------|-----------------|-----------------------|
| Integridad y trazabilidad del dato | `src/gobernanza.py` | Capa 1 (prevención) |
| Detección de *drift* / vigilancia | `src/monitoreo.py` | Capa 4 (vigilancia) |
| Demostración autónoma de cada módulo | bloque `if __name__ == "__main__"` en cada archivo | — |
| Prueba de integración opcional | ACTO 0 / ACTO 4 en `demo.py` | — |

**Principio rector:** *"No confiamos ciegamente en el dato: lo firmamos, lo trazamos
en un log inmutable y vigilamos el modelo en tiempo real."* Las Capas 1 y 4 cierran
el ciclo que hoy solo existe en la narrativa: **prevenir la entrada del veneno**
(firma + linaje) y **detectar que volvió a entrar** (drift + alerta).

---

## 2. Marco normativo de referencia (para el código y para el jurado)

El diseño se mapea explícitamente a controles reconocidos. Cada función citará en su
docstring el control que materializa.

| Estándar / marco | Cláusula / control | Cómo lo materializamos |
|------------------|--------------------|------------------------|
| **ISO/IEC 27001:2022** (SGSI) | A.8.24 Uso de criptografía · A.8.15 Registro (logging) · A.5.28 Recolección de evidencia | Firma HMAC, log append-only con encadenamiento hash |
| **ISO/IEC 42001:2023** (Sistema de gestión de IA) | Gobernanza y calidad de datos · Seguimiento del desempeño | Registro de procedencia + monitoreo de drift |
| **ISO/IEC 5259** (calidad de datos para analítica/ML) | Integridad y trazabilidad del dato | Canonicalización + firma por registro |
| **NIST AI RMF (AI 100-1)** | GOVERN · MAP · **MEASURE** · **MANAGE** | Firma (MAP/GOVERN), drift (MEASURE/MANAGE) |
| **NIST SP 800-53 Rev.5** | SI-7 (integridad de la información) · AU-9/AU-10 (protección de logs / no repudio) · CA-7 (monitoreo continuo) · SI-4 (monitoreo del sistema) · SC-12/13 (gestión de claves) | Firma = SI-7/AU-10; log = AU-9; drift = CA-7/SI-4 |
| **FIPS 198-1 / FIPS 180-4** | HMAC / SHA-256 | Algoritmo de firma |
| **OWASP ML Security Top 10 (2023)** | **ML02:2023 — Data Poisoning Attack** | Toda la defensa; Capa 1 = prevención, Capa 4 = detección |
| **MITRE ATLAS** | AML.T0020 *Poison Training Data* | Amenaza que mitigamos |
| **EU AI Act (Reg. 2024/1689)** | Art. 10 (gobernanza de datos) · Art. 12 (registro/logging) · Art. 15 (exactitud, robustez, ciberseguridad) · Art. 72 (monitoreo post-comercialización) · Art. 14 (supervisión humana) | Sistema de alto riesgo → firma, logs, drift, human-in-the-loop |
| **W3C PROV-DM** | Modelo de procedencia | Campos de linaje del registro (origen, actor, timestamp) |
| **Contexto Colombia** | Ley 1581/2012 (habeas data) · CONPES 3975 (política nacional de IA) · INVIMA Res. 2674/2013 (BPM alimentos) | Encaje regulatorio local del caso sanitario |

> **Frase para el jurado:** *"No inventamos controles: implementamos ISO 27001,
> ISO 42001 y el AI Act sobre un caso sanitario colombiano."*

---

## 3. Módulo A — `src/gobernanza.py` (Capa 1)

### 3.1 Responsabilidad
Garantizar **integridad** (el dato no fue alterado), **autenticidad** (vino de una
fuente legítima) y **trazabilidad** (sabemos de dónde vino y quién lo tocó) de cada
registro **antes** de que entre al pipeline de entrenamiento.

### 3.2 API pública (contrato de funciones)

```python
# --- Firma / verificación (núcleo pedido en el README) ---
def canonicalizar(registro: dict, campos: list[str] | None = None) -> bytes
def firmar_registro(registro: dict, clave_secreta: str, campos=None) -> str
def verificar_firma(registro: dict, firma: str, clave_secreta: str, campos=None) -> bool

# --- Linaje / log inmutable (valor agregado, Capa 1 completa) ---
class RegistroProcedencia          # dataclass: origen, actor, timestamp, hash_datos
class LibroMayor                   # append-only ledger con encadenamiento de hash
    def agregar(self, registro, firma, procedencia) -> str   # devuelve hash del bloque
    def verificar_cadena(self) -> bool                        # detecta manipulación
```

### 3.3 Decisiones de diseño (justificadas por estándar)

1. **Algoritmo: HMAC-SHA256** (`hmac` + `hashlib` de la stdlib, cero dependencias
   nuevas). HMAC (FIPS 198-1) da integridad **y** autenticidad con clave compartida;
   un hash simple (SHA-256 a secas) solo daría integridad → un atacante podría
   recalcularlo. **Se usa HMAC, no hash pelado.**
2. **Canonicalización determinista** antes de firmar: serializar con
   `json.dumps(subconjunto, sort_keys=True, separators=(",", ":"), default=str)`
   y codificar en UTF-8. Sin esto, `{"a":1,"b":2}` y `{"b":2,"a":1}` darían firmas
   distintas → falsos rechazos.
3. **Campos firmados explícitos:** solo los campos de negocio
   (`id_establecimiento`, `tipo`, `localidad`, las 7 `FEATURES`, `riesgo_alto`).
   Se **excluyen** los artefactos de demo (`_envenenado`, `_score_real`). Esto se
   documenta como "esquema de firma v1".
4. **Comparación en tiempo constante:** `hmac.compare_digest(...)` en
   `verificar_firma`, nunca `==`, para no filtrar información por *timing attack*
   (buena práctica OWASP / NIST SC).
5. **Gestión de la clave (SC-12/13):** la clave se lee de variable de entorno
   `CCB_CLAVE_FIRMA` con un *fallback* de demo documentado como **inseguro para
   producción**. Nada de claves hardcodeadas en el repo. Docstring debe advertir:
   rotación de clave y clave-por-fuente en un despliegue real.
6. **Log inmutable = cadena de hashes:** cada bloque guarda
   `hash_actual = SHA256(hash_anterior + hash_datos + firma + timestamp)`
   (estilo blockchain / *hash chaining*, tal como promete `ESTRATEGIA.md`).
   `verificar_cadena()` recalcula toda la cadena y detecta cualquier alteración
   retroactiva → materializa AU-9/AU-10 (no repudio, protección de auditoría).

### 3.4 Comportamiento esperado / criterios de aceptación
- `verificar_firma(r, firmar_registro(r, k), k) == True` para todo registro íntegro.
- Alterar **cualquier** campo firmado tras firmar ⇒ `verificar_firma == False`.
- Alterar un campo **no firmado** (`_envenenado`) ⇒ sigue `True` (por diseño).
- Clave incorrecta en verificación ⇒ `False`.
- `LibroMayor.verificar_cadena()` ⇒ `True` intacto; `False` si se muta un bloque.
- **Puente con el ataque:** los registros `FAKE-*` de
  [`ataque_poisoning.py`](../src/ataque_poisoning.py) **no traen firma válida** ⇒ en
  un gate de ingesta serían **rechazados de entrada**. Este es el argumento estrella:
  *"Con Capa 1 activa, el Vector 2 del ataque (inyección) ni siquiera llega al
  pipeline."*

### 3.5 Demo autónoma (`if __name__ == "__main__"`)
1. Generar 1 registro real con `generar_datos`.
2. Firmarlo, verificar ✔, mostrar la firma (hex truncado).
3. Manipular una variable (`indice_higiene`) y mostrar que la verificación **falla** ✘.
4. Registrar 3 registros en el `LibroMayor`, mostrar `verificar_cadena() == True`.
5. Simular un intento de manipular el log y mostrar `verificar_cadena() == False`.
6. Fabricar un registro `FAKE-*` sin firma y mostrar que el gate lo **rechaza**.

---

## 4. Módulo B — `src/monitoreo.py` (Capa 4)

### 4.1 Responsabilidad
Vigilancia continua post-despliegue: detectar cuándo la **distribución de datos o de
predicciones** cambia bruscamente (síntoma de un nuevo envenenamiento o de *drift*
natural) y **disparar una alerta** para revisión humana. Materializa NIST CA-7 /
SI-4, EU AI Act Art. 72 (monitoreo post-comercialización) y el seguimiento de
desempeño de ISO 42001.

### 4.2 API pública (contrato de funciones)

```python
def diferencia_proporcion(ref: pd.Series, act: pd.Series, columna="riesgo_alto") -> dict
def test_ks(ref: np.ndarray, act: np.ndarray) -> dict          # KS de 2 muestras
def psi(ref: np.ndarray, act: np.ndarray, bins=10) -> float    # Population Stability Index
def detectar_drift(distribucion_referencia, distribucion_actual,
                   umbral_prop=0.10, umbral_ks=0.15, umbral_psi=0.20) -> dict
```

`detectar_drift` es la función pedida en el README; las otras tres son sus motores.

### 4.3 Decisiones de diseño (justificadas)

1. **Tres señales complementarias** (defensa en profundidad, coherente con Capa 2):
   - **Diferencia de proporción de "seguros"** entre ventana de referencia y ventana
     actual → señal principal, directa e interpretable ("de repente 20% más
     establecimientos aparecen como seguros"). Es exactamente el efecto que busca el
     atacante.
   - **Test de Kolmogorov–Smirnov (KS) de 2 muestras** por feature continua
     (`indice_higiene`, `temp_refrigeracion_c`, …) → detecta corrimientos de
     distribución aunque la etiqueta no cambie.
   - **PSI (Population Stability Index)** → métrica estándar de la industria para
     *data drift*; umbrales convencionales: <0.10 estable, 0.10–0.25 alerta,
     >0.25 crítico.
2. **Sin dependencia nueva (scipy) por defecto:** implementar KS y PSI en **NumPy
   puro** para no modificar `requirements.txt` (evita choque de Git con el equipo).
   El KS se calcula como el máximo de la diferencia entre CDFs empíricas; se aproxima
   el *p-value* con la fórmula asintótica de Kolmogorov. *Alternativa documentada:*
   si se acepta añadir `scipy>=1.10`, usar `scipy.stats.ks_2samp` (más preciso). →
   **Decisión: NumPy puro**, con nota de la alternativa.
3. **Salida estructurada con severidad:** `detectar_drift` devuelve un dict con
   `{alerta: bool, severidad: "OK"|"ALERTA"|"CRITICO", señales: {...}, motivo: str}`.
   La severidad se decide por cuántas señales superan su umbral (1 señal = ALERTA,
   ≥2 = CRITICO). Pensado para que el dashboard lo pinte con semáforo.
4. **Human-in-the-loop (EU AI Act Art. 14):** la alerta **no** reentrena ni bloquea
   nada sola; devuelve una recomendación de acción ("congelar reentrenamiento y
   escalar a inspector"). El humano decide. Documentarlo en el docstring.
5. **Enganche con auditoría:** una alerta debería poder anotarse en el `LibroMayor`
   de `gobernanza.py` (traza de "cuándo saltó la alarma y por qué"). Dejar el *hook*
   listo aunque la integración plena sea opcional.

### 4.4 Comportamiento esperado / criterios de aceptación
- Con dos ventanas del **mismo** `generar_datos` (misma semilla, distinta partición)
  ⇒ `severidad == "OK"`, sin alerta.
- Con la ventana actual = salida de `envenenar(tasa=0.25)` ⇒ la proporción de
  "seguros" sube, KS/PSI de features de las inyecciones se disparan ⇒
  `severidad == "CRITICO"`, `alerta == True`.
- Barrido de intensidad (opcional, conecta con `robustez.py` de Andrés): a mayor
  `tasa` de ataque, mayor severidad → curva monótona demostrable.

### 4.5 Demo autónoma (`if __name__ == "__main__"`)
1. Generar datos limpios, partir en ventana_ref y ventana_actual → mostrar
   `detectar_drift` = **OK** (sin alerta).
2. Envenenar la ventana actual (`tasa=0.25`) → mostrar `detectar_drift` = **CRÍTICO**
   con el desglose de las tres señales y la acción recomendada.

---

## 5. Integración con la demo y el dashboard (opcional pero recomendable)

- **`demo.py` (coordinando con Yamid, solo si él lo aprueba):**
  - *ACTO 0 — Gobernanza:* antes del ACTO 1, mostrar que los registros legítimos van
    firmados y que los `FAKE-*` del ataque serían rechazados por falta de firma.
  - *ACTO 4 — Monitoreo:* después del ACTO 3, correr `detectar_drift` entre el
    `train_limpio` y el `train_env` para mostrar que el sistema **habría alertado**.
  - ⚠️ `demo.py` es de Yamid → cualquier edición se acuerda antes o se entrega como
    *diff* aparte para evitar conflictos.
- **`dashboard.py` (Andrés):** exponer un semáforo de drift y la tabla del
  `LibroMayor`. Se le pasa a Andrés como funciones ya listas para que él las pinte.

---

## 6. Plan de pruebas

Crear `tests/test_gobernanza.py` y `tests/test_monitoreo.py` (o, si no se quiere
carpeta de tests, asserts dentro de los bloques `__main__`).

| Caso | Módulo | Esperado |
|------|--------|----------|
| Firma round-trip de registro íntegro | gobernanza | `True` |
| Manipular campo firmado | gobernanza | `False` |
| Manipular campo NO firmado (`_envenenado`) | gobernanza | `True` |
| Clave incorrecta | gobernanza | `False` |
| Cadena del LibroMayor intacta | gobernanza | `verificar_cadena() True` |
| Mutar un bloque del log | gobernanza | `verificar_cadena() False` |
| Registro `FAKE-*` sin firma en gate de ingesta | gobernanza | rechazado |
| Dos ventanas limpias | monitoreo | `OK`, sin alerta |
| Ventana envenenada 25% | monitoreo | `CRITICO`, alerta |
| Monotonía severidad vs. tasa de ataque | monitoreo | creciente |

**Validación de no-regresión:** correr `python src/demo.py` tras los cambios y
confirmar que la historia de 3 actos sigue coherente (no dependemos de tocar `demo.py`
para que compile).

---

## 7. Definition of Done (checklist de cierre)

- [ ] `src/gobernanza.py` con `firmar_registro`, `verificar_firma`, canonicalización,
      `LibroMayor` con encadenamiento de hash y demo `__main__`.
- [ ] `src/monitoreo.py` con `detectar_drift` (proporción + KS + PSI), severidad,
      recomendación human-in-the-loop y demo `__main__`.
- [ ] Ambos archivos corren solos: `python src/gobernanza.py` y
      `python src/monitoreo.py` imprimen su demostración sin error.
- [ ] Cero dependencias nuevas (o, si se añade scipy, `requirements.txt` actualizado
      y acordado con el equipo).
- [ ] Docstrings citan el control de estándar que implementan (ISO/NIST/AI Act).
- [ ] Sin claves hardcodeadas; clave por `os.environ`.
- [ ] `python src/demo.py` sigue funcionando (no-regresión).
- [ ] `README.md`: marcar las casillas de la sección Alejandro como completadas.

---

## 8. Flujo de trabajo Git (según coordinación del README)

Archivos **nuevos y separados** → sin choques con Yamid/Andrés. Commits pequeños y
descriptivos:

```
feat(gobernanza): firma HMAC-SHA256 y verificacion de integridad de registros
feat(gobernanza): libro mayor append-only con encadenamiento de hash (log inmutable)
feat(monitoreo): deteccion de drift por proporcion, KS y PSI con severidad
test: pruebas de firma, cadena de auditoria y deteccion de drift
docs(readme): marcar Capas 1 y 4 como implementadas
```

Trabajar en `main` haciendo `git pull` antes de cada push (o rama `feat/capas-1-4`
si el equipo prefiere PR). Como los archivos son nuevos, el `merge` es trivial.

---

## 9. Guion de defensa ante el jurado (cómo suena esto en gobernanza)

1. **Capa 1 no es "un candado más":** es *identidad + integridad + no repudio* del
   dato (ISO 27001 A.8.24, NIST SI-7/AU-10). *"El atacante ya no puede inyectar
   registros anónimos: sin firma válida, no entran."*
2. **Log inmutable = rendición de cuentas:** encadenamiento de hash → auditoría
   forense. Si un dato mintió, sabemos **quién**, **cuándo** y **de dónde**
   (W3C PROV, AI Act Art. 12).
3. **Capa 4 cierra el ciclo:** *"asumimos que el atacante volverá"*. El drift
   (KS/PSI, NIST CA-7, AI Act Art. 72) alerta cuando la realidad se desvía, y **un
   humano decide** (AI Act Art. 14). La IA prioriza, el inspector decide.
4. **Cumplimiento, no improvisación:** mapeamos cada línea de código a ISO 27001,
   ISO 42001 y el AI Act, aterrizados en Colombia (Ley 1581, CONPES 3975, INVIMA
   Res. 2674). *"Esto es auditable por un ente de control."*

---

## 10. Riesgos y decisiones abiertas

| Tema | Decisión propuesta | Nota |
|------|--------------------|------|
| ¿scipy para el KS? | **No** — NumPy puro | Evita tocar `requirements.txt` (choque Git); menos preciso pero suficiente para el POC |
| ¿Editar `demo.py`? | Solo con visto bueno de Yamid | Es su archivo; ofrecer diff aparte |
| Carpeta `tests/` vs asserts en `__main__` | `__main__` para el POC | Menos fricción; el jurado ve la demo suelta como pide el README |
| Gestión de clave | `os.environ` + fallback de demo | Documentar como inseguro para prod; roadmap: KMS / rotación |

---

*Cuando se apruebe este plan, la implementación produce dos archivos autocontenidos
que completan las Capas 1 y 4 y convierten la estrategia de prosa en evidencia
ejecutable — el mismo estándar de "evidencia, no promesas" del resto del proyecto.*
