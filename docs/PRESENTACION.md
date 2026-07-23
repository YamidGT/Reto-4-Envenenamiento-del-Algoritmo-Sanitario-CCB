# 🎤 GUION DE PRESENTACIÓN — Pitch para el jurado

**Duración objetivo: 5-7 min de pitch + demo en vivo. 8-10 diapositivas.**

> Regla de oro: **cuenta una historia** (problema → villano → héroe → evidencia),
> no una lista de features. Y **muestra la demo corriendo**: eso gana.

---

## 🎬 Estructura narrativa (los 3 actos)

**Gancho inicial (di esto tal cual):**
> *"La Secretaría de Salud construyó una IA para proteger a los ciudadanos... y unos
> corruptos la convirtieron en cómplice. Sin hackear un solo servidor. Les vamos a
> mostrar cómo lo hicieron —y cómo lo detenemos."*

---

## 📊 Diapositivas

### Slide 1 — Portada
- Título: **"Blindando la IA sanitaria contra el envenenamiento de datos"**
- Reto 4 · CCB · Nombres del equipo + GitHub.

### Slide 2 — El problema (30 seg)
- La IA prioriza inspecciones según riesgo. Gran idea, recursos limitados.
- **El ataque:** Data Poisoning. No hackean el servidor, **corrompen los datos**.
- Frase clave: *"insalubre etiquetado como seguro = ciudadano en riesgo"*.

### Slide 3 — ¿Qué es Data Poisoning? (analogía, 30 seg)
- **El perro guardián:** si entrenas al perro con fotos de ladrones etiquetadas como
  "amigos", aprende a dejarlos entrar. Eso le hicieron a la IA.
- Dos vectores: **cambiar etiquetas** + **inyectar datos falsos**.

### Slide 4 — Impacto (con NÚMEROS de la demo)
- Tabla del "Resumen Ejecutivo" de la demo:
  | Modelo | Recall (peligrosos detectados) | Peligrosos que se escapan |
  |--------|-------|------|
  | Limpio | ~69% | 57 |
  | **Envenenado** 💥 | **~47%** | **98** |
- Frase: *"41 establecimientos peligrosos adicionales dejarían de ser inspeccionados."*

### Slide 5 — Nuestra solución (la gran idea)
- **"No confiamos ciegamente en el dato: lo firmamos, lo auditamos, lo validamos
  contra la verdad de campo y vigilamos el modelo."**
- El diagrama de las **4 capas** (Gobernanza → Detección → Robustez → Monitoreo).

### Slide 6 — Cómo detectamos el veneno (Capa 2, el corazón)
- 3 detectores independientes:
  1. **Verdad de campo** (semilla de confianza) → caza etiquetas cambiadas.
  2. **Reglas de dominio** (el inspector experto) → caza inyecciones.
  3. **Anomalías** (Isolation Forest) → caza lo estadísticamente raro.
- Consenso → **cuarentena** (no borrado a ciegas, revisión humana).

### Slide 7 — 🖥️ DEMO EN VIVO
- Corre `python src/demo.py` en pantalla.
- Señala: ACTO 1 (limpio) → ACTO 2 (ataque, recall se desploma) → ACTO 3
  (defensa: **~78% del veneno detectado, ~61% del desempeño recuperado**).
- *Este es el momento que gana el reto. Que se vea correr.*

### Slide 8 — Por qué SALVA la iniciativa
- Recupera confianza **con evidencia, no promesas**.
- Es **anti-frágil**: asume ataques y sigue siendo confiable.
- **Rinde cuentas**: trazabilidad + humano en el bucle.
- **Ataca la corrupción de raíz**: firmar y castigar fuentes que mienten.

### Slide 9 — Innovación + Roadmap
- Diferenciadores: **semilla de confianza**, **cuarentena vs. borrado**,
  **gate de despliegue** (ningún modelo entra a producción si empeora el recall).
- Roadmap por fases: Contención (semana 1) → Detección (mes 1) → Gobernanza →
  Robustez.

### Slide 10 — Cierre
- *"La tecnología no falló: le faltó blindaje. Nosotros se lo damos."*
- Gracias + repo GitHub + equipo.

---

## 🗣️ Reparto en tarima (sugerencia)

- **Persona 1:** Slides 1-4 (problema e impacto). Engancha.
- **Persona 2:** Slides 5-7 (solución + **corre la demo**). El técnico.
- **Persona 3:** Slides 8-10 (valor, innovación, cierre). El visionario.

---

## ❓ Preguntas probables del jurado (y respuestas)

**"¿Y si envenenan también la semilla de confianza?"**
> Está blindada: verificada físicamente en campo, firmada criptográficamente y
> aislada del pipeline. Comprometerla exige corromper inspectores en persona, no
> solo tocar una base de datos — un ataque mucho más caro y expuesto.

**"¿Esto no genera falsas alarmas / inspecciones de más?"**
> Sí, y es deliberado: en salud pública preferimos inspeccionar de más que dejar
> pasar un peligroso. Además, la cuarentena la revisa un humano; no se actúa a ciegas.

**"¿Es caro o difícil de implementar?"**
> No. Las reglas de dominio y la semilla dorada se activan en semanas y no botan lo
> construido. El ML robusto es el roadmap. Es evolución, no reinicio.

**"¿Cómo sé que el modelo ya es confiable de nuevo?"**
> Porque lo validamos contra el conjunto dorado verificado en campo, y ningún modelo
> se despliega si empeora el recall. La confianza es medible y auditable.

**"¿Por qué recall y no exactitud (accuracy)?"**
> Porque el error grave es el falso negativo: decir "seguro" a algo peligroso. La
> exactitud puede verse bien mientras se escapan los peligrosos; el recall no miente.

---

## ✅ Checklist antes de subir a tarima

- [ ] La demo corre sin errores en el portátil que vamos a usar.
- [ ] Tenemos los números de NUESTRA corrida anotados (recall limpio/envenenado/recuperado).
- [ ] Cada quien sabe su parte y los tiempos.
- [ ] Slide del diagrama de 4 capas se ve claro.
- [ ] Frase de cierre memorizada.
