"""Motor de reglas RCP (RN-01 a RN-06).

Cada regla evalúa las :class:`~rcp.analisis.Metricas` de un fotograma y
devuelve un :class:`ResultadoRegla` con el estado de cumplimiento. El
generador de feedback y el gestor de sesión consumen estos resultados
(RF-08, CA-05, CA-06, CA-07).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .analisis import Metricas
from .configuracion import Configuracion

# Estados posibles de una regla.
ESTADO_OK = "ok"
ESTADO_ALERTA = "alerta"
ESTADO_ERROR = "error"
ESTADO_ESPERA = "espera"

#: Prioridad para elegir el mensaje principal del feedback (menor = más grave).
_PRIORIDAD = {ESTADO_ERROR: 0, ESTADO_ALERTA: 1, ESTADO_ESPERA: 2, ESTADO_OK: 3}


@dataclass(frozen=True)
class ResultadoRegla:
    """Resultado de evaluar una regla sobre las métricas de un fotograma."""

    id: str
    nombre: str
    estado: str
    mensaje: str
    valor: Optional[float] = None

    @property
    def cumple(self) -> bool:
        """``True`` solo cuando la regla se cumple plenamente."""
        return self.estado == ESTADO_OK


class MotorReglas:
    """Evalúa el conjunto de reglas de negocio sobre las métricas."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()

    def evaluar(self, metricas: Metricas) -> List[ResultadoRegla]:
        """Devuelve un resultado por regla, en orden de gravedad."""
        reglas = [
            self.regla_pose_detectada(metricas),
            self.regla_frecuencia(metricas),
            self.regla_profundidad(metricas),
            self.regla_posicion_manos(metricas),
            self.regla_retorno_toracico(metricas),
            self.regla_rectitud_brazos(metricas),
        ]
        return sorted(reglas, key=lambda r: _PRIORIDAD.get(r.estado, 9))

    # -- RN-01 / RF-03 / CA-03 -------------------------------------------
    def regla_frecuencia(self, metricas: Metricas) -> ResultadoRegla:
        if not metricas.pose_detectada:
            return ResultadoRegla("RN-01", "Frecuencia", ESTADO_ESPERA, "Sin postura detectada")
        cpm = metricas.cpm
        if cpm <= 0.0:
            return ResultadoRegla("RN-01", "Frecuencia", ESTADO_ESPERA, "Inicie las compresiones", cpm)
        if cpm < self.config.cpm_minimo:
            return ResultadoRegla(
                "RN-01", "Frecuencia", ESTADO_ALERTA,
                f"Aumente la frecuencia ({cpm:.0f} cpm)", cpm,
            )
        if cpm > self.config.cpm_maximo:
            return ResultadoRegla(
                "RN-01", "Frecuencia", ESTADO_ALERTA,
                f"Reduzca la frecuencia ({cpm:.0f} cpm)", cpm,
            )
        return ResultadoRegla("RN-01", "Frecuencia", ESTADO_OK, f"Ritmo correcto ({cpm:.0f} cpm)", cpm)

    # -- RN-02 / RF-04 / CA-04 -------------------------------------------
    def regla_profundidad(self, metricas: Metricas) -> ResultadoRegla:
        if not metricas.pose_detectada:
            return ResultadoRegla("RN-02", "Profundidad", ESTADO_ESPERA, "Sin postura detectada")
        profundidad = metricas.profundidad_cm
        if profundidad <= 0.0:
            return ResultadoRegla("RN-02", "Profundidad", ESTADO_ESPERA, "Inicie las compresiones", profundidad)
        if profundidad < self.config.profundidad_minima_cm:
            return ResultadoRegla(
                "RN-02", "Profundidad", ESTADO_ALERTA,
                f"Presione más hondo ({profundidad:.1f} cm)", profundidad,
            )
        if profundidad > self.config.profundidad_maxima_cm:
            return ResultadoRegla(
                "RN-02", "Profundidad", ESTADO_ALERTA,
                f"Presione menos hondo ({profundidad:.1f} cm)", profundidad,
            )
        return ResultadoRegla(
            "RN-02", "Profundidad", ESTADO_OK,
            f"Profundidad correcta ({profundidad:.1f} cm)", profundidad,
        )

    # -- RN-03 / RF-05 / CA-05 -------------------------------------------
    def regla_posicion_manos(self, metricas: Metricas) -> ResultadoRegla:
        if not metricas.pose_detectada:
            return ResultadoRegla("RN-03", "Posición de manos", ESTADO_ESPERA, "Sin postura detectada")
        if metricas.distancia_munecas_cm is None:
            return ResultadoRegla(
                "RN-03", "Posición de manos", ESTADO_ESPERA,
                "Muestre el marcador ArUco para medir la posición", None,
            )
        if metricas.distancia_munecas_cm > self.config.distancia_maxima_munecas_cm:
            return ResultadoRegla(
                "RN-03", "Posición de manos", ESTADO_ALERTA,
                f"Junte las manos ({metricas.distancia_munecas_cm:.0f} cm de separación)",
                metricas.distancia_munecas_cm,
            )
        if not metricas.esternon_ok:
            return ResultadoRegla(
                "RN-03", "Posición de manos", ESTADO_ALERTA,
                "Centra las manos sobre el esternón", metricas.distancia_esternon_cm,
            )
        return ResultadoRegla(
            "RN-03", "Posición de manos", ESTADO_OK,
            "Manos sobre el centro del tórax", metricas.distancia_munecas_cm,
        )

    # -- RN-04 / RF-06 / CA-06 -------------------------------------------
    def regla_retorno_toracico(self, metricas: Metricas) -> ResultadoRegla:
        if not metricas.pose_detectada:
            return ResultadoRegla("RN-04", "Retorno torácico", ESTADO_ESPERA, "Sin postura detectada")
        if metricas.desvio_hombros_cm is None:
            return ResultadoRegla("RN-04", "Retorno torácico", ESTADO_ESPERA, "Sin escala de referencia")
        if not metricas.retorno_ok:
            return ResultadoRegla(
                "RN-04", "Retorno torácico", ESTADO_ERROR,
                "Retorno torácico incompleto: los hombros no recuperan la altura",
                metricas.desvio_hombros_cm,
            )
        return ResultadoRegla("RN-04", "Retorno torácico", ESTADO_OK, "Retorno torácico completo")

    # -- RN-05 / RF-07 / CA-07 -------------------------------------------
    def regla_rectitud_brazos(self, metricas: Metricas) -> ResultadoRegla:
        if not metricas.pose_detectada:
            return ResultadoRegla("RN-05", "Rectitud de brazos", ESTADO_ESPERA, "Sin postura detectada")
        angulo = metricas.angulo_brazo_grados
        if angulo is None:
            return ResultadoRegla("RN-05", "Rectitud de brazos", ESTADO_ESPERA, "Sin datos de codos")
        if angulo < self.config.angulo_brazo_minimo:
            return ResultadoRegla(
                "RN-05", "Rectitud de brazos", ESTADO_ALERTA,
                f"Estire los brazos ({angulo:.0f}°)", angulo,
            )
        return ResultadoRegla("RN-05", "Rectitud de brazos", ESTADO_OK, "Brazos extendidos", angulo)

    # -- Requisito previo de RF-02 ---------------------------------------
    def regla_pose_detectada(self, metricas: Metricas) -> ResultadoRegla:
        if metricas.pose_detectada:
            return ResultadoRegla("RF-02", "Postura visible", ESTADO_OK, "Hombros, codos, muñecas y caderas detectados")
        return ResultadoRegla("RF-02", "Postura visible", ESTADO_ESPERA, "Muestre hombros, caderas y manos a la cámara")