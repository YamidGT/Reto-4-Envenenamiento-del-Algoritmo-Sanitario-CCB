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

Verás en consola: el modelo limpio funcionando, el ataque de **3 vectores**
envenenando el pipeline, el modelo comprometido dejando pasar establecimientos
peligrosos, y finalmente la **defensa en profundidad** (criptografía + IA)
neutralizando el 100% del envenenamiento, con el **gate de despliegue bloqueando**
el modelo malo antes de que llegue a producción.

Generar las gráficas para las diapositivas:

```bash
python src/experimentos.py
```

Módulos de gobernanza y monitoreo (se pueden correr sueltos ante el jurado):

```bash
python src/procedencia.py   # LibroMayor: firma + trazabilidad inmutable (Capa 1)
python src/monitoreo.py     # Detección de drift con alerta y acción (Capa 4)
```

Dashboard visual interactivo:

```bash
streamlit run app/dashboard.py
```

---

## 📊 Resultados de la demo (evidencia para el jurado)

| Escenario | Recall (peligrosos detectados) | Peligrosos que se escapan |
|-----------|-------------------------------|---------------------------|
| 🟢 Modelo limpio | ~69% | 57 |
| 🔴 **Envenenado** (ataque 15%) | **~51%** 💥 | 90 |
| 🛡️ **Recuperado** (con defensa) | **~70%** ✅ | 55 |

- **Capa 1 (criptografía):** neutraliza inyección + manipulación de forma
  determinística (100%).
- **Capa 2 (IA):** caza al infiltrado corrupto que firmó datos falsos con clave válida.
- **Detección global: 100% del ataque** · **el gate bloquea** el modelo envenenado.
- **Robustez:** con un ataque del 40%, el modelo sin defensa colapsa a ~15% de
  recall; **con defensa se mantiene sobre 60%** (ver `figuras/robustez.png`).

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
│   ├── gobernanza.py          # 🔒 CAPA 1: firma digital HMAC (autenticidad + integridad)
│   ├── procedencia.py         # 🔒 CAPA 1: LibroMayor inmutable + gate de ingesta (trazabilidad)
│   ├── modelo.py              # Modelo de riesgo + explicabilidad (importancia de variables)
│   ├── ataque_poisoning.py    # Ataque de 3 vectores (inyección, manipulación, infiltrado)
│   ├── defensa.py             # 🛡️ Defensa en profundidad (Capa 1 + Capa 2 + gate de despliegue)
│   ├── monitoreo.py           # 📡 CAPA 4: detección de drift (KS, PSI) con alerta y acción
│   ├── experimentos.py        # Genera las gráficas (curva de robustez, resumen)
│   └── demo.py                # Orquesta la historia completa (ATAQUE vs DEFENSA)
├── app/
│   └── dashboard.py           # Dashboard visual interactivo (Streamlit)
├── figuras/                   # Gráficas PNG para las diapositivas (las crea experimentos.py)
└── docs/
    ├── CONTEXTO.md            # Onboarding del equipo (leer primero)
    ├── ESTRATEGIA.md          # Propuesta de solución para el jurado
    ├── PRESENTACION.md        # Guion de la presentación (pitch)
    └── PLAN_ALEJANDRO.md      # Diseño de gobernanza/monitoreo y alineación normativa
```

---

## ✅ Estado de implementación (las 4 capas, en código)

| Capa | Componente | Estado |
|------|-----------|--------|
| 1 | Firma digital HMAC-SHA256 (`gobernanza.py`) | ✅ Implementado |
| 1 | LibroMayor inmutable + gate de ingesta (`procedencia.py`) | ✅ Implementado |
| 2 | Detección: referencia + reglas + anomalías (`defensa.py`) | ✅ Implementado |
| 3 | Reentrenamiento robusto + gate de despliegue (`defensa.py`) | ✅ Implementado |
| 4 | Monitoreo de *drift* con alerta y acción (`monitoreo.py`) | ✅ Implementado |
| — | Explicabilidad (importancia de variables, `modelo.py`) | ✅ Implementado |
| — | Ataque de 3 vectores (`ataque_poisoning.py`) | ✅ Implementado |
| — | Curva de robustez y gráficas (`experimentos.py`) | ✅ Implementado |
| — | Dashboard interactivo (`dashboard.py`) | ✅ Implementado |

> 📐 **Alineación normativa:** el diseño de gobernanza y monitoreo se mapea a
> **ISO/IEC 27001** (seguridad de la información), **ISO/IEC 42001** (gestión de
> IA), **NIST AI RMF** y el **EU AI Act**. Detalle en
> [docs/PLAN_ALEJANDRO.md](docs/PLAN_ALEJANDRO.md).

**Roadmap (mejora continua):** firma en origen desde HSM/KMS en producción,
integración de las reglas de dominio con normativa INVIMA (Resolución 2674 de 2013)
y tablero de auditoría con el LibroMayor en vivo.

---

## 👥 Equipo

- Yamid GT — [@YamidGT](https://github.com/YamidGT)
- Andrés — [@andres456s](https://github.com/andres456s)
- Alejandro Higuera C — [@DarkNightSoldier](https://github.com/DarkNightSoldier)

*Cámara de Comercio de Bogotá — Reto 4.*
