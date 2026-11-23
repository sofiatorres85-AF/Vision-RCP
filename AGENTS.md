# AGENTS.md — Reglas y contexto para agentes de IA

Guía para que cualquier agente trabaje en este repositorio sin romper nada.
Documento viviente: si cambias algo estructural, actualízalo en el mismo
commit.

---

## 1. Contexto (Context Spec)

**Nombre:** Sistema de análisis de técnica de RCP.
**Objetivo de grado:** evaluar con una cámara web la técnica de reanimación
cardiopulmonar en adultos (frecuencia, profundidad, posición de manos, retorno
torácico y rectitud de brazos) y dar retroalimentación inmediata al alumno.

- **Idioma:** español. Los nombres de archivos, funciones, comentarios,
  mensajes de la interfaz y la documentación están en español. No traduzcas
  nada al inglés salvo que se pida explícitamente.
- **Stack:** Python 3, OpenCV, MediaPipe Pose y Tkinter. Sin frameworks web y
  sin base de datos.
- **Arquitectura:** monolito de escritorio, un solo proceso local, sin
  comunicación por red.
- **Parámetros de negocio (AHA 2025):** frecuencia 100-120 cpm y profundidad
  5-6 cm. Son valores fijos y residen en `rcp/configuracion.py`; nunca en la
  interfaz ni hardcodeados en otro módulo.
- **Referencia funcional:** antes de codificar, lee `docs/01_requisitos.md` y
  `docs/02_historias_usuario.md` (solo lectura; ver §3).

---

## 2. Estructura

```
main.py                 punto de entrada (lleva Tkinter al mainloop)
ejecutar_rcp.bat        lanzador Windows (define Tcl/Tk, ejecuta main.py)
requirements.md         dependencias
AGENTS.md               este documento
README.md               presentación y guía rápida
rcp/                    9 módulos (más __init__.py)
pruebas/                test_criterios.py y su documentación
docs/                   documentación del proyecto
venv/                   entorno virtual (ignorado por Git)
models/                 modelos .task de MediaPipe (ignorados por Git)
```

`rcp/__init__.py` solo marca el paquete; no contiene lógica.

### Módulos de `rcp/` y su responsabilidad

| Archivo | Responsabilidad | ¿Importa OpenCV? | ¿Importa Tkinter? |
|---------|-----------------|-------------------|--------------------|
| `configuracion.py` | Índices de landmarks y umbrales AHA | no | no |
| `captura.py` | Apertura y lectura de la cámara | sí | no |
| `modelos.py` | Descarga y creación de modelos MediaPipe | no | no |
| `procesamiento.py` | ArUco, extracción de landmarks, dibujo | sí | no |
| `analisis.py` | Señal, cpm, profundidad, ángulos, retorno | **no** | no |
| `reglas.py` | RN-01 a RN-06, estados ok/alerta/error/espera | **no** | no |
| `retroalimentacion.py` | Mensaje principal y color | **no** | no |
| `sesion.py` | Ciclo de vida, errores con hora, resumen | **no** | no |
| `interfaz.py` | GUI Tkinter y orquestación del fotograma | sí | sí |

**Regla clave:** `analisis`, `reglas`, `retroalimentacion` y `sesion` **no deben
importar OpenCV ni Tkinter**. Eso permite ejecutar las pruebas sin cámara ni
pantalla y es lo que garantiza el criterio CP-16 / RNF-07. Si agregas una
dependencia ahí, rompes el aislamiento.

---

## 3. Límites (Boundary Spec)

- **NO** implementes base de datos ni persistencia. El registro es manual en
  CSV/Excel (ver Limitaciones del proyecto).
- **NO** añadas dependencias que requieran GPU. El sistema debe correr en CPU
  sin GPU dedicada (RNF-06).
- **NO** modifiques `docs/` por tu cuenta. Si necesitas un cambio de requisito,
  umbral, regla o arquitectura, propónlo y espera aprobación humana. Esta regla
  aplica también a la trazabilidad (§6).
- **NO** modifiques las pruebas existentes para que pasen. Si una prueba falla,
  corrige el código de producción.
- **NO** hardcodees los valores de la AHA. Léelos desde
  `rcp/configuracion.py`. Si necesitas un umbral nuevo, agrega un campo en ese
  archivo con el número de requisito en el comentario.
- **NO** elimines ni renombres módulos de `rcp/` sin actualizar `main.py` y
  `pruebas/`, y sin proponer la actualización correspondiente de `docs/`.
- **NO** fusiones `analisis`, `reglas`, `retroalimentacion` o `sesion` en un
  solo archivo: incumple CP-16.
- **NO** reemplaces la API de MediaPipe Tasks por `mp.solutions` (eliminada en
  1.x) ni instales `mediapipe<1.0` sin avisar.
- **NO** subas cambios de `pruebas/` hasta que el usuario lo autorice
  expresamente.

---

## 4. Calidad (Quality Spec — ISO/IEC 25010)

- **Eficiencia (RNF-01):** cada fotograma debe procesarse en menos de 100 ms.
  Si tu código introduce un cuello de botella, debes justificarlo.
- **Exactitud (RNF-02, RNF-03):** la frecuencia debe cumplir un error máximo de
  5 % (≈ 6 cpm a 120 cpm) y la profundidad no debe desviarse más de ±0,5 cm.
- **Mantenibilidad (RNF-07):** organiza el código en módulos separados
  (`rcp/captura.py`, `rcp/procesamiento.py`, `rcp/analisis.py`,
  `rcp/reglas.py`, `rcp/retroalimentacion.py`, `rcp/sesion.py`,
  `rcp/interfaz.py`, `rcp/configuracion.py`, `rcp/modelos.py`). No mezcles
  responsabilidades en un solo archivo.
- **Usabilidad (RNF-04):** la interfaz debe ser clara, con códigos de color
  (verde/rojo/amarillo) y mensajes breves (ej. "Presiona más hondo").

### 4.1 Convenciones de código

- **Español** en identificadores (`AnalizadorRCP`, `regla_profundidad`) y en
  los docstrings. Comenta el *por qué*, no el *qué*.
- **Docstrings** en todos los módulos, clases y funciones públicas, citando el
  requisito que implementan (ej. `"RN-02 / RF-04 / CA-04"`), en formato Google
  o NumPy.
- **`dataclass`** para datos (`Configuracion`, `Metricas`, `ResultadoRegla`,
  `ErrorDetectado`, `ResumenSesion`). Usa `frozen=True` cuando sea inmutable.
- **Tipo completo** en las firmas (`Optional[float]`, `List[...]`).
- **Sin excepciones genéricas silenciosas**: si capturas una, deja mensaje.
- **Nombres de variables** en minúscula con guion bajo; constantes en
  mayúsculas.
- Mantén los nombres de la interfaz existentes (`etiqueta_*`, `boton_*`) para
  no romper referencias.

### 4.2 Pruebas

- `pruebas/test_criterios.py` es un **script plano**, no un framework: usa
  `comprobar(nombre, condicion)` y termina con un resumen `PASS`/`FALLA`.
  Devuelve código de salida distinto de cero si algo falla.
- Cada funcionalidad nueva agrega comprobaciones para sus criterios CA-xx.
- No modifiques las comprobaciones existentes para que pasen; corrige el código
  de producción. La única excepción es que el requisito haya cambiado de forma
  aprobada.
- No migres las pruebas a otro framework sin aprobación.

---

## 5. Seguridad (OWASP)

- **Sandboxing:** ejecuta comandos de shell solo dentro del entorno virtual de
  Python (venv). No instales paquetes globalmente.
- **Permisos:** pide confirmación antes de ejecutar comandos que modifiquen
  archivos fuera de `rcp/`.
- **Secretos:** nunca escribas claves API ni rutas absolutas de tu máquina en
  el código. Usa variables de entorno o rutas relativas.
- **Inyección:** trata los datos de entrada de la cámara (frames) como no
  confiables. Valida tipos y rangos antes de procesarlos.

---

## 6. Flujo de trabajo (basado en IEEE 3398 y SDD)

**Planificación.** Antes de escribir código para una nueva HU, presenta un plan
con: (1) archivos a modificar, (2) estrategia de pruebas, (3) verificación de
que cumples los RNF.

**Commits.**

- Escribe los mensajes en español y menciona el requisito que cubren (`RF-04`,
  `CA-09`, `CP-11`, etc.).
- Los cambios en `pruebas/` no se suben hasta que el usuario lo autorice
  expresamente.
- `venv/`, `models/*.task`, `__pycache__/` y `*.csv` están en `.gitignore`; no
  los agregues al control de versiones.

**Trazabilidad.** Cada cambio funcional debe rastrearse en `docs/`, pero la IA
no edita `docs/` por su cuenta: propone el cambio y espera aprobación humana.

- ¿Agregaste un requisito? → propón su fila RF/RNF y su criterio de aceptación
  en `docs/01_requisitos.md`.
- ¿Cambiaste un umbral? → propón la actualización de `docs/04_parametros_aha.md`.
- ¿Agregaste una regla nueva? → propón la RN en ambos documentos.

---

## 7. Comandos

```bat
:: entorno
venv\Scripts\activate.bat
pip install "opencv-contrib-python>=4.9" "mediapipe>=1.0" "numpy>=1.26" "pillow>=10.0"

:: aplicación (o usar ejecutar_rcp.bat)
.\venv\Scripts\python main.py

:: pruebas de criterios de aceptación
.\venv\Scripts\python -m pruebas.test_criterios

:: verificación de sintaxis de un archivo
.\venv\Scripts\python -m py_compile <archivo.py>

:: verificación de sintaxis de todo el proyecto
.\venv\Scripts\python -m compileall -q main.py rcp
```

**Siempre** usa el Python del venv (`.\venv\Scripts\python` o el venv
activado). El `python` global no tiene `cv2` instalado y fallará.

---

## 8. Problemas conocidos (pitfalls)

| Pitfall | Detalle |
|---------|---------|
| Tkinter en el venv | Python 3.13 no encuentra `init.tcl`. Requiere `TCL_LIBRARY` y `TK_LIBRARY`; ya están en `ejecutar_rcp.bat` y en los scripts de activación del venv. No "arregles" eso reinstalando. |
| PowerShell vs CMD | `$env:X=` es PowerShell; `set X=` es CMD. `&&` no existe en CMD en versiones viejas de Windows. |
| MediaPipe 1.x | Solo Tasks API (`mediapipe.tasks.python.vision`). `detect_for_video` exige marcas de tiempo **monotónicas crecientes**; no pases `time.time()`. |
| Escala ArUco | Sin marcador visible no hay centímetros: el sistema degrada a ~10 px/cm y avisa. No finjas que hay precisión. |
| Modelo sintético de pruebas | Con brazos rígidos las muñecas se mueven lo mismo que los hombros. Si mueves las muñecas más que los hombros, la profundidad medida queda inflada. |
| Errores repetidos | `Sesion.registrar_reglas` usa enfriamiento (`enfriamiento_error_s`); si "solo aparece un error" es comportamiento esperado. |
| Cámara Windows | Usa `cv2.CAP_DSHOW`; sin eso a veces la captura se bloquea. |
| FPS mínimo | El criterio CA-01 exige ≥ 15 fps. Mídelo en el panel de la GUI, no en microbenchmarks. |

---

## 9. Verificación antes de dar por terminado un cambio

1. `.\venv\Scripts\python -m compileall -q main.py rcp` sin errores.
2. `.\venv\Scripts\python -m pruebas.test_criterios` → **todas PASS**.
3. Si tocaste la GUI: lanza `ejecutar_rcp.bat`, inicia y finaliza una sesión,
   y confirma que aparece el resumen.
4. Si cambió un requisito, un umbral o la arquitectura: **propón** la
   actualización de `docs/` y espera aprobación humana; no la edites por tu
   cuenta.
5. Ejecuta `git status` y confirma que no quedan cambios sin commitear.

---

## 10. Referencia rápida de requisitos

| ID | Requisito |
|----|-----------|
| RF-01 | Video en tiempo real ≥ 15 fps; sin cámara no inicia |
| RF-02 | Landmarks 11,12,13,14,15,16,23,24 superpuestos |
| RF-03 | Frecuencia en cpm, clasificada baja/correcta/alta |
| RF-04 | Profundidad en cm vía desplazamiento de muñecas + escala ArUco |
| RF-05 | Manos sobre el esternón; error con marca de tiempo |
| RF-06 | Retorno torácico completo vía elevación de hombros |
| RF-07 | Ángulo hombro-codo-muñeca; error con marca de tiempo |
| RF-08 | Feedback con color y mensaje, sin demoras > 2 s |
| RF-09 | GUI con video, landmarks, indicadores y finalización con resumen |
| RNF-01 | Proceso por fotograma < 100 ms |
| RNF-02 | Precisión en frecuencia: error máximo de 5 % (≈ 6 cpm a 120 cpm) |
| RNF-03 | Error de profundidad < ±0,5 cm |
| RNF-04 | Usabilidad: interfaz clara, uso sin capacitación |
| RNF-05 | Disponibilidad: inactividad < 5 % en sesiones programadas |
| RNF-06 | Cámara web 640×480 por USB; CPU sin GPU dedicada |
| RNF-07 | Módulos independientes y documentados |

Detalle completo: [`docs/01_requisitos.md`](docs/01_requisitos.md) (solo
lectura; ver §3).
