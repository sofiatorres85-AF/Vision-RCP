"""Módulo de procesamiento de imagen.

Responsabilidades:
* detectar el marcador ArUco que da la escala en centímetros (RF-04);
* extraer los landmarks de MediaPipe Pose (RF-02) como índices normalizados;
* dibujar la superposición de landmarks e indicadores (RF-08, CA-02, CA-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .analisis import Metricas
from .configuracion import Configuracion, CONEXIONES_POSE, INDICES_REQUERIDOS

Punto = Tuple[float, float]


# ---------------------------------------------------------------- ArUco ---
@dataclass(frozen=True)
class ResultadoArUco:
    """Marcador ArUco detectado en el fotograma."""

    ids: Tuple[int, ...] = ()
    centro_px: Optional[Punto] = None
    lado_px: Optional[float] = None

    @property
    def detectado(self) -> bool:
        return self.centro_px is not None


class ProcesadorArUco:
    """Detección del marcador de referencia (ArUco)."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.diccionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.parametros = cv2.aruco.DetectorParameters()
        try:
            self._detector = cv2.aruco.ArucoDetector(self.diccionario, self.parametros)
            self._api_nueva = True
        except AttributeError:  # pragma: no cover - OpenCV < 4.7
            self._detector = None
            self._api_nueva = False

    def detectar(self, frame_bgr: np.ndarray, dibujar: bool = True) -> ResultadoArUco:
        if frame_bgr is None or frame_bgr.size == 0:
            return ResultadoArUco()
        gris = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        if self._api_nueva:
            esquinas, ids, _ = self._detector.detectMarkers(gris)
        else:  # pragma: no cover - OpenCV < 4.7
            esquinas, ids, _ = cv2.aruco.detectMarkers(
                gris, self.diccionario, parameters=self.parametros
            )

        if ids is None or len(ids) == 0:
            return ResultadoArUco()

        if dibujar:
            cv2.aruco.drawDetectedMarkers(frame_bgr, esquinas, ids)

        lista_ids = [int(i) for i in ids.flatten()]
        indice = 0
        if self.config.id_marcador_objetivo in lista_ids:
            indice = lista_ids.index(self.config.id_marcador_objetivo)

        esquinas_obj = np.asarray(esquinas[indice][0], dtype=float)
        centro = (
            float(esquinas_obj[:, 0].mean()),
            float(esquinas_obj[:, 1].mean()),
        )
        lados = [
            float(np.linalg.norm(esquinas_obj[i] - esquinas_obj[(i + 1) % 4]))
            for i in range(4)
        ]
        lado_px = float(np.mean(lados))
        if dibujar:
            cv2.circle(frame_bgr, (int(centro[0]), int(centro[1])), 6, (0, 200, 0), -1)
            cv2.putText(
                frame_bgr,
                f"ArUco ID {lista_ids[indice]} - {self.config.tamano_marcador_cm:.1f} cm",
                (int(centro[0]) - 60, int(centro[1]) - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 200, 0),
                2,
            )
        return ResultadoArUco(ids=tuple(lista_ids), centro_px=centro, lado_px=lado_px)


# ----------------------------------------------------------------- Pose ---
class ProcesadorPose:
    """Extrae landmarks de MediaPipe Pose en coordenadas de píxeles."""

    def __init__(self, config: Optional[Configuracion] = None) -> None:
        self.config = config or Configuracion()
        self.landmarker = None

    def iniciar(self) -> bool:
        """Carga el modelo. ``False`` si no está disponible."""
        from .modelos import crear_pose_landmarker

        self.landmarker = crear_pose_landmarker(self.config)
        return self.landmarker is not None

    def procesar(self, frame_bgr: np.ndarray, marca_tiempo_ms: int) -> Dict[int, Punto]:
        """Devuelve ``{indice: (x_px, y_px)}`` de los landmarks requeridos."""
        vacio: Dict[int, Punto] = {}
        if self.landmarker is None or frame_bgr is None or frame_bgr.size == 0:
            return vacio
        try:
            import mediapipe as mp

            alto, ancho = frame_bgr.shape[:2]
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            resultado = self.landmarker.detect_for_video(imagen, marca_tiempo_ms)
            if not resultado.pose_landmarks:
                return vacio
            puntos = resultado.pose_landmarks[0]
            mapa: Dict[int, Punto] = {}
            for indice in self.config.indices_requeridos:
                punto = puntos[indice]
                mapa[indice] = (float(punto.x * ancho), float(punto.y * alto))
            return mapa
        except Exception as error:  # pragma: no cover - dependiente del modelo
            print(f"Error de pose: {error}")
            return vacio

    def cerrar(self) -> None:
        if self.landmarker is not None:
            try:
                self.landmarker.close()
            except Exception:  # pragma: no cover
                pass
            self.landmarker = None


# ------------------------------------------------------------ Dibujante ---
class Dibujante:
    """Superposición de landmarks e indicadores sobre el video (RF-09)."""

    COLORES_PUNTO = {
        11: (255, 160, 0),
        12: (255, 160, 0),
        13: (0, 200, 255),
        14: (0, 200, 255),
        15: (0, 0, 255),
        16: (0, 0, 255),
        23: (255, 0, 255),
        24: (255, 0, 255),
    }

    def dibujar_landmarks(self, frame: np.ndarray, landmarks_px: Dict[int, Punto]) -> None:
        """Dibuja los ocho landmarks requeridos y sus conexiones (CA-02)."""
        for a, b in CONEXIONES_POSE:
            if a in landmarks_px and b in landmarks_px:
                pa = (int(landmarks_px[a][0]), int(landmarks_px[a][1]))
                pb = (int(landmarks_px[b][0]), int(landmarks_px[b][1]))
                cv2.line(frame, pa, pb, (0, 220, 0), 2)
        for indice in INDICES_REQUERIDOS:
            if indice not in landmarks_px:
                continue
            centro = (int(landmarks_px[indice][0]), int(landmarks_px[indice][1]))
            cv2.circle(frame, centro, 5, self.COLORES_PUNTO[indice], -1)
        # Etiquetas de los grupos requeridos por RF-02.
        etiquetas = {
            11: "Hombro izq",
            12: "Hombro der",
            13: "Codo izq",
            14: "Codo der",
            15: "Muneca izq",
            16: "Muneca der",
            23: "Cadera izq",
            24: "Cadera der",
        }
        for indice, texto in etiquetas.items():
            if indice in landmarks_px:
                x, y = int(landmarks_px[indice][0]), int(landmarks_px[indice][1])
                cv2.putText(frame, texto, (x + 7, y - 7), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, self.COLORES_PUNTO[indice], 1, cv2.LINE_AA)

    def dibujar_indicadores(
        self,
        frame: np.ndarray,
        metricas: Metricas,
        mensaje: str,
        color_bgr: Tuple[int, int, int],
    ) -> None:
        """Panel superior con cpm, profundidad y mensaje de corrección."""
        alto = frame.shape[0]
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 76), (25, 25, 25), -1)

        cv2.putText(frame, f"{metricas.cpm:.0f} cpm", (14, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color_bgr, 2, cv2.LINE_AA)
        cv2.putText(frame, f"{metricas.profundidad_cm:.1f} cm", (190, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color_bgr, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Compresiones: {metricas.compresiones}", (14, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
        if metricas.angulo_brazo_grados is not None:
            cv2.putText(frame, f"Brazos: {metricas.angulo_brazo_grados:.0f} deg", (200, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
        if metricas.distancia_munecas_cm is not None:
            cv2.putText(frame, f"Munecas: {metricas.distancia_munecas_cm:.0f} cm", (400, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)

        # Mensaje de corrección en la parte inferior.
        ancho_texto, _ = cv2.getTextSize(mensaje, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        posicion = ((frame.shape[1] - ancho_texto[0]) // 2, alto - 18)
        cv2.putText(frame, mensaje, posicion, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2, cv2.LINE_AA)

    def dibujar_senal(self, frame: np.ndarray, valores: Sequence[float]) -> None:
        """Mini-gráfica de la señal vertical de las muñecas."""
        if len(valores) < 5:
            return
        alto, ancho = frame.shape[:2]
        x0, y0, ancho_g, alto_g = 14, alto - 130, 240, 100
        cv2.rectangle(frame, (x0, y0), (x0 + ancho_g, y0 + alto_g), (25, 25, 25), -1)
        referencia = float(np.mean(list(valores)[-30:]))
        normalizado = [v - referencia for v in list(valores)[-90:]]
        maximo = max(20.0, max(abs(v) for v in normalizado))
        puntos: List[Tuple[int, int]] = []
        for i, valor in enumerate(normalizado):
            x = int(x0 + i / max(1, len(normalizado) - 1) * ancho_g)
            y = int(y0 + alto_g / 2 + valor / maximo * (alto_g / 2 - 6))
            puntos.append((x, y))
        for i in range(1, len(puntos)):
            cv2.line(frame, puntos[i - 1], puntos[i], (0, 220, 0), 2)
        cv2.putText(frame, "Senal munecas", (x0 + 6, y0 + 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (220, 220, 220), 1, cv2.LINE_AA)

    def dibujar_errores(
        self,
        frame: np.ndarray,
        filas: Sequence[Tuple[Tuple[int, int, int], str]],
    ) -> None:
        """Panel «¿Qué está mal?» sobre el video, una fila por regla (RF-08).

        ``filas`` es una lista de ``(color_bgr, texto)`` ya ordenada por
        gravedad, de modo que el error más importante aparezca primero.
        """
        if not filas:
            return
        alto, ancho = frame.shape[:2]
        ancho_panel = max(240, min(430, int(ancho * 0.42)))
        x0, x1 = ancho - ancho_panel, ancho - 6
        y0 = 86
        alto_fila = 26
        alto_panel = 30 + alto_fila * len(filas)
        y1 = min(alto - 6, y0 + alto_panel)
        max_caracteres = max(16, int((ancho_panel - 60) / 11))

        # Fondo translúcido, limitado al panel (RNF-01: ~11x menos píxeles
        # que mezclar el fotograma completo).
        self._fondo_translucido(frame, x0, y0, x1, y1, (30, 30, 30), 0.72)

        cv2.putText(frame, "QUE ESTA MAL", (x0 + 12, y0 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
        for indice, (color, texto) in enumerate(filas):
            y = y0 + 46 + indice * alto_fila
            if y + 8 > y1:
                break
            cv2.circle(frame, (x0 + 20, y - 5), 8, color, -1)
            etiqueta = texto if len(texto) <= max_caracteres else texto[: max_caracteres - 1] + "..."
            cv2.putText(frame, etiqueta, (x0 + 36, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    @staticmethod
    def _fondo_translucido(
        frame: np.ndarray,
        x0: int, y0: int, x1: int, y1: int,
        color: Tuple[int, int, int],
        alfa: float = 0.7,
    ) -> None:
        """Rellena un rectángulo translúcido tocando solo esa región.

        Mezclar el fotograma completo con ``addWeighted`` cuesta el doble que
        operar sobre el recorte, y aquí siempre se pinta el mismo rectángulo.
        """
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(frame.shape[1], x1), min(frame.shape[0], y1)
        if x1 <= x0 or y1 <= y0:
            return
        region = frame[y0:y1, x0:x1]
        relleno = np.empty_like(region)
        relleno[:] = color
        frame[y0:y1, x0:x1] = cv2.addWeighted(relleno, alfa, region, 1.0 - alfa, 0)

    def dibujar_cuenta_atras(self, frame: np.ndarray, restantes: int, mensaje: str) -> None:
        """Gran cuenta regresiva centrada antes de empezar a analizar (RNF-04)."""
        alto, ancho = frame.shape[:2]
        centro = (ancho // 2, alto // 2 - 40)
        radio = max(70, int(min(ancho, alto) * 0.14))

        margen = radio + 18
        self._fondo_translucido(
            frame, centro[0] - margen, centro[1] - margen,
            centro[0] + margen, centro[1] + margen, (30, 30, 30), 0.75,
        )

        # A medida que faltan menos segundos el círculo pasa de rojo a verde.
        if restantes > 3:
            color = (60, 200, 255)      # ámbar
        elif restantes > 1:
            color = (0, 170, 255)       # naranja
        else:
            color = (0, 220, 0)         # verde
        cv2.circle(frame, centro, radio, color, 5, cv2.LINE_AA)
        cv2.putText(frame, str(max(0, restantes)), centro, cv2.FONT_HERSHEY_SIMPLEX,
                    radio / 45.0, color, 5, cv2.LINE_AA)

        texto = mensaje or ""
        ancho_texto, _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        posicion = ((ancho - ancho_texto[0]) // 2, centro[1] + radio + 52)
        cv2.putText(frame, texto, posicion, cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (255, 255, 255), 2, cv2.LINE_AA)