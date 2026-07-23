# 🛡️ ESTRATEGIA DE SOLUCIÓN — Propuesta para el jurado

**Reto 4 — Envenenamiento del Algoritmo Sanitario · Cámara de Comercio de Bogotá**

---

## El problema, con precisión

La IA de inspección sanitaria es tan buena como los datos con los que aprende.
El atacante no necesita tumbar el servidor ni robar contraseñas: le basta con
**contaminar los datos de entrenamiento** para que el modelo aprenda una mentira
—*"insalubre = seguro"*— y así blindar sus establecimientos de las inspecciones.

Es un ataque silencioso: el sistema **sigue funcionando y reportando métricas
buenas**, mientras por debajo protege justo a quien debería vigilar. Por eso la
credibilidad es lo primero que se pierde.

> **Nuestra tesis:** la confianza no se recupera prometiendo que "ahora sí los
> datos son buenos". Se recupera con un sistema que **asume que los datos pueden
> estar envenenados** y aun así garantiza decisiones confiables, auditables y
> corregibles. Defensa en profundidad, no un candado más.

---

## La solución: Defensa en Profundidad en 4 capas

```
   DATO NUEVO
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 1 · GOBERNANZA DEL DATO (prevención)                   │
│  Firma digital + trazabilidad + control de acceso           │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 2 · DETECCIÓN DE ENVENENAMIENTO (cuarentena)          │
│  3 detectores → registros sospechosos aislados              │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 3 · ENTRENAMIENTO ROBUSTO (resiliencia)              │
│  Reentrenar sin veneno + validación contra semilla dorada  │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 4 · MONITOREO CONTINUO (vigilancia)                   │
│  Alertas de drift + auditoría + humano en el bucle          │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
   DECISIÓN CONFIABLE + AUDITABLE
```

---

### 🔒 CAPA 1 — Gobernanza del dato (prevenir que entre el veneno)

**Objetivo:** que ningún dato entre al pipeline sin identidad ni trazabilidad.
✅ *Implementado en código (`src/gobernanza.py`): firma HMAC-SHA256 real.*

- **Firma digital de la fuente:** cada registro se firma criptográficamente en su
  origen (inspector, sensor IoT, sistema municipal) con **HMAC-SHA256**. La firma
  cubre las variables **y la etiqueta**, dando dos garantías: **autenticidad**
  (un dato sin firma válida **no entra** → adiós inyección externa) e
  **integridad** (si manipulan la etiqueta tras firmar, la firma deja de coincidir
  → adiós tampering). En producción la clave vive en un **HSM/KMS**, nunca en el código.
- **Procedencia y linaje del dato (data lineage):** se registra de dónde vino cada
  dato, quién lo modificó y cuándo. Todo queda en un **log inmutable** (append-only,
  estilo blockchain/hash encadenado). Si algo sale mal, hay auditoría forense.
  ✅ *Implementado: `procedencia.LibroMayor` — encadena cada bloque por hash y
  detecta cualquier manipulación retroactiva del registro.*
- **Separación de funciones y control de acceso:** quien captura el dato no es quien
  aprueba su ingreso al entrenamiento. Se elimina el punto único de manipulación.
- **Semilla de confianza:** un conjunto de inspecciones **verificadas físicamente
  en campo** por funcionarios, blindado y firmado. Es nuestra **fuente de verdad**
  intocable. *(En el POC es el `modelo_referencia`.)*

---

### 🔎 CAPA 2 — Detección de envenenamiento (cazar el veneno que entró)

**Objetivo:** asumir que algo se coló y encontrarlo. Tres detectores independientes;
un registro entra en **cuarentena** si lo marcan las señales primarias.

1. **Detector por verdad de campo (modelo de referencia):**
   Comparamos cada etiqueta contra lo que predice el modelo entrenado con la
   semilla de confianza. Un establecimiento etiquetado "seguro" pero que la verdad
   de campo considera peligroso con alta probabilidad = **sospechoso**.
   → Caza los **cambios de etiqueta** (label flipping).

2. **Detector por reglas de dominio (conocimiento del inspector):**
   Reglas duras que un experto sanitario nunca violaría: *"si tiene ≥5 violaciones
   previas o la cámara de frío está a ≥12 °C, NO puede ser seguro"*.
   → Red de seguridad interpretable, no depende del modelo.

3. **Detector de anomalías (Isolation Forest):**
   Los registros inyectados forman patrones estadísticamente atípicos. El detector
   los aísla **sin mirar las etiquetas**.
   → Caza las **inyecciones masivas** de registros falsos.

> **Resultado en el POC:** combinando la Capa 1 (criptografía) y la Capa 2 (IA),
> detectamos el **100% del veneno** en el ataque de 3 vectores. La criptografía
> frena la inyección y la manipulación de forma determinística; la IA caza al
> **infiltrado corrupto** que logró firmar datos falsos con clave válida — el
> único caso que la firma no puede detectar. Lo dudoso se pone en cuarentena para
> revisión humana, no se borra a ciegas.

> 🧩 **Modelo de amenaza (3 vectores) — implementado en `ataque_poisoning.py`:**
> (1) inyección externa sin firma válida, (2) manipulación de etiquetas que rompe
> la firma, (3) infiltrado con clave legítima. Demuestra por qué **ninguna capa
> sola basta** y se necesita defensa en profundidad.

---

### 💪 CAPA 3 — Entrenamiento robusto (resistir aunque quede algo de veneno)

**Objetivo:** que el modelo sea difícil de mover incluso con datos contaminados.

- **Reentrenamiento con datos saneados:** excluimos los registros en cuarentena y
  reentrenamos. *(En el POC recuperamos por completo el desempeño perdido: el
  recall vuelve a ~70%, igual o mejor que la línea base limpia.)*
- **Gate de despliegue automático** ✅ *(implementado: `defensa.gate_despliegue`)*:
  un modelo nuevo **solo se promueve a producción si mantiene el recall** sobre el
  conjunto dorado verificado (mínimo absoluto + caída máxima tolerada). Si el
  envenenamiento bajó el recall, el despliegue **se bloquea automáticamente** — así
  el ataque se vuelve inútil aunque logre colarse.
- **Técnicas de ML robusto (roadmap):** entrenamiento con poda de outliers, límites
  de influencia por registro, *ensemble* de modelos y aprendizaje robusto a ruido
  de etiquetas.

---

### 📡 CAPA 4 — Monitoreo continuo (que no vuelva a pasar)

**Objetivo:** vigilancia permanente, porque el atacante volverá a intentarlo.
✅ *Implementado en código (`src/monitoreo.py`): drift con test KS, PSI y
diferencia de proporción, con severidad (OK/ALERTA/CRÍTICO) y acción recomendada.*

- **Detección de drift:** si la distribución de datos o de predicciones cambia
  bruscamente (p.ej. de repente muchos mataderos pasan a "seguros"), salta una
  **alerta automática** que escala a un inspector (nunca actúa sola).
- **Auditoría cruzada campo vs. modelo:** un % de inspecciones se hace al azar
  (no solo las que el modelo prioriza). Si el modelo dijo "seguro" y en campo era
  insalubre, ese caso alimenta el detector y **castiga la fuente** del dato malo.
- **Humano en el bucle (human-in-the-loop):** las decisiones de alto impacto y los
  casos en cuarentena los revisa un inspector. La IA **prioriza**, el humano
  **decide**. Esto sostiene la responsabilidad legal y la confianza pública.
- **Transparencia y explicabilidad:** cada predicción viene con las razones
  (variables que más pesaron). Un modelo que se explica es un modelo que se puede
  auditar y defender ante la ciudadanía.

---

## Por qué esto SALVA la iniciativa (el argumento para el jurado)

1. **Recupera la confianza con evidencia, no con promesas.** Mostramos números:
   ataque → caída del recall → defensa → recuperación medible.
2. **Es anti-frágil:** asume que habrá ataques y aun así garantiza decisiones
   auditables. No depende de que "los datos sean perfectos".
3. **Rinde cuentas:** trazabilidad total + humano en el bucle = responsabilidad
   clara. Clave para una entidad pública.
4. **Es viable y por fases:** las reglas de dominio y la semilla dorada se
   implementan ya; el ML robusto es el roadmap. No hay que botar lo construido.
5. **Ataca la raíz (la corrupción):** al firmar y trazar cada dato y castigar las
   fuentes que mienten, encarece y expone el ataque. Deja de ser rentable manipular.

---

## Innovación diferencial

- **"Semilla de confianza" como ancla de verdad:** un pequeño núcleo verificado en
  campo, blindado criptográficamente, contra el cual se valida todo lo demás.
- **Cuarentena en vez de borrado:** ningún dato se elimina a ciegas; lo dudoso va a
  revisión humana → cero falsos borrados, auditoría completa.
- **Gate de despliegue automático:** ningún modelo llega a producción si empeora el
  recall sobre la verdad de campo. El envenenamiento se vuelve inútil.

---

## Roadmap de implementación (realista)

| Fase | Plazo | Acciones |
|------|-------|----------|
| **0 — Contención** | Semana 1 | Congelar reentrenamientos, activar reglas de dominio, crear semilla dorada |
| **1 — Detección** | Mes 1 | Desplegar los 3 detectores + cuarentena + auditoría cruzada |
| **2 — Gobernanza** | Mes 2-3 | Firma digital de fuentes, log inmutable, control de acceso |
| **3 — Robustez** | Mes 3-6 | ML robusto, monitoreo de drift, dashboards, human-in-the-loop formal |

---

*La tecnología no falló: le faltó blindaje. Este sistema se lo da.*
