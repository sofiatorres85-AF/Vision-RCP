# Dependencias del proyecto

Versiones mínimas y versiones con las que se probó el sistema (Python 3.13,
Windows, CPU sin GPU dedicada).

| Paquete | Versión mínima | Versión probada | Uso |
|---------|----------------|-----------------|-----|
| `opencv-contrib-python` | 4.9 | 5.0.0 | Captura, ArUco y dibujo |
| `mediapipe` | 1.0 | 1.0.1 | Pose (Tasks API) |
| `numpy` | 1.26 | 2.5.3 | Cálculo vectorial |
| `pillow` | 10.0 | 12.3.0 | Conversión BGR → `PhotoImage` para Tkinter |

## Instalación

```bat
venv\Scripts\activate.bat
pip install "opencv-contrib-python>=4.9" "mediapipe>=1.0" "numpy>=1.26" "pillow>=10.0"
```

O sin activar el entorno:

```bat
.\venv\Scripts\python -m pip install "opencv-contrib-python>=4.9" "mediapipe>=1.0" "numpy>=1.26" "pillow>=10.0"
```

> Las comillas son necesarias para que `cmd` no interprete `>` como redirección.
> La primera ejecución de la aplicación descarga el modelo de MediaPipe en
> `models/` y requiere conexión a internet una sola vez.
