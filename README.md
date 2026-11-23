# Sistema de análisis de técnica de RCP

Aplicación de escritorio que evalúa en tiempo real la técnica de la reanimación
cardiopulmonar usando una cámara web: detecta los puntos clave del cuerpo con
MediaPipe, mide la frecuencia y la profundidad de las compresiones, calcula la
posición de las manos, el retorno torácico y la rectitud de los brazos, y emite
retroalimentación inmediata en color.

**Stack:** OpenCV (`opencv-contrib-python`) · MediaPipe Tasks · ArUco · NumPy ·
Pillow · Tkinter.

---

## 1. Requisitos

* Python 3.13 (probado con el instalador de `C:\...\Python\Python313`)
* Cámara web USB de 640×480 o superior
* Sin GPU: funciona en un Intel Core i5 equivalente (RNF-06)

## 2. Instalación

```bat
venv\Scripts\activate.bat
pip install "opencv-contrib-python>=4.9" "mediapipe>=1.0" "numpy>=1.26" "pillow>=10.0"
```

La primera ejecución descarga los modelos de MediaPipe a `models/`
(`pose_landmarker_lite.task`), requiere conexión a internet una sola vez.

## 3. Ejecutar

Doble clic en **`ejecutar_rcp.bat`**, o en una terminal:

```bat
set TCL_LIBRARY=%~dp0venv\tcl\tcl8.6
set TK_LIBRARY=%~dp0venv\tcl\tk8.6
.\venv\Scripts\python main.py
```

> El `set` de `TCL_LIBRARY` / `TK_LIBRARY` es necesario porque Tkinter dentro de
> un venv de Python 3.13 no encuentra `init.tcl`. `ejecutar_rcp.bat` y los
> scripts de activación del venv ya lo incluyen, así que activar el venv antes de
> ejecutar también funciona.

## 4. Uso

1. Pulsa **«Generar marcador ArUco»** y guarda el PNG (ID 0).
2. Imprímelo a **5,0 cm** de lado exactos, sin «ajustar a página», en papel
   blanco mate, y pégalo plano en el pecho.
3. Colócate frente a la cámara con **hombros, caderas y manos visibles**.
4. Pulsa **«1. Iniciar sesión»**; la cámara se activa en menos de 3 segundos.
5. Comprime a **100-120 cpm** y **5-6 cm** de profundidad.
6. Pulsa **«2. Finalizar sesión»** cuando termines: se detienen la captura y el
   análisis y aparece el resumen (duración, compresiones, frecuencia y
   profundidad promedio, errores detectados con su marca de tiempo).

**Indicadores en pantalla:** frecuencia, profundidad, número de compresiones,
ángulo de brazos, separación de muñecas, FPS, tiempo de proceso y un mensaje de
corrección con color — verde correcto, naranja desviación leve, rojo desviación.

**Registro de eventos** (columna de la derecha): cada error queda con hora
`HH:MM:SS.mmm`, lo que permite revisar después qué falló y cuándo.

## 5. Pruebas de criterios de aceptación

```bat
.\venv\Scripts\python -m pruebas.test_criterios
```

No necesita cámara ni pantalla gráfica. Verifica los criterios CP-02 a CP-12,
entre ellos la precisión exigida por RNF-02 (≤ 6 cpm) y RNF-03 (≤ 0,5 cm).

## 6. Documentación

| Archivo | Contenido |
|---------|-----------|
| [`docs/01_requisitos.md`](docs/01_requisitos.md) | RF-01..RF-09, RNF-01..RNF-07, RN-01..RN-06 y criterios de aceptación |
| [`docs/02_historias_usuario.md`](docs/02_historias_usuario.md) | HU-01 a HU-07 y su trazabilidad con los requisitos |
| [`docs/03_arquitectura.md`](docs/03_arquitectura.md) | Módulos, flujo de un fotograma y decisiones de diseño |
| [`docs/04_parametros_aha.md`](docs/04_parametros_aha.md) | Umbrales AHA y su localización en el código |
| [`AGENTS.md`](AGENTS.md) | Contexto y reglas para agentes de IA |

## 7. Estructura

```
main.py              punto de entrada
ejecutar_rcp.bat     inicio rápido (define Tcl/Tk y lanza main.py)
requirements.md      dependencias (instalación manual)
rcp/                 código fuente (config, captura, modelos, procesamiento,
                     analisis, reglas, retroalimentacion, sesion, interfaz)
pruebas/             verificación de criterios de aceptación
docs/                documentación del proyecto
```

## 8. Solución de problemas

| Problema | Solución |
|----------|----------|
| `_tkinter.TclError: Can't find a usable init.tcl` | Usa `ejecutar_rcp.bat`, o exporta `TCL_LIBRARY` y `TK_LIBRARY` antes de ejecutar |
| `ModuleNotFoundError: 'cv2'` | Activaste el Python global; ejecuta `venv\Scripts\activate.bat` primero |
| `AttributeError: module 'mediapipe' has no attribute 'solutions'` | MediaPipe 1.x solo expone Tasks API; el código ya usa `rcp/modelos.py` |
| «No hay cámara conectada» | Cierra Zoom/Teams o prueba cambiando `Configuracion.indice_camara` |
| «Muestre el marcador ArUco para medir la posición» | Pega el marcador ID 0 en el pecho a 5,0 cm |
| Frecuencia errática | Pon la cámara a la altura del tórax y asegúrate de que las muñecas se vean completas |

## 9. Parámetros AHA

| Regla | Parámetro | Valor |
|-------|-----------|-------|
| RN-01 | Frecuencia | 100 – 120 cpm |
| RN-02 | Profundidad | 5 – 6 cm |
| RN-03 | Manos sobre el esternón | ≤ 12 cm de separación de muñecas |
| RN-04 | Retorno torácico | < 2 cm de desplazamiento residual de hombros |
| RN-05 | Rectitud de brazos | ≥ 150° hombro-codo-muñeca |
| RN-06 | Retroalimentación | < 100 ms de proceso por fotograma |

Detalle en [`docs/04_parametros_aha.md`](docs/04_parametros_aha.md).