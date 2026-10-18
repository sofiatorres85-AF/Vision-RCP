"""Paquete del sistema de análisis de técnica RCP.

Módulos (equivalentes a los de la Figura 10 del documento):

- ``configuracion``  Parámetros y umbrales derivados de los RN.
- ``captura``        Módulo de captura de video (cámara web).
- ``modelos``        Carga/descarga de los modelos MediaPipe Tasks.
- ``procesamiento``  Procesamiento de imagen: ArUco y landmarks de Pose.
- ``analisis``       Analizador RCP: frecuencia, profundidad y geometría.
- ``reglas``         Motor de reglas RCP (RN-01 a RN-06).
- ``retroalimentacion`` Generador de feedback (mensajes y color).
- ``sesion``         Gestor de sesión: métricas, errores y resumen.
- ``interfaz``       Interfaz gráfica Tkinter.
"""

__all__ = [
    "configuracion",
    "captura",
    "modelos",
    "procesamiento",
    "analisis",
    "reglas",
    "retroalimentacion",
    "sesion",
    "interfaz",
]