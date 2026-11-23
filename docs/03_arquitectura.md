# Arquitectura del sistema

## 1. Vista general

El sistema es una aplicación de escritorio en Python que toma una imagen de la
cámara web, extrae la postura del usuario, calcula métricas de la técnica de RCP
y las presenta en una interfaz Tkinter con reglas AHA aplicadas en tiempo real.

```
                  ┌──────────────────────────────────────────────┐
                  │                    main.py                   │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │          rcp/interfaz.py  (GUI)              │
                  │  video · indicadores · registro · resumen    │
                  └──┬──────────┬──────────┬──────────┬──────────┘
                     │          │          │          │
        ┌────────────▼───┐ ┌────▼────────┐ ┌▼──────────┐ ┌───────────────┐
        │ rcp/captura.py │ │rcp/procesa- │ │rcp/analisi│ │ rcp/reglas.py │
        │ cámara web USB │ │miento.py    │ │z.py       │ │ RN-01..RN-06  │
        └────────────────┘ │ArUco+Pose   │ │cpm·cm·ang │ └──────┬────────┘
                           └──────┬──────┘ └────┬──────┘        │
                                  │             │     ┌─────────▼────────┐
                           ┌──────▼──────┐ ┌────▼─────┐│rcp/retroalimen- │
                           │rcp/modelos.py│ │señal y   ││tacion.py        │
                           │MediaPipe     │ │escalas   │└─────────────────┘
                           └─────────────┘ └──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   rcp/sesion.py     │
                              │ errores con hora y  │
                              │ resumen de desempeño│
                              └─────────────────────┘
```

## 2. Módulos y responsabilidad única

Estructura CP-16 / RNF-07: cada módulo es independiente y se puede probar aislado.

| Módulo | Archivo | Responsabilidad | Sin dependencia de |
|--------|---------|-----------------|--------------------|
| Configuración | `rcp/configuracion.py` | Índices de landmarks y umbrales de todos los RN | cualquier librería externa |
| Captura | `rcp/captura.py` | Abrir cámara, cronometrar, reportar ausencia | Pose y Tkinter |
| Modelos | `rcp/modelos.py` | Descargar y crear los modelos MediaPipe | OpenCV y Tkinter |
| Procesamiento | `rcp/procesamiento.py` | Detección ArUco, extracción de landmarks, superposición | Tkinter |
| Análisis | `rcp/analisis.py` | Señal, contador, cpm, profundidad, ángulos, retorno | OpenCV y Tkinter |
| Reglas | `rcp/reglas.py` | Evaluar RN-01 a RN-06 sobre las métricas | OpenCV y Tkinter |
| Retroalimentación | `rcp/retroalimentacion.py` | Elegir mensaje principal y color | OpenCV y Tkinter |
| Sesión | `rcp/sesion.py` | Ciclo de vida, promedios, errores, resumen | OpenCV y Tkinter |
| Interfaz | `rcp/interfaz.py` | GUI Tkinter y orquestación del fotograma | — |

`analisis.py`, `reglas.py`, `retroalimentacion.py` y `sesion.py` **no importan
OpenCV ni Tkinter**, por lo que las pruebas de precisión se ejecutan sin cámara
ni pantalla gráfica.

## 3. Flujo de un fotograma

`AplicacionRCP._actualizar()` en `rcp/interfaz.py`:

1. **Captura** — `CapturaVideo.leer()` devuelve `(ok, frame_bgr)`.
2. **Espejo** — `cv2.flip(frame, 1)` para que la vista sea natural.
3. **Procesamiento · ArUco** — `ProcesadorArUco.detectar()` obtiene centro y lado
   en píxeles; de ahí sale `px_por_cm`.
4. **Procesamiento · Pose** — `ProcesadorPose.procesar()` devuelve
   `{índice: (x_px, y_px)}` para 11, 12, 13, 14, 15, 16, 23, 24.
5. **Análisis** — `AnalizadorRCP.actualizar()` produce `Metricas`.
6. **Reglas** — `MotorReglas.evaluar()` devuelve seis resultados ordenados por
   gravedad.
7. **Retroalimentación** — `GeneradorFeedback.generar()` produce mensaje y color.
8. **Registro de errores** — `Sesion.registrar_reglas()` añade con marca de tiempo.
9. **Superposición** — dibujo de landmarks, panel de indicadores y señal.
10. **Rendimiento** — se cronometra el paso 1 a 9 y se compara con 100 ms.
11. **Persistencia** — fila CSV opcional.
12. **Refresco** — `root.after(1, ...)` programa el siguiente fotograma.

## 4. Tecnologías

| Componente | Librería | Versión en el venv | Uso |
|------------|----------|--------------------|-----|
| Visión | `opencv-contrib-python` | 5.0.0 | Captura, ArUco, dibujo |
| Pose | `mediapipe` | 1.0.1 | Tasks API: `PoseLandmarker` |
| Números | `numpy` | 2.5.3 | Cálculo vectorial |
| Imagen | `pillow` | 12.3.0 | BGR → `PhotoImage` para Tkinter |
| GUI | `tkinter` | stdlib | Ventana, paneles, diálogo de resumen |

> MediaPipe 1.x **eliminó** `mp.solutions`; el código usa `mediapipe.tasks.python`
> con `RunningMode.VIDEO` y marcas de tiempo monotónicas.

## 5. Decisiones de diseño

* **Umbrales centralizados** en `Configuracion` (dataclass congelada): cambiar un
  valor AHA no toca la lógica de ninguna regla.
* **Motor de reglas separado del análisis**: las métricas son hechos y las reglas
  son juicios; permite reevaluar sin recalcular.
* **Estados `ok` / `alerta` / `error` / `espera`**: el «espera» distingue la
  falta de datos de un error real, evitando falsos positivos al inicio de la sesión.
* **Enfriamiento de errores** (`enfriamiento_error_s = 1.0`): cada infracción se
  registra una sola vez hasta que la condición desaparece.
* **Escala por ArUco**: el lado impreso conocido convierte píxeles en
  centímetros; sin el marcador se degrada a escala aproximada en lugar de bloquear.
* **Arquitectura sin cámara ni GUI en los módulos núcleo**: permite verificar
  RNF-02, RNF-03 y RNF-01 en CI sin hardware.

## 6. Estructura de carpetas

```
Proyecto_Grado/
├── AGENTS.md
├── README.md
├── requirements.md
├── ejecutar_rcp.bat
├── main.py                      # punto de entrada
├── docs/
│   ├── 01_requisitos.md         # RF, RNF, RN y matriz de trazabilidad
│   ├── 02_historias_usuario.md  # HU-01 a HU-07
│   ├── 03_arquitectura.md       # este archivo
│   └── 04_parametros_aha.md     # umbrales de las reglas
├── rcp/                         # código fuente (equivalente a src/)
│   ├── __init__.py
│   ├── configuracion.py
│   ├── captura.py
│   ├── modelos.py
│   ├── procesamiento.py
│   ├── analisis.py
│   ├── reglas.py
│   ├── retroalimentacion.py
│   ├── sesion.py
│   └── interfaz.py
├── pruebas/
│   ├── __init__.py
│   └── test_criterios.py
├── aruco_ID0.png                # marcador a imprimir
├── app_rcp_aruco_pose.py        # versión anterior (solo referencia)
└── venv/                        # entorno virtual (ignorado por git)
```

## 7. Consideraciones de entorno

* **Tkinter en venv con Python 3.13 en Windows** falla con
  `TclError: Can't find a usable init.tcl`. La solución es exportar
  `TCL_LIBRARY` y `TK_LIBRARY`; ya está incrustada en `venv/Scripts/activate.bat`,
  `venv/Scripts/Activate.ps1` y `ejecutar_rcp.bat`.
* **Modelos MediaPipe** se descargan a `models/` en el primer arranque (ignorados
  por git por su tamaño).
* **Cámara en Windows**: `cv2.CAP_DSHOW` evita cuelgues típicos de DirectShow.