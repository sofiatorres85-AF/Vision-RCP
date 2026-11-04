"""Generador de retroalimentación visual (RF-08 / CA-08).

Convierte los resultados del :class:`~rcp.reglas.MotorReglas` en un mensaje
breve y un color de estado para la interfaz y para la superposición en el
video. Los colores son los exigidos por CA-08: verde para correcto, rojo o
amarillo para desviaciones.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .reglas import (
    ESTADO_ALERTA,
    ESTADO_ERROR,
    ESTADO_ESPERA,
    ESTADO_OK,
    ResultadoRegla,
)

# Colores semánticos usados por Tkinter.
COLOR_OK = "green"
COLOR_ALERTA = "orange"      # amarillo/naranja: desviación leve
COLOR_ERROR = "red"
COLOR_ESPERA = "gray"

#: Colores BGR equivalentes para la superposición con OpenCV.
COLOR_OK_BGR = (0, 170, 0)
COLOR_ALERTA_BGR = (0, 180, 255)
COLOR_ERROR_BGR = (0, 0, 255)
COLOR_ESPERA_BGR = (200, 200, 200)

# Fondos claros para los paneles de estado: legibles con texto negro.
FONDO_OK = "#dff5df"
FONDO_ALERTA = "#ffe9c2"
FONDO_ERROR = "#fbd9d9"
FONDO_ESPERA = "#e9e9e9"

#: Fondos por estado de regla, para el panel "¿Qué está mal?".
FONDOS_POR_ESTADO = {
    ESTADO_OK: FONDO_OK,
    ESTADO_ALERTA: FONDO_ALERTA,
    ESTADO_ERROR: FONDO_ERROR,
    ESTADO_ESPERA: FONDO_ESPERA,
}


class GeneradorFeedback:
    """Selecciona el mensaje más relevante y su color."""

    @staticmethod
    def color_por_estado(estado: str) -> str:
        if estado == ESTADO_OK:
            return COLOR_OK
        if estado == ESTADO_ALERTA:
            return COLOR_ALERTA
        if estado == ESTADO_ESPERA:
            return COLOR_ESPERA
        return COLOR_ERROR

    @staticmethod
    def color_bgr_por_estado(estado: str) -> Tuple[int, int, int]:
        if estado == ESTADO_OK:
            return COLOR_OK_BGR
        if estado == ESTADO_ALERTA:
            return COLOR_ALERTA_BGR
        if estado == ESTADO_ESPERA:
            return COLOR_ESPERA_BGR
        return COLOR_ERROR_BGR

    @staticmethod
    def fondo_por_estado(estado: str) -> str:
        """Fondo claro del panel de estado; el texto siempre va en negro."""
        return FONDOS_POR_ESTADO.get(estado, FONDO_ESPERA)

    @staticmethod
    def generar(reglas: Sequence[ResultadoRegla]) -> Tuple[str, str, str]:
        """Devuelve ``(mensaje_principal, color, mensaje_completo)``.

        El mensaje principal es el de la regla con mayor prioridad de
        gravedad; el mensaje completo concatena las correcciones pendientes.
        """
        if not reglas:
            return "Sin datos", COLOR_ESPERA, "Sin datos"

        principal = reglas[0]
        pendientes = [
            r.mensaje for r in reglas
            if r.estado in (ESTADO_ALERTA, ESTADO_ERROR, ESTADO_ESPERA)
        ]
        if pendientes:
            completo = " | ".join(pendientes)
        elif all(r.estado == ESTADO_OK for r in reglas):
            completo = "Ritmo y tecnica correctos"
        else:
            completo = principal.mensaje
        return principal.mensaje, GeneradorFeedback.color_por_estado(principal.estado), completo

    @staticmethod
    def lista_mensajes(reglas: Sequence[ResultadoRegla]) -> List[str]:
        """Mensajes de todas las reglas, para el registro de la interfaz."""
        return [f"[{r.id}] {r.nombre}: {r.mensaje}" for r in reglas]