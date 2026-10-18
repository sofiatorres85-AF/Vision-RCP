"""Carga de los modelos de MediaPipe Tasks.

MediaPipe 1.x eliminó ``mp.solutions``; este módulo encapsula la creación de
``PoseLandmarker`` / ``HandLandmarker`` y la descarga automática de los
archivos ``.task`` a la carpeta ``models/`` la primera vez.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Optional

from .configuracion import Configuracion

URL_POSE = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
URL_MANO = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

RUTA_MODELO_POSE = Path("models/pose_landmarker_lite.task")
RUTA_MODELO_MANO = Path("models/hand_landmarker.task")


def asegurar_modelo(url: str, ruta: Path) -> str:
    """Descarga el modelo si aún no existe y devuelve su ruta."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        print(f"Descargando modelo {ruta.name} ...")
        urllib.request.urlretrieve(url, str(ruta))
    return str(ruta)


def crear_pose_landmarker(config: Optional[Configuracion] = None):
    """Crea el detector de pose. Devuelve ``None`` si no está disponible."""
    cfg = config or Configuracion()
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import vision as mpv
        from mediapipe.tasks.python.core.base_options import BaseOptions

        ruta = asegurar_modelo(URL_POSE, RUTA_MODELO_POSE)
        opciones = mpv.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=ruta),
            running_mode=mpv.RunningMode.VIDEO,
            num_poses=cfg.maximo_poses,
            min_pose_detection_confidence=cfg.min_confianza_deteccion,
            min_tracking_confidence=cfg.min_confianza_seguimiento,
        )
        return mpv.PoseLandmarker.create_from_options(opciones)
    except Exception as error:  # pragma: no cover - depende del entorno
        print(f"Aviso: no se pudo crear PoseLandmarker: {error}")
        return None


def crear_hand_landmarker(config: Optional[Configuracion] = None):
    """Crea el detector de manos (opcional). Devuelve ``None`` si falla."""
    cfg = config or Configuracion()
    try:
        from mediapipe.tasks.python import vision as mpv
        from mediapipe.tasks.python.core.base_options import BaseOptions

        ruta = asegurar_modelo(URL_MANO, RUTA_MODELO_MANO)
        opciones = mpv.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=ruta),
            running_mode=mpv.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=cfg.min_confianza_deteccion,
            min_tracking_confidence=cfg.min_confianza_seguimiento,
        )
        return mpv.HandLandmarker.create_from_options(opciones)
    except Exception as error:  # pragma: no cover - depende del entorno
        print(f"Aviso: no se pudo crear HandLandmarker: {error}")
        return None