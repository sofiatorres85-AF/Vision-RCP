"""Analizador RCP: señal de compresión, frecuencia, profundidad y geometría.

Este módulo es puro cálculo (no depende de OpenCV ni de Tkinter) para poder
verificarse de forma aislada en las pruebas de precisión RNF-02 y RNF-03.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

from .configuracion import (
    Configuracion,
    INDICE_CADERA_DERECHA,
    INDICE_CADERA_IZQUIERDA,
    INDICE_CODO_DERECHO,
    INDICE_CODO_IZQUIERDO,
    INDICE_HOMBRO_DERECHO,
    INDICE_HOMBRO_IZQUIERDO,
    INDICE_MUNECA_DERECHA,
    INDICE_MUNECA_IZQUIERDA,
)

Punto = Tuple[float, float]


def angulo_abc(a: Punto, b: Punto, c: Punto) -> float:  # type: ignore[valid-type]
    """Ángulo ABC en grados, con ``b`` como vértice.

    Se usa para RF-07 / CA-07 con los tríos hombro-codo-muñeca.
    """
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    vc = np.array(c, dtype=float)
    ba, bc = va - vb, vc - vb
    norma = np.linalg.norm(ba) * np.linalg.norm(bc)
    if norma < 1e-6:
        return 0.0
    coseno = np.dot(ba, bc) / norma
    return float(np.degrees(np.arccos(np.clip(coseno, -1.0, 1.0))))


def punto_medio(p1: Punto, p2: Punto) -> Punto:  # type: ignore[valid-type]
    """Punto medio de dos landmarks."""
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


@dataclass
class Metricas:
    """Resultado del análisis para un fotograma."""

    #: Compresiones por minuto (0.0 si aún no hay ciclos completos).
    cpm: float = 0.0
    #: Profundidad media de las últimas compresiones en centímetros.
    profundidad_cm: float = 0.0
    #: Número total de compresiones contadas en la sesión.
    compresiones: int = 0
    #: Separación entre las dos muñecas en centímetros (None sin escala).
    distancia_munecas_cm: Optional[float] = None
    #: Distancia del punto medio de las muñecas a la referencia torácica, en cm.
    distancia_esternon_cm: Optional[float] = None
    #: Ángulo medio hombro-codo-muñeca en grados (RF-07).
    angulo_brazo_grados: Optional[float] = None
    #: Las manos están sobre el centro del tórax (RF-05).
    esternon_ok: bool = False
    #: El tórax volvió por completo entre compresiones (RF-06).
    retorno_ok: bool = True
    #: Desnivel de los hombros respecto de la línea base, en cm.
    desvio_hombros_cm: Optional[float] = None
    #: Píxeles por centímetro según el marcador ArUco (None sin escala).
    px_por_cm: Optional[float] = None
    #: El detector vio el torso y las manos del usuario.
    pose_detectada: bool = False
    #: Posición de las muñecas en píxeles (para la superposición).
    munecas_px: Optional[Punto] = None
    #: Posición de los hombros en píxeles.
    hombros_px: Optional[Punto] = None
    #: Posición de las caderas en píxeles.
    caderas_px: Optional[Punto] = None


class ContadorCompresiones:
    """Detector de ciclos de compresión sobre la señal vertical de las muñecas.

    La señal ``y`` crece hacia abajo. Cada compresión es un ciclo
    ``alto -> fondo -> subida``; se cuenta una compresión al confirmar el
    valle siempre que la amplitud supere ``amplitud_minima_cm`` y haya
    pasado el intervalo mínimo entre compresiones.
    """

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.reiniciar()

    def reiniciar(self) -> None:
        self.compresiones = 0
        self.profundidades: deque = deque(maxlen=self.config.muestras_para_profundidad)
        self.intervalos: deque = deque(maxlen=self.config.muestras_para_frecuencia)
        self.profundidad_ultima = 0.0
        self._instante_ultima_compresion: Optional[float] = None
        self._anterior: Optional[float] = None
        self._direccion = 0            # 1 = bajando, -1 = subiendo
        self._punto_alto: Optional[float] = None
        self._extremo: Optional[float] = None

    def actualizar(self, y_cm: float, instante: float) -> bool:
        """Registra una muestra; devuelve ``True`` si contó una compresión."""
        if self._anterior is None:
            self._anterior = y_cm
            self._extremo = y_cm
            self._punto_alto = y_cm
            return False

        delta = y_cm - self._anterior
        umbral = 0.05
        nueva_direccion = 1 if delta > umbral else (-1 if delta < -umbral else self._direccion)
        contada = False

        if self._direccion == 0:
            self._direccion = nueva_direccion
            self._extremo = y_cm

        if nueva_direccion != 0 and nueva_direccion != self._direccion:
            if self._direccion == 1 and nueva_direccion == -1:
                # Venía bajando y empieza a subir: se confirma el valle (fondo).
                valle = self._extremo
                alto = self._punto_alto if self._punto_alto is not None else valle
                amplitud = valle - alto
                anterior = self._instante_ultima_compresion
                if amplitud >= self.config.amplitud_minima_compresion_cm:
                    if anterior is None or (instante - anterior) >= self.config.intervalo_minimo_compresion_s:
                        self.compresiones += 1
                        self.profundidad_ultima = round(float(amplitud), 2)
                        self.profundidades.append(self.profundidad_ultima)
                        if anterior is not None:
                            self.intervalos.append(instante - anterior)
                        self._instante_ultima_compresion = instante
                        contada = True
            elif self._direccion == -1 and nueva_direccion == 1:
                # Venía subiendo y empieza a bajar: nuevo punto alto.
                self._punto_alto = self._extremo
            self._direccion = nueva_direccion
            self._extremo = y_cm
        else:
            if self._direccion == 1:
                self._extremo = max(self._extremo, y_cm)
            elif self._direccion == -1:
                self._extremo = min(self._extremo, y_cm)
            else:
                self._extremo = y_cm

        self._anterior = y_cm
        return contada

    def frecuencia_cpm(self) -> float:
        """CPM = 60 / promedio de los últimos intervalos entre compresiones."""
        if not self.intervalos:
            return 0.0
        promedio = float(np.mean(list(self.intervalos)))
        if promedio <= 0:
            return 0.0
        return round(60.0 / promedio, 1)

    def profundidad_media_cm(self) -> float:
        """Profundidad media de las últimas compresiones (RN-02)."""
        if not self.profundidades:
            return 0.0
        return round(float(np.mean(list(self.profundidades))), 2)


class AnalizadorRCP:
    """Convierte landmarks y escala ArUco en :class:`Metricas` por fotograma."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.contador = ContadorCompresiones(self.config)
        self.historial_y: deque = deque(maxlen=self.config.muestras_historial)
        self.historial_hombros: deque = deque(maxlen=self.config.muestras_historial)
        self.linea_base_y_px: Optional[float] = None
        self.linea_base_hombros_px: Optional[float] = None
        #: Senal vertical suavizada actual, en cm respecto de la línea base.
        self.senal_cm = 0.0

    # -- gestión del estado ------------------------------------------------
    def reiniciar(self) -> None:
        """Reinicia contador y líneas base (botón de calibración)."""
        self.contador.reiniciar()
        self.historial_y.clear()
        self.historial_hombros.clear()
        self.linea_base_y_px = None
        self.linea_base_hombros_px = None
        self.senal_cm = 0.0

    # -- cálculo por fotograma --------------------------------------------
    def actualizar(
        self,
        instante: float,
        landmarks_px: Dict[int, Punto],
        centro_aruco_px: Optional[Punto] = None,
        lado_aruco_px: Optional[float] = None,
    ) -> Metricas:
        """Procesa un fotograma.

        ``landmarks_px`` mapea índice de MediaPipe a ``(x, y)`` en píxeles.
        ``centro_aruco_px`` y ``lado_aruco_px`` provenienen del marcador que
        actúa como referencia de escala (RF-04).
        """
        metricas = Metricas()
        metricas.compresiones = self.contador.compresiones

        escala = self._escala_px_por_cm(lado_aruco_px)
        metricas.px_por_cm = escala

        if not self._pose_completa(landmarks_px):
            return metricas

        metricas.pose_detectada = True
        hombro_izq = landmarks_px[INDICE_HOMBRO_IZQUIERDO]
        hombro_der = landmarks_px[INDICE_HOMBRO_DERECHO]
        codo_izq = landmarks_px[INDICE_CODO_IZQUIERDO]
        codo_der = landmarks_px[INDICE_CODO_DERECHO]
        muneca_izq = landmarks_px[INDICE_MUNECA_IZQUIERDA]
        muneca_der = landmarks_px[INDICE_MUNECA_DERECHA]

        metricas.hombros_px = punto_medio(hombro_izq, hombro_der)
        metricas.caderas_px = punto_medio(
            landmarks_px[INDICE_CADERA_IZQUIERDA], landmarks_px[INDICE_CADERA_DERECHA]
        )
        metricas.munecas_px = punto_medio(muneca_izq, muneca_der)

        # RF-07 / RN-05: ángulo hombro-codo-muñeca de ambos brazos.
        angulo_izq = angulo_abc(hombro_izq, codo_izq, muneca_izq)
        angulo_der = angulo_abc(hombro_der, codo_der, muneca_der)
        metricas.angulo_brazo_grados = round((angulo_izq + angulo_der) / 2.0, 1)

        ancho_hombros_px = float(np.hypot(hombro_izq[0] - hombro_der[0], hombro_izq[1] - hombro_der[1]))

        # RF-05 / RN-03: distancia entre muñecas y centricidad torácica.
        separacion_munecas_px = float(
            np.hypot(muneca_izq[0] - muneca_der[0], muneca_izq[1] - muneca_der[1])
        )
        if escala:
            metricas.distancia_munecas_cm = round(separacion_munecas_px / escala, 2)

        referencia = centro_aruco_px or metricas.hombros_px
        if escala and ancho_hombros_px > 1.0:
            desalineacion_px = abs(metricas.munecas_px[0] - referencia[0])
            metricas.distancia_esternon_cm = round(desalineacion_px / escala, 2)
            desalineacion_relativa = desalineacion_px / ancho_hombros_px
            manos_juntas = (
                metricas.distancia_munecas_cm is None
                or metricas.distancia_munecas_cm <= self.config.distancia_maxima_munecas_cm
            )
            metricas.esternon_ok = (
                desalineacion_relativa <= self.config.tolerancia_desalineacion_esternon and manos_juntas
            )
        else:
            metricas.esternon_ok = False

        # RF-06 / RN-04: retorno torácico medido con la elevación de los hombros.
        y_hombros = metricas.hombros_px[1]
        self.historial_hombros.append(y_hombros)
        if (
            self.linea_base_hombros_px is None
            and len(self.historial_hombros) > self.config.muestras_linea_base_hombros
        ):
            self.linea_base_hombros_px = float(np.mean(list(self.historial_hombros)[:-1]))
        if self.linea_base_hombros_px is not None and escala:
            y_suavizada_hombros = float(np.mean(list(self.historial_hombros)[-self.config.muestras_suavizado:]))
            desvio = (y_suavizada_hombros - self.linea_base_hombros_px) / escala
            metricas.desvio_hombros_cm = round(desvio, 2)
            metricas.retorno_ok = desvio < self.config.tolerancia_retorno_cm

        # RF-03 / RF-04: señal vertical de las muñecas -> profundidad y cpm.
        y_munecas = metricas.munecas_px[1]
        self.historial_y.append(y_munecas)
        ventana = list(self.historial_y)[-self.config.muestras_suavizado:]
        y_suavizada = float(np.mean(ventana))
        if self.linea_base_y_px is None:
            self.linea_base_y_px = y_suavizada
        # Sin escala se usa una referencia aproximada de 10 px/cm.
        divisor = escala if escala else 10.0
        self.senal_cm = (y_suavizada - self.linea_base_y_px) / divisor
        self.contador.actualizar(self.senal_cm, instante)

        metricas.compresiones = self.contador.compresiones
        metricas.cpm = self.contador.frecuencia_cpm()
        metricas.profundidad_cm = self.contador.profundidad_media_cm()
        return metricas

    # -- auxiliares -------------------------------------------------------
    def _escala_px_por_cm(self, lado_aruco_px: Optional[float]) -> Optional[float]:
        if not self.config.escalado_aruco or not lado_aruco_px:
            return None
        if self.config.tamano_marcador_cm <= 0:
            return None
        return float(lado_aruco_px) / self.config.tamano_marcador_cm

    def _pose_completa(self, landmarks_px: Dict[int, Punto]) -> bool:
        return all(indice in landmarks_px for indice in self.config.indices_requeridos)

    def senal_historial(self) -> Sequence[float]:
        """Historial de la señal suavizada, para la mini-gráfica."""
        return list(self.historial_y)