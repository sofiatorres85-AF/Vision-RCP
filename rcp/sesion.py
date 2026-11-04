"""Gestor de sesión (RF-09 / CA-09 y registro de errores CA-05, CA-06, CA-07).

Mantiene el estado de la sesión, promedia el desempeño, registra cada error
con su marca de tiempo y produce el resumen mostrado al finalizar.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, List, Optional, Sequence

from .configuracion import Configuracion
from .reglas import ESTADO_ALERTA, ESTADO_ERROR, ResultadoRegla


@dataclass(frozen=True)
class ErrorDetectado:
    """Error técnico registrado con su marca de tiempo (CA-05/06/07)."""

    regla_id: str
    nombre: str
    mensaje: str
    #: Marca de tiempo legible: ``HH:MM:SS.mmm``.
    marca_tiempo: str
    #: Tiempo relativo al inicio de la sesión, en segundos.
    instante_s: float
    valor: Optional[float] = None

    def __str__(self) -> str:
        valor = "" if self.valor is None else f" valor={self.valor:.1f}"
        return f"[{self.marca_tiempo}] {self.regla_id} {self.nombre}: {self.mensaje}{valor}"


@dataclass
class ResumenSesion:
    """Resumen de desempeño mostrado al finalizar la sesión (CA-09)."""

    duracion_s: float = 0.0
    compresiones: int = 0
    frecuencia_promedio_cpm: float = 0.0
    profundidad_promedio_cm: float = 0.0
    fps_promedio: float = 0.0
    tiempo_proceso_promedio_ms: float = 0.0
    errores: List[ErrorDetectado] = field(default_factory=list)

    def como_texto(self) -> str:
        lineas = [
            "=== RESUMEN DE SESIÓN ===",
            f"Duración:               {self.duracion_s:.1f} s",
            f"Compresiones:           {self.compresiones}",
            f"Frecuencia promedio:    {self.frecuencia_promedio_cpm:.1f} cpm",
            f"Profundidad promedio:   {self.profundidad_promedio_cm:.2f} cm",
            f"FPS promedio:           {self.fps_promedio:.1f}",
            f"Tiempo de proceso:      {self.tiempo_proceso_promedio_ms:.1f} ms/fotograma",
            f"Errores detectados:     {len(self.errores)}",
        ]
        if self.errores:
            lineas.append("")
            lineas.append("Detalle de errores (marca de tiempo):")
            conteo: dict = {}
            for error in self.errores:
                conteo[error.nombre] = conteo.get(error.nombre, 0) + 1
            for nombre, total in conteo.items():
                lineas.append(f"  - {nombre}: {total}")
            lineas.append("")
            lineas.append("Primeros 15 registros:")
            for error in self.errores[:15]:
                lineas.append(f"  {error}")
        return "\n".join(lineas)


class CuentaAtras:
    """Cuenta regresiva de posicionamiento previa a la sesión (RNF-04).

    Lógica pura, sin dependencias de Tkinter ni OpenCV, de modo que pueda
    verificarse en ``pruebas/test_criterios.py``.

    Flujo::

        cuenta = CuentaAtras(5)
        cuenta.iniciar()    -> 5   (segundos restantes)
        cuenta.avanzar()    -> 4
        ...
        cuenta.avanzar()    -> 0   y ``terminada`` pasa a True
    """

    def __init__(self, segundos: int = 5) -> None:
        self.segundos_totales = max(0, int(segundos))
        self.restantes = 0
        self.en_curso = False

    @property
    def terminada(self) -> bool:
        """``True`` cuando no hay cuenta regresiva en curso."""
        return not self.en_curso

    @property
    def en_ejecucion(self) -> bool:
        return self.en_curso

    def iniciar(self) -> int:
        """Arranca la cuenta regresiva y devuelve los segundos restantes."""
        self.restantes = self.segundos_totales
        self.en_curso = self.segundos_totales > 0
        return self.restantes

    def avanzar(self) -> int:
        """Descuenta un segundo y devuelve los restantes (0 al terminar)."""
        if not self.en_curso:
            return 0
        self.restantes = max(0, self.restantes - 1)
        if self.restantes == 0:
            self.en_curso = False
        return self.restantes

    def cancelar(self) -> None:
        """Corta la cuenta regresiva sin arrancar la sesión."""
        self.en_curso = False
        self.restantes = 0


class Sesion:
    """Estado y métricas agregadas de una sesión de entrenamiento."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.activa = False
        self.inicio: Optional[float] = None
        self.fin: Optional[float] = None
        self.errores: List[ErrorDetectado] = []
        self._ultimo_registro: dict = {}
        self._frecuencias: Deque[float] = deque(maxlen=600)
        self._profundidades: Deque[float] = deque(maxlen=600)
        self._fps: Deque[float] = deque(maxlen=600)
        self._tiempos_proceso: Deque[float] = deque(maxlen=600)
        self.compresiones = 0

    # -- ciclo de vida ---------------------------------------------------
    def iniciar(self, instante: Optional[float] = None) -> None:
        ahora = instante if instante is not None else time.time()
        self.activa = True
        self.inicio = ahora
        self.fin = None
        self.compresiones = 0
        self.errores.clear()
        self._ultimo_registro.clear()
        self._frecuencias.clear()
        self._profundidades.clear()
        self._fps.clear()
        self._tiempos_proceso.clear()

    def finalizar(self, instante: Optional[float] = None) -> ResumenSesion:
        self.activa = False
        self.fin = instante if instante is not None else time.time()
        return self.resumen()

    def duracion_s(self) -> float:
        if self.inicio is None:
            return 0.0
        fin = self.fin if self.fin is not None else time.time()
        return max(0.0, fin - self.inicio)

    # -- acumulación por fotograma --------------------------------------
    def registrar_fotograma(
        self,
        compresiones: int,
        cpm: float,
        profundidad_cm: float,
        fps: float,
        tiempo_proceso_ms: float,
    ) -> None:
        """Acumula los valores del fotograma para el resumen."""
        if not self.activa:
            return
        self.compresiones = compresiones
        if cpm > 0:
            self._frecuencias.append(cpm)
        if profundidad_cm > 0:
            self._profundidades.append(profundidad_cm)
        if fps > 0:
            self._fps.append(fps)
        if tiempo_proceso_ms > 0:
            self._tiempos_proceso.append(tiempo_proceso_ms)

    # -- registro de errores con marca de tiempo ------------------------
    def registrar_reglas(self, reglas: Sequence[ResultadoRegla]) -> List[ErrorDetectado]:
        """Registra las reglas incumplidas, evitando duplicados seguidos.

        Devuelve los errores nuevos registrados en este fotograma.
        """
        if not self.activa:
            return []
        nuevos: List[ErrorDetectado] = []
        ahora = time.time()
        transcurrido = self.duracion_s()
        for regla in reglas:
            if regla.estado not in (ESTADO_ALERTA, ESTADO_ERROR):
                self._ultimo_registro.pop(regla.id, None)
                continue
            ultimo = self._ultimo_registro.get(regla.id)
            if ultimo is not None and (ahora - ultimo) < self.config.enfriamiento_error_s:
                continue
            self._ultimo_registro[regla.id] = ahora
            error = ErrorDetectado(
                regla_id=regla.id,
                nombre=regla.nombre,
                mensaje=regla.mensaje,
                marca_tiempo=datetime.now().strftime("%H:%M:%S.%f")[:-3],
                instante_s=round(transcurrido, 2),
                valor=regla.valor,
            )
            self.errores.append(error)
            nuevos.append(error)
        return nuevos

    # -- resumen ---------------------------------------------------------
    def resumen(self) -> ResumenSesion:
        def promedio(coleccion: Deque[float]) -> float:
            return float(sum(coleccion) / len(coleccion)) if coleccion else 0.0

        return ResumenSesion(
            duracion_s=round(self.duracion_s(), 1),
            compresiones=self.compresiones,
            frecuencia_promedio_cpm=round(promedio(self._frecuencias), 1),
            profundidad_promedio_cm=round(promedio(self._profundidades), 2),
            fps_promedio=round(promedio(self._fps), 1),
            tiempo_proceso_promedio_ms=round(promedio(self._tiempos_proceso), 1),
            errores=list(self.errores),
        )