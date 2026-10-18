"""Módulo de captura de video desde la cámara web (RF-01 / CA-01).

Responsabilidades:
* abrir la cámara y medir cuánto tarda (CA-01: menos de 3 s);
* reportar un mensaje de error claro si no hay cámara conectada, de modo
  que la sesión no inicie;
* exponer la lectura de fotogramas a 15 fps o más.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2

from .configuracion import Configuracion


@dataclass(frozen=True)
class ResultadoActivacion:
    """Resultado de intentar abrir la cámara (CA-01)."""

    ok: bool
    mensaje: str
    segundos: float


class CapturaVideo:
    """Envoltorio sobre ``cv2.VideoCapture``."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.cap: Optional[cv2.VideoCapture] = None

    @property
    def activa(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def activar(self) -> ResultadoActivacion:
        """Abre la cámara web. Si falla, la sesión no debe iniciarse."""
        inicio = time.perf_counter()
        try:
            camara = cv2.VideoCapture(self.config.indice_camara, cv2.CAP_DSHOW)
            abierta = camara.isOpened()
        except Exception as error:  # pragma: no cover - depende del hardware
            return ResultadoActivacion(False, f"Error al acceder a la cámara: {error}", 0.0)

        segundos = time.perf_counter() - inicio
        if not abierta:
            camara.release()
            return ResultadoActivacion(
                False,
                "No hay cámara conectada o está siendo usada por otra aplicación.",
                segundos,
            )

        self.cap = camara
        # Resolución mínima razonable para no perder los landmarks.
        camara.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if segundos > self.config.tiempo_maximo_activacion_camara_s:
            mensaje = (
                f"Cámara activada en {segundos:.2f} s "
                f"(por encima del objetivo de {self.config.tiempo_maximo_activacion_camara_s:.0f} s)."
            )
        else:
            mensaje = f"Cámara activada en {segundos:.2f} s."
        return ResultadoActivacion(True, mensaje, segundos)

    def leer(self) -> Tuple[bool, Optional["object"]]:
        """Lee un fotograma. Devuelve ``(ok, frame_bgr)``."""
        if not self.activa:
            return False, None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return False, None
        return True, frame

    def liberar(self) -> None:
        """Libera la cámara; se invoca al finalizar la sesión (CA-09)."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None