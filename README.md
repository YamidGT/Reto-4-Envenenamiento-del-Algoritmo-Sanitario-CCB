# 🛡️ Reto 4 — Envenenamiento del Algoritmo Sanitario (CCB)

**Blindaje de un modelo de IA de inspección sanitaria contra ataques de Data Poisoning.**

> La Secretaría de Salud usa IA para priorizar qué restaurantes, mataderos y fábricas de
> alimentos inspeccionar. Un grupo de competidores deshonestos inyectó datos falsos
> (*Data Poisoning*) para que establecimientos insalubres sean clasificados como
> **"Seguros"** y así evitar inspecciones. Este proyecto **demuestra el ataque**, lo
> **detecta**, **recupera la confianza** en el modelo y propone un **blindaje** para que no
> vuelva a ocurrir.

---

## 🎯 ¿Qué entregamos?

1. **POC funcional** que simula el ataque real y la defensa (código Python ejecutable).
2. **Sistema de defensa en 4 capas**: gobernanza del dato, detección de envenenamiento,
   entrenamiento robusto y monitoreo continuo.
3. **Estrategia para el jurado** ([docs/ESTRATEGIA.md](docs/ESTRATEGIA.md)) y
   **guion de presentación** ([docs/PRESENTACION.md](docs/PRESENTACION.md)).

---

## 🚀 Ejecutar la demo (2 minutos)

```bash
pip install -r requirements.txt
python src/demo.py
```

Verás en consola: el modelo limpio funcionando, el ataque envenenando el pipeline,
el modelo comprometido dejando pasar establecimientos peligrosos, y finalmente el
**sistema de defensa detectando y neutralizando** el envenenamiento.

Dashboard visual opcional:

```bash
streamlit run app/dashboard.py
```

---

## 🧠 La idea en una frase

> **No confiamos ciegamente en el dato: lo firmamos, lo auditamos, lo validamos contra un
> "conjunto dorado" de verdad de campo, y vigilamos el modelo en tiempo real.
> El envenenamiento deja huellas estadísticas — y nosotros las cazamos.**

---

## 🏗️ Estructura del repositorio

```
├── README.md                  # Este archivo
├── requirements.txt           # Dependencias
├── src/
│   ├── generar_datos.py       # Genera dataset sintético de establecimientos
│   ├── modelo.py              # Entrena el modelo de riesgo sanitario
│   ├── ataque_poisoning.py    # Simula el ataque de envenenamiento
│   ├── defensa.py             # Sistema de defensa (4 capas)
│   └── demo.py                # Orquesta la historia completa (ATAQUE vs DEFENSA)
├── app/
│   └── dashboard.py           # Dashboard visual (Streamlit)
└── docs/
    ├── ESTRATEGIA.md          # Propuesta de solución para el jurado
    └── PRESENTACION.md        # Guion de la presentación (pitch)
```

---

## 🛠️ Próximas tareas técnicas (mejora continua)

Reparto en 3 líneas paralelas que tocan archivos distintos (para evitar choques de Git).

### Yamid — Arreglar el corazón de la detección (`src/defensa.py`, `src/modelo.py`)

- [ ] **Desacoplar el Detector B del atacante.** Reemplazar los umbrales de
  `deteccion_por_reglas()` por valores basados en normativa sanitaria real (ej.
  INVIMA / Resolución 2674 de 2013 sobre cadena de frío y buenas prácticas), no
  en los rangos exactos que usa `_fabricar_registros_falsos()`. Meta: que el
  detector funcione aunque cambien los parámetros del ataque.
- [ ] **Explicabilidad real.** En `modelo.py`, añadir `importancia_variables(modelo)`
  que devuelva `modelo.feature_importances_` ordenado, y usarla en `demo.py` para
  imprimir el top 5 de variables que más pesan en la predicción.
- [ ] Validar que `python src/demo.py` siga dando resultados coherentes tras el
  cambio de umbrales.

### Andrés — Robustez y evidencia cuantitativa (archivo nuevo `src/robustez.py`)

- [ ] Script que corra el pipeline completo (`envenenar` → `entrenar_modelo` →
  `detectar_envenenamiento` → reentrenar) con varias semillas e intensidades de
  ataque (tasas 0.05, 0.15, 0.25, 0.35 × 5 semillas cada una).
- [ ] Guardar los resultados (recall limpio/envenenado/recuperado, % de veneno
  detectado) en un DataFrame y exportarlo a CSV.
- [ ] Añadir al dashboard (`app/dashboard.py`) un gráfico de recall recuperado vs.
  intensidad del ataque, para demostrar que la defensa no depende de un solo run
  con suerte.
- [ ] Extra si hay tiempo: tabla en el dashboard con los registros en cuarentena
  y la razón (qué detector los marcó).

### Alejandro — Convertir las Capas 1 y 4 de prosa a código (archivos nuevos
`src/gobernanza.py`, `src/monitoreo.py`)

- [x] `src/gobernanza.py`: `firmar_registro(registro, clave_secreta)` (HMAC-SHA256
  del registro, simula la firma digital de la fuente) y
  `verificar_firma(registro, firma, clave_secreta)`. Incluye además canonicalización
  determinista, `LibroMayor` (log inmutable con encadenamiento de hash) y un
  `gate_ingesta` que rechaza registros sin firma válida (los `FAKE-*` del ataque).
- [x] `src/monitoreo.py`: `detectar_drift(distribucion_referencia, distribucion_actual)`
  combina diferencia de proporción de "seguros", test KS y PSI para disparar
  una alerta con severidad (OK/ALERTA/CRÍTICO) y una acción recomendada
  (human-in-the-loop: nunca actúa solo).
- [x] Ejemplo ejecutable en `if __name__ == "__main__":` de cada archivo — correr
  `python src/gobernanza.py` y `python src/monitoreo.py` para verlas sueltas.
  Detalle del diseño y su alineación con ISO 27001/42001, NIST y el EU AI Act en
  [docs/PLAN_ALEJANDRO.md](docs/PLAN_ALEJANDRO.md).

**Coordinación:** cada quien trabaja en archivos separados para poder hacer
`git pull` sin conflictos. Commits pequeños y descriptivos
(`feat: detector B basado en normativa real`, etc.).

---

## 👥 Equipo

- Yamid GT — [@YamidGT](https://github.com/YamidGT)
- Andrés — [@andres456s](https://github.com/andres456s)
- Alejandro Higuera C — [@DarkNightSoldier](https://github.com/DarkNightSoldier)

*Cámara de Comercio de Bogotá — Reto 4.*
