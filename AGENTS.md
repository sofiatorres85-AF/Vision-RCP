# AGENTS.md — Reglas y contexto para agentes de IA

Guía para que cualquier agente trabajen en este repositorio sin romper nada.
Documento viviente: si cambias algo estructural, actualízalo en el mismo commit.

---

## 1. Contexto del proyecto

**Nombre:** Sistema de análisis de técnica de RCP.
**Objetivo de grado:** evaluar con una cámara web la técnica de reanimación
cardiopulmonar en adultos (frecuencia, profundidad, posición de manos, retorno
torácico y rectitud de brazos) y dar retroalimentación inmediata al alumno.

*Idioma del proyecto: español.* Los nombres de archivos, funciones, comentarios,
mensajes de la interfaz y la documentación están en español. No traduzcas nada
al inglés salvo que se pida explícitamente.

---

## 2. Estructura

```
main.py              punto de entrada (lleva Tkinter al mainloop)
ejecutar_rcp.bat     lanzador Windows (define Tcl/Tk, ejecuta main.py)
requirements.txt     dependencias
rcp/                 paquete de código fuente (10 módulos)
pruebas/             verificación de criterios de aceptación
docs/                documentación
aruco_ID0.png        marcador ArUco a imprimir
```

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

## 3. Comandos

```bat
:: entorno
venv\Scripts\activate.bat
pip install -r requirements.txt

:: aplicación (o usar ejecutar_rcp.bat)
.\venv\Scripts\python main.py

:: pruebas de criterios de aceptación
.\venv\Scripts\python -m pruebas.test_criterios

:: verificación rápida de sintaxis
.\venv\Scripts\python -m py_compile main.py <archivo.py>
```

**Siempre** usa el Python del venv (`.\venv\Scripts\python` o el venv activado).
El `python` global no tiene `cv2` instalado y fallará.

---

## 4. Reglas

### 4.1 No romper

* No elimines ni renombres módulos de `rcp/` sin actualizar `main.py`,
  `pruebas/` y toda la documentación de `docs/`.
* No cambies umbrales AHA sueltos dentro del código: van en
  `rcp/configuracion.py`. Si necesitas un umbral nuevo, agrega un campo ahí con
  el número de requisito en el comentario.
* No fusiones `analisis`, `reglas`, `retroalimentacion` o `sesion` en un solo
  archivo: incumple CP-16.
* No reemplaces la API de MediaPipe Tasks por `mp.solutions` (eliminada en 1.x)
  ni instales `mediapipe<1.0` sin avisar.

### 4.2 Commits

* `pruebas/` **no** se sube hasta que el usuario lo autorice expresamente.
* `app_rcp_aruco_pose.py` es la versión monolítica anterior: se conserva como
  referencia, no se modifica, no se usa como punto de entrada.
* `venv/`, `models/*.task`, `__pycache__/` y `*.csv` están en `.gitignore`;
  no los agregues al control de versiones.
* Escribe los mensajes de commit en español y menciona el requisito que cubren
  (`RF-04`, `CA-09`, `CP-11`, etc.).

### 4.3 Trazabilidad

Cada cambio funcional debe rastrearse en `docs/01_requisitos.md`:

* ¿Agregaste un requisito? → agrega su fila RF/RNF y su criterio de aceptación.
* ¿Cambiaste un umbral? → actualiza `docs/04_parametros_aha.md`.
* ¿Agregaste una regla nueva? → aggiorna RN en ambos documentos.

---

## 5. Convenciones de código

* **Español** en identificadores (`AnalizadorRCP`, `regla_profundidad`) y en los
  docstrings. Comenta el *por qué*, no el *qué*.
* **Docstrings** en todos los módulos, clases y funciones públicas, citando el
  requisito que implementan (ej. `"RN-02 / RF-04 / CA-04"`).
* **`dataclass`** para datos (Configuracion, Metricas, ResultadoRegla,
  ErrorDetectado, ResumenSesion). Usa `frozen=True` cuando sea inmutable.
* **Tipo completo** en las firmas (`Optional[float]`, `List[...]`).
* **Sin excepciones genéricas silenciosas**; si capturas una, deja mensaje.
* **Nombre de variables** en minúscula con guion bajo; constantes en mayúsculas.
* Mantén los nombres de la interfaz existentes (`etiqueta_*`, `boton_*`) para no
  romper referencias.

---

## 6. Pitfalls conocidos (no los vuelvas a redescubrir)

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

## 7. Verificación antes de dar por terminado un cambio

1. `.\venv\Scripts\python -m py_compile main.py rcp\*.py` sin errores.
2. `.\venv\Scripts\python -m pruebas.test_criterios` → **todas PASS**.
3. Si tocaste la GUI: lanza `ejecutar_rcp.bat`, inicia y finaliza una sesión,
   y confirma que aparece el resumen.
4. Actualiza `docs/` si cambió requisito, umbral o arquitectura.
5. Ejecuta `git status` y confirma que `pruebas/` sigue sin trackear salvo
   autorización expresa.

---

## 8. Requisitos de referencia rápida

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
| RNF-02 | Error de frecuencia ≤ 6 cpm |
| RNF-03 | Error de profundidad < ±0,5 cm |
| RNF-07 | Módulos independientes y documentados |

Detalle completo: [`docs/01_requisitos.md`](docs/01_requisitos.md).

---
---

# AGENTS.md - Reglas para el Agente de IA

> **Nota de aplicación en este repositorio.** Antes de aplicar las reglas
> siguientes, ten en cuenta tres aclaraciones:
>
> 1. **`src/` = `rcp/`.** En este proyecto el paquete de código fuente se llama
>    `rcp/` (no existe carpeta `src/`). Los nombres `captura.py`,
>    `deteccion_pose.py`, `analizador_rcp.py`, `motor_reglas.py` e `interfaz.py`
>    de la sección 3 corresponden, en orden, a `rcp/captura.py`,
>    `rcp/procesamiento.py`, `rcp/analisis.py`, `rcp/reglas.py` e
>    `rcp/interfaz.py`. El alcance de permisos de la sección 4 se lee como
>    "archivos fuera de `rcp/`". `rcp/` contiene además `configuracion.py`,
>    `modelos.py`, `retroalimentacion.py` y `sesion.py`, que la sección 3 no
>    enumera pero que CP-16 sí exige.
> 2. **`docs/` sí se modifica, solo con aprobación.** La sección 2 prohíbe
>    tocar `docs/`; en este repositorio la regla operativa es: proponer el
>    cambio y esperar aprobación humana, tal como indica la propia sección 2
>    ("propónlo y espera aprobación humana"). Mientras tanto, actualiza los
>    requisitos en `docs/01_requisitos.md` y los umbrales en
>    `docs/04_parametros_aha.md` solo con esa aprobación.
> 3. **Las pruebas son un script plano.** `pruebas/test_criterios.py` no usa
>    `pytest` ni `unittest`: es un script con `comprobar(nombre, condicion)` y
>    un resumen `PASS`/`FALLA` al final. Amplía ese formato para los nuevos CA;
>    no lo migres a otro framework sin aprobación.

## 1. Contexto del Proyecto (Context Spec)

Eres un asistente de codificación para un prototipo de visión artificial que evalúa la técnica de RCP.

- **Stack:** Python 3, OpenCV, MediaPipe Pose, Tkinter (sin frameworks web, sin base de datos).
- **Arquitectura:** Monolito de escritorio, un solo proceso local, sin comunicación por red.
- **Parámetros de negocio (AHA 2025):** Frecuencia 100-120 cpm, Profundidad 5-6 cm. Estos valores son fijos y residen en un archivo de configuración (no en la interfaz).
- **Referencia funcional:** Antes de codificar, lee `docs/01_requisitos.md` y `docs/02_historias_usuario.md`.

## 2. Límites y Restricciones (Boundary Spec)

- **NO** implementes base de datos ni persistencia. El registro es manual en CSV/Excel (ver Limitaciones del proyecto).
- **NO** añadas dependencias que requieran GPU. El sistema debe correr en CPU (Intel Core i5 o similar).
- **NO** modifiques los archivos en `docs/`. Si necesitas un cambio de requisito, propónlo y espera aprobación humana.
- **NO** modifiques los tests existentes para que pasen. Si un test falla, corrige el código de producción.
- **NO** hardcodees los valores de la AHA. Léelos desde el archivo de configuración.

## 3. Estándares de Calidad (Quality Spec - ISO/IEC 25010)

- **Eficiencia (RNF-01):** Cada fotograma debe procesarse en menos de 100 ms. Si tu código introduce un cuello de botella, debes justificarlo.
- **Exactitud (RNF-02, RNF-03):** La frecuencia no debe desviarse más del ±5% (±6 cpm) y la profundidad más de ±0.5 cm.
- **Mantenibilidad (RNF-07):** Organiza el código en módulos separados: `captura.py`, `deteccion_pose.py`, `analizador_rcp.py`, `motor_reglas.py`, `interfaz.py`. No mezcles responsabilidades en un solo archivo.
- **Usabilidad (RNF-04):** La interfaz debe ser clara, con códigos de color (verde/rojo/amarillo) y mensajes breves (ej. "Presiona más hondo").

## 4. Reglas de Seguridad (OWASP)

- **Sandboxing:** Ejecuta comandos de shell solo dentro del entorno virtual de Python (venv). No instales paquetes globalmente.
- **Permisos:** Pide confirmación antes de ejecutar comandos que modifiquen archivos fuera de `src/`.
- **Secretos:** Nunca escribas claves API o rutas absolutas de tu máquina en el código. Usa variables de entorno o rutas relativas.
- **Inyección:** Trata los datos de entrada de la cámara (frames) como no confiables. Valida los tipos y rangos antes de procesarlos.

## 5. Flujo de Trabajo (Basado en IEEE 3398 y SDD)

- **Planificación:** Antes de escribir código para una nueva HU, presenta un plan con: (1) archivos a modificar, (2) estrategia de pruebas, (3) verificación de que cumples los RNF.
- **Pruebas:** Para cada funcionalidad, escribe un test unitario (usando `pytest` o `unittest`) que verifique los criterios de aceptación (CA-01 a CA-16).
- **Commits:** Usa mensajes claros que referencien el requisito (ej. `feat: implementar RF-03 medicion de frecuencia`).
- **Documentación:** Documenta cada módulo con docstrings en formato Google o NumPy.