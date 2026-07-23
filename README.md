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

## 👥 Equipo

- Yamid GT — [@YamidGT](https://github.com/YamidGT)
- Andrés — [@andres456s](https://github.com/andres456s)
- Alejandro Higuera C — [@DarkNightSoldier](https://github.com/DarkNightSoldier)

*Cámara de Comercio de Bogotá — Reto 4.*
