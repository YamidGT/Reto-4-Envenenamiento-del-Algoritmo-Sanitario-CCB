# 📌 CONTEXTO DEL PROYECTO — Para el equipo

> Léelo completo antes de empezar. En 5 minutos entiendes TODO el reto y qué
> hicimos. Al final hay una lista de "quién hace qué" para las próximas horas.

---

## 1. ¿Cuál es el reto? (en cristiano)

La **Secretaría de Salud** creó una IA que decide **qué restaurantes, mataderos y
fábricas de alimentos inspeccionar primero**, según su nivel de riesgo. Es una
gran idea: recursos limitados → priorizar lo más peligroso.

**El problema:** unos competidores deshonestos **hackearon el flujo de datos** que
alimenta a la IA y le están metiendo **datos falsos** (esto se llama
**Data Poisoning** / envenenamiento de datos). ¿Con qué fin? Que la IA aprenda que
sus establecimientos **insalubres son "seguros"**, para que **nunca los visiten**
los inspectores. Es corrupción, pero por la vía del algoritmo.

**Lo que nos pide el jurado:**
> *¿Cómo salvas la credibilidad de esta tecnología y evitas que la vuelvan a
> manipular?*

No es solo un reto técnico: es una propuesta de **cómo rescatar un proyecto de
modernización del Estado** que está a punto de cancelarse por falta de confianza.

---

## 2. ¿Qué es "Data Poisoning"? (para explicarlo sin tecnicismos)

Imagina que entrenas a un perro guardián mostrándole fotos de ladrones. Si alguien
**mete a escondidas fotos de ladrones etiquetadas como "amigo"**, el perro
aprenderá a dejar entrar a esos ladrones. Eso es data poisoning: **corromper los
datos con los que aprende la IA** para que tome decisiones equivocadas *a favor del
atacante*.

Dos formas de hacerlo (las dos las simulamos en el código):

1. **Cambiar etiquetas (label flipping):** toman un restaurante que SÍ es peligroso
   y en los datos lo marcan como "seguro".
2. **Inyectar registros falsos:** inventan establecimientos con perfil peligroso
   pero etiquetados como "seguros", para confundir a la IA.

---

## 3. Nuestra solución en una frase

> **No confiamos ciegamente en el dato: lo firmamos, lo auditamos, lo validamos
> contra una "semilla de verdad" verificada en campo, y vigilamos el modelo en
> tiempo real. El envenenamiento deja huellas estadísticas, y nosotros las cazamos.**

La solución es un **sistema de defensa en 4 capas** (ver [ESTRATEGIA.md](ESTRATEGIA.md)):

| Capa | Nombre | Qué hace |
|------|--------|----------|
| 1 | **Gobernanza del dato** | Firma digital + trazabilidad de cada dato (¿de dónde vino? ¿quién lo tocó?) |
| 2 | **Detección de veneno** | 3 detectores que marcan datos sospechosos y los ponen en cuarentena |
| 3 | **Entrenamiento robusto** | Reentrena el modelo SIN los datos envenenados |
| 4 | **Monitoreo continuo** | Vigila el modelo con un "conjunto dorado" y alerta si algo raro pasa |

---

## 4. ¿Qué construimos? (el POC que funciona)

Un programa en Python que **demuestra en vivo** el ataque y la defensa. No es teoría:
lo corres y ves los números. Está en la carpeta `src/`:

| Archivo | Qué hace |
|---------|----------|
| `generar_datos.py`   | Inventa 3.000 establecimientos realistas con su nivel de riesgo real |
| `modelo.py`          | Entrena la IA que predice el riesgo |
| `ataque_poisoning.py`| Simula el ataque de los competidores deshonestos |
| `defensa.py`         | **Nuestro sistema de defensa** (lo más importante) |
| `demo.py`            | Junta todo y cuenta la historia en 3 actos |

### Cómo correrlo (2 minutos)

```bash
pip install -r requirements.txt
python src/demo.py
```

Verás 3 actos:
- **ACTO 1:** la IA limpia funciona bien.
- **ACTO 2:** el ataque envenena los datos → la IA empieza a dejar pasar
  establecimientos peligrosos como "seguros" (el recall se desploma ~22 puntos).
- **ACTO 3:** nuestra defensa detecta ~78% del veneno, limpia los datos y
  **recupera ~61%** del desempeño perdido. Confianza restaurada.

> 💡 Los números concretos salen al correr la demo. Úsalos en la presentación:
> son nuestra evidencia.

---

## 5. Qué NO es (para no confundirnos)

- **No** estamos hackeando nada real. Todo es simulado y sintético.
- **No** necesitamos datos reales de la Secretaría; los generamos.
- **No** es solo código: el 50% del puntaje es la **propuesta al jurado**
  (la narrativa de gobernanza, confianza y anti-corrupción).

---

## 6. Glosario rápido (por si preguntan)

- **Recall (sensibilidad):** de todos los establecimientos peligrosos que existen,
  ¿cuántos detecta la IA? Es NUESTRA métrica clave: un peligroso no detectado =
  un ciudadano en riesgo.
- **Falso negativo:** decir "seguro" a algo que es peligroso. **El error más grave.**
- **Isolation Forest:** algoritmo que detecta datos "raros"/atípicos.
- **Semilla / conjunto dorado:** un conjunto pequeño de inspecciones **verificadas
  por humanos en campo**, blindado, que usamos como "fuente de verdad".

---

## 7. Reparto de trabajo sugerido (tenemos ~2h)

| Persona | Tarea | Entregable |
|---------|-------|-----------|
| **Yamid** | Repo + demo corriendo + README | Que `python src/demo.py` funcione y se vea bonito |
| **Andrés** | Presentación (slides) usando [PRESENTACION.md](PRESENTACION.md) | 8-10 diapositivas |
| **Alejandro** | Dominar la [ESTRATEGIA.md](ESTRATEGIA.md) + preparar respuestas a preguntas del jurado | Speech de las 4 capas |

**Todos:** correr la demo una vez y anotar los números para citarlos en vivo.

---

## 8. Estado actual

- [x] Estructura del repo
- [x] Generador de datos sintéticos
- [x] Modelo de riesgo
- [x] Simulación del ataque (2 vectores)
- [x] Sistema de defensa (3 detectores + reentrenamiento)
- [x] Demo end-to-end funcionando
- [x] Documento de estrategia para el jurado
- [x] Guion de presentación
- [ ] Slides finales (Andrés)
- [ ] Ensayar el pitch (todos)

¡A darle! 🚀
