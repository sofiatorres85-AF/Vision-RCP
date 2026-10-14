# SPECS — Sistema de análisis de técnica RCP con OpenCV + MediaPipe + ArUco

## 1. Objetivo
Evaluar en tiempo real la técnica de RCP desde cámara web convencional,
con superposición de landmarks e indicadores de calidad.

## 2. Requisitos funcionales (pliego)

| ID | Requisito | Implementación | Archivo |
|----|-----------|----------------|---------|
| RF-01 | Capturar video webcam en tiempo real ≥15 fps y mostrarlo en GUI | `cv2.VideoCapture(0, CAP_DSHOW)` + loop `after(15)` (~60 fps) / versión CV2 `waitKey(1)` | `app_rcp_aruco_pose.py:start`, `_update` / `app_rcp_cv2.py` |
| RF-02 | Detectar landmarks MediaPipe Pose: hombros 11-12, codos 13-14, muñecas 15-16, caderas 23-24 | Tasks API `PoseLandmarker` VIDEO, `res.pose_landmarks[0]` | `app_rcp_aruco_pose.py:_update` (sección 2), `POSE_LINES` |
| RF-03 | Calcular frecuencia (cpm) por movimiento cíclico hombros/muñecas | `CompressionCounter`: detector de valles alto→fondo→alto, `frec = 60/media(intervalos)` | `app_rcp_aruco_pose.py:CompressionCounter` |
| RF-04 | Estimar profundidad (cm) por desplazamiento vertical muñecas | `y_cm=(y_smooth-baseline)/px_por_cm`, escala por ArUco `px_por_cm=lado_px/tamaño_cm` | `_update` sección 4 |
| RF-05 | Verificar manos sobre centro del tórax (esternón) | a) dist. entre muñecas 15-16 <12 cm (manos juntas), b) punto medio muñecas vs punto medio hombros en X y vs ArUco | `_update` + `feedback()` |
| RF-06 | Verificar retorno completo del tórax (descompresión) | Elevación hombros: `shoulder_mid_y` debe volver a línea base ±1.0 cm tras cada valle | `recoil_ok()` / `_update` |
| RF-07 | Ángulo hombro-codo-muñeca (brazos extendidos) | `angle()` ABC, promedio ambos brazos, umbral ≥150° | `angle()` + `feedback()` |
| RF-08 | Mostrar en vivo frecuencia, profundidad e indicadores de error | Labels Tk + texto OpenCV: "Presione más hondo", "Aumente la frecuencia", etc. | `_build_ui`, `feedback()` |
| RF-09 | Ventana con video + landmarks + indicadores de calidad | Dibujo manual cv2 + panel métricas + mini-gráfica señal | `_draw_landmarks`, `_draw_signal` |

## 3. Landmarks (MediaPipe Pose, 33 puntos)

| Índice | Punto | Uso RCP |
|--------|-------|---------|
| 11, 12 | Hombros izq/der | Frecuencia auxiliar, recoil (elevación), referencia esternón |
| 13, 14 | Codos izq/der | Ángulo brazo 11-13-15 / 12-14-16 |
| 15, 16 | Muñecas izq/der | Señal principal compresión, profundidad, posición manos |
| 23, 24 | Caderas izq/der | Postura tronco (inclinación), evita falsos por movimiento cuerpo |

Dibujo: `POSE_LINES = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24)]`

## 4. Fórmulas

- Escala: `px_por_cm = lado_px_aruco / tamaño_real_cm`
- Profundidad: `prof = valle_y_cm - alto_previo_cm` (promedio últimas 5)
- Frecuencia: `frec = 60 / media(últimos 5 intervalos entre valles)`
- Dist. manos: `d_manos = |15-16| / px_por_cm` → OK si <12 cm
- Posición esternón: `|midX(muñecas)-midX(hombros)| < 0.15*ancho_hombros` y `dist(mid_muñecas, aruco) < 15 cm` si hay ArUco
- Recoil: `shoulder_y` vuelve a `baseline_hombros ±1.0 cm` antes del siguiente valle
- Ángulo: `acos((BA·BC)/(|BA||BC|))`, OK si ≥150°

Rangos AHA: frecuencia 100–120 cpm, profundidad 5–6 cm.

## 5. Criterios de aceptación

1. Video ≥15 fps medido con `t` y contador fps en pantalla.
2. Con torso visible: los 8 landmarks (11,12,13,14,15,16,23,24) se dibujan.
3. Simulación senoidal 1.83 Hz, 5.5 cm pico-pico → conteo 18/10 s, frec 110±5, prof 5.5±0.5 (test `CompressionCounter`).
4. Sin ArUco: sistema avisa "Sin escala", usa escala aprox 10 px/cm, no se bloquea.
5. CSV con columnas: timestamp, t_s, wrist_x/y, caderas, aruco, distancias, px_por_cm, compresiones, frec, prof, recoil, ang_brazo.

## 6. Arquitectura

```
Cámara → OpenCV → ArUco (escala) → MediaPipe Tasks Pose/Hands (VIDEO) →
señal muñecas → CompressionCounter → métricas → overlay cv2 + GUI Tk + CSV
```

- `app_rcp_aruco_pose.py`: versión Tkinter (requiere TCL_LIBRARY/TK_LIBRARY en venv Windows).
- `app_rcp_cv2.py`: versión solo-OpenCV (`imshow`), sin Tkinter, evita error `init.tcl`.
- `models/`: `pose_landmarker_lite.task`, `hand_landmarker.task` (descarga auto).
- `aruco_ID0.png`: marcador DICT_4X4_50 ID 0 para imprimir a 5.0 cm.

## 7. Error conocido Windows + venv + Tkinter

`_tkinter.TclError: Can't find a usable init.tcl` → el venv no propaga Tcl.
Fix aplicado en `venv/Scripts/activate.bat` y `Activate.ps1`:
`TCL_LIBRARY=...Python313\tcl\tcl8.6`, `TK_LIBRARY=...tcl\tk8.6`.
Alternativa: usar `app_rcp_cv2.py` o `ejecutar_rcp.bat`.
