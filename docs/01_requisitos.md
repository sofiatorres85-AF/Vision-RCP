# SPECS — Sistema de análisis de técnica RCP

OpenCV + MediaPipe Pose + ArUco + Tkinter.

## 1. Requisitos funcionales y no funcionales

| ID | Requisito | Tipo | Prioridad MoSCoW | RN | Artefacto de diseño | Módulo o componente | Caso de prueba / Criterio de aceptación |
|----|-----------|------|------------------|----|---------------------|--------------------|------------------------------------------|
| RF-01 | Captura de video en tiempo real | Funcional | M | — | HU-01 | `rcp/captura.py`, OpenCV, Tkinter | CP-01 / CA-01: la cámara se activa en menos de 3 s y el video se muestra a mínimo 15 fps. Sin cámara conectada se muestra error y la sesión no inicia. |
| RF-02 | Detección de landmarks corporales | Funcional | M | — | HU-01, HU-02 | `rcp/procesamiento.py`, MediaPipe Pose | CP-02 / CA-02: detecta y superpone hombros (11,12), codos (13,14), muñecas (15,16) y caderas (23,24) durante toda la sesión. |
| RF-03 | Medición de frecuencia de compresiones | Funcional | M | RN-01 | HU-03 | `rcp/analisis.py`, MediaPipe Pose, `rcp/reglas.py` | CP-03 / CA-03: calcula las cpm a partir del intervalo entre compresiones, actualiza tras cada ciclo y clasifica baja (<100), correcta (100-120) o alta (>120). |
| RF-04 | Medición de profundidad de compresión | Funcional | M | RN-02 | HU-04 | `rcp/analisis.py`, OpenCV, ArUco | CP-04 / CA-04: estima la profundidad en cm a partir del desplazamiento vertical de las muñecas, con ArUco como escala, y clasifica insuficiente (<5), correcta (5-6) o excesiva (>6). |
| RF-05 | Detección de posición de manos | Funcional | S | RN-03 | HU-05 | `rcp/analisis.py`, ArUco, `rcp/reglas.py` | CP-05 / CA-05: verifica si las manos están sobre el centro del tórax respecto de la referencia torácica y registra el error con su marca de tiempo. |
| RF-06 | Detección de retorno torácico completo | Funcional | S | RN-04 | HU-05 | `rcp/analisis.py`, `rcp/reglas.py` | CP-06 / CA-06: evalúa el retorno midiendo la elevación de los hombros en la descompresión y registra el error con marca de tiempo. |
| RF-07 | Detección de rectitud de brazos | Funcional | S | RN-05 | HU-05 | `rcp/analisis.py`, `rcp/reglas.py` | CP-07 / CA-07: calcula el ángulo hombro-codo-muñeca y registra el error con marca de tiempo si los brazos no se mantienen extendidos. |
| RF-08 | Retroalimentación visual inmediata | Funcional | M | RN-06 | HU-06 | `rcp/retroalimentacion.py`, Tkinter | CP-08 / CA-08: muestra en tiempo real frecuencia y profundidad, color (verde correcto, rojo/amarillo desviación) y mensajes breves, sin interrupciones superiores a 2 s. |
| RF-09 | Interfaz de usuario gráfica | Funcional | M | — | HU-02, HU-07 | `rcp/interfaz.py`, `rcp/sesion.py` | CP-09 / CA-09: muestra video, landmarks e indicadores. Botón siempre visible para finalizar; al finalizar detiene captura y análisis y muestra resumen (duración, frecuencia promedio, profundidad promedio, errores). |
| RNF-01 | Rendimiento en tiempo real | No funcional | M | — | HU-01..04, HU-06 | `rcp/interfaz.py` (cronómetro) | CP-10 / CA-10: tiempo de procesamiento por fotograma y de generación de feedback menor a 100 ms. |
| RNF-02 | Precisión en frecuencia | No funcional | M | RN-01 | HU-03 | `rcp/analisis.py`, `rcp/reglas.py` | CP-11 / CA-11: contra una referencia conocida (metrónomo 100-120 cpm), error absoluto ≤ 6 cpm (±5 %). |
| RNF-03 | Precisión en profundidad | No funcional | M | RN-02 | HU-04 | `rcp/analisis.py`, `rcp/procesamiento.py` | CP-12 / CA-12: contra una profundidad medida con regla entre 5 y 6 cm, error absoluto < ±0,5 cm. |
| RNF-04 | Usabilidad | No funcional | S | — | HU-02, HU-06, HU-07 | `rcp/interfaz.py` | CP-13 / CA-13: prueba piloto; el administrador inicia, usa y finaliza la sesión sin capacitación. |
| RNF-05 | Disponibilidad | No funcional | M | — | HU-01, HU-07 | `rcp/captura.py`, `rcp/interfaz.py` | CP-14 / CA-14: disponibilidad con inactividad < 5 % durante las sesiones programadas. |
| RNF-06 | Compatibilidad de hardware | No funcional | S | — | HU-01 | `rcp/captura.py`, MediaPipe Pose | CP-15 / CA-15: cámara web estándar 640×480 por USB en Intel Core i5 o similar, sin GPU. |
| RNF-07 | Mantenibilidad | No funcional | C | — | HU-01..07 | Todos los módulos (ver §2) | CP-16 / CA-16: código documentado y organizado en módulos independientes: captura, procesamiento, análisis, reglas, retroalimentación, sesión e interfaz. |

## 2. Módulos (RNF-07 / CP-16)

| Módulo | Archivo | Responsabilidad |
|--------|---------|------------------|
| Configuración | `rcp/configuracion.py` | Índices de landmarks y umbrales de todos los RN |
| Captura de video | `rcp/captura.py` | Apertura de cámara, cronometraje (<3 s), error sin cámara |
| Modelos | `rcp/modelos.py` | Descarga y creación de PoseLandmarker / HandLandmarker |
| Procesamiento | `rcp/procesamiento.py` | ArUco (escala), extracción de landmarks, superposición gráfica |
| Análisis | `rcp/analisis.py` | Señal, contador de compresiones, cpm, profundidad, ángulos, retorno |
| Reglas | `rcp/reglas.py` | Motor RN-01 a RN-06 con estados ok / alerta / error / espera |
| Retroalimentación | `rcp/retroalimentacion.py` | Mensaje principal, color y lista de correcciones |
| Sesión | `rcp/sesion.py` | Ciclo de vida, promedios, errores con marca de tiempo, resumen |
| Interfaz | `rcp/interfaz.py` | GUI Tkinter, panel de indicadores, registro de eventos, CSV |

Punto de entrada: `main.py`. Pruebas: `pruebas/test_criterios.py`.

> **Nota sobre la estructura de carpetas.** El paquete vive en `rcp/` y no en
> `src/`; los nombres de los módulos se mantuvieron por que ya estaban
> referenciados en `main.py` y en las pruebas. La equivalencia con la
> estructura objetivo `src/` es directa: `rcp/captura.py` = `src/captura.py`,
> `rcp/procesamiento.py` = `src/deteccion_pose.py`, `rcp/analisis.py` =
> `src/analizador_rcp.py`, `rcp/reglas.py` = `src/motor_reglas.py`,
> `rcp/configuracion.py` = `src/config.py`, `rcp/interfaz.py` = `src/interfaz.py`.
> `rcp/retroalimentacion.py` y `rcp/sesion.py` son los módulos exigidos por
> CP-16 que la estructura `src/` no contempla.

## 3. Landmarks utilizados (RF-02)

| Índices | Punto | Uso |
|---------|-------|-----|
| 11, 12 | Hombros | Retorno torácico (RN-04), referencia de simetría |
| 13, 14 | Codos | Ángulo hombro-codo-muñeca (RN-05) |
| 15, 16 | Muñecas | Señal de compresión, profundidad (RN-01, RN-02), separación de manos (RN-03) |
| 23, 24 | Caderas | Referencia postural del tronco |

## 4. Fórmulas

- Escala: `px_por_cm = lado_px_aruco / tamaño_real_cm` (ArUco ID 0 impreso a 5,0 cm).
- Señal: `y_cm = (y_suavizada_muñecas − línea_base) / px_por_cm`.
- Profundidad: `amplitud = valle − punto_alto` de cada ciclo, promedio de las últimas 5.
- Frecuencia: `cpm = 60 / media(últimos 5 intervalos entre valles)`.
- Posición de manos: separación de muñecas ≤ 12 cm y desalineación del punto medio de
  muñecas respecto del ArUco ≤ 0,35 × ancho de hombros.
- Retorno torácico: `desvio_hombros_cm < 2 cm` respecto de la línea base de hombros.
- Ángulo de brazo: `acos((BA·BC)/(|BA||BC|))`; extendidos si ≥ 150°.

Referencias AHA: 100-120 cpm y 5-6 cm de profundidad.

## 5. Verificación

```
.\venv\Scripts\python -m pruebas.test_criterios
```

Resultados actuales (todas aprobadas):

| Prueba | Criterio | Resultado medido |
|--------|----------|-------------------|
| Índices de landmarks | CA-02 | 11,12,13,14,15,16,23,24 detectados |
| Clasificación de cpm (80/110/140) | CA-03 | Correcta en los tres casos |
| Clasificación de profundidad (3,5/5,5/8,0 cm) | CA-04 | Correcta en los tres casos |
| Frecuencia con metrónomo 100/110/120 cpm | CA-11 / RNF-02 | 100,0 / 110,4 / 120,0 cpm (error ≤ 0,4) |
| Profundidad 5,0 / 5,5 / 6,0 cm | CA-12 / RNF-03 | 4,93 / 5,42 / 5,92 cm (error ≤ 0,08) |
| Posición de manos juntas vs separadas | CA-05 | Detecta ambos casos |
| Retorno completo vs colapso postural | CA-06 | Detecta ambos casos |
| Ángulos 180° / 90° y brazos flexionados | CA-07 | Correcto; alerta por debajo de 150° |
| Feedback con color y dos correcciones | CA-08 | Verde correcto; naranja/rojo en desviación |
| Tiempo de proceso por fotograma | CA-10 / RNF-01 | 0,14 ms (límite 100 ms) |
| Registro de errores con marca de tiempo | CA-05/06/07 | 4 errores, formato HH:MM:SS.mmm, sin duplicados |

## 6. Notas de operación en Windows

Tkinter dentro del venv puede fallar con `_tkinter.TclError: Can't find a usable
init.tcl`. El fix es definir `TCL_LIBRARY` y `TK_LIBRARY`, lo cual ya quedó
incorporado en `venv/Scripts/activate.bat`, `venv/Scripts/Activate.ps1` y
`ejecutar_rcp.bat`.