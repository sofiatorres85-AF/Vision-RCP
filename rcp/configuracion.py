"""Parámetros de configuración y umbrales del sistema.

Todos los valores numéricos provienen de los criterios de aceptación
CA-01, CA-03, CA-04, CA-05, CA-06, CA-07 y de las reglas de negocio
RN-01 a RN-06, de modo que changing un umbral sea una decisión aislada.
"""

from dataclasses import dataclass, field

# Índices de landmarks de MediaPipe Pose requeridos por RF-02.
INDICE_HOMBRO_IZQUIERDO = 11
INDICE_HOMBRO_DERECHO = 12
INDICE_CODO_IZQUIERDO = 13
INDICE_CODO_DERECHO = 14
INDICE_MUNECA_IZQUIERDA = 15
INDICE_MUNECA_DERECHA = 16
INDICE_CADERA_IZQUIERDA = 23
INDICE_CADERA_DERECHA = 24

#: Landmarks que el sistema debe detectar y superponer (RF-02 / CA-02).
INDICES_REQUERIDOS = (
    INDICE_HOMBRO_IZQUIERDO,
    INDICE_HOMBRO_DERECHO,
    INDICE_CODO_IZQUIERDO,
    INDICE_CODO_DERECHO,
    INDICE_MUNECA_IZQUIERDA,
    INDICE_MUNECA_DERECHA,
    INDICE_CADERA_IZQUIERDA,
    INDICE_CADERA_DERECHA,
)

#: Conexiones dibujadas entre los landmarks requeridos.
CONEXIONES_POSE = (
    (INDICE_HOMBRO_IZQUIERDO, INDICE_HOMBRO_DERECHO),
    (INDICE_HOMBRO_IZQUIERDO, INDICE_CODO_IZQUIERDO),
    (INDICE_CODO_IZQUIERDO, INDICE_MUNECA_IZQUIERDA),
    (INDICE_HOMBRO_DERECHO, INDICE_CODO_DERECHO),
    (INDICE_CODO_DERECHO, INDICE_MUNECA_DERECHA),
    (INDICE_HOMBRO_IZQUIERDO, INDICE_CADERA_IZQUIERDA),
    (INDICE_HOMBRO_DERECHO, INDICE_CADERA_DERECHA),
    (INDICE_CADERA_IZQUIERDA, INDICE_CADERA_DERECHA),
)


@dataclass(frozen=True)
class Configuracion:
    """Parámetros de operación del sistema."""

    # --- RF-01 / CA-01: captura de video en tiempo real ---
    indice_camara: int = 0
    tiempo_maximo_activacion_camara_s: float = 3.0
    fps_minimo: int = 15

    # --- Presentación de la ventana de video ---
    ancho_ventana_video: int = 880
    alto_ventana_video: int = 660

    # --- RF-02 / CA-02: detección de landmarks ---
    maximo_poses: int = 1
    min_confianza_deteccion: float = 0.5
    min_confianza_seguimiento: float = 0.5

    # --- RF-04 / RN-02: referencia de escala con ArUco ---
    tamano_marcador_cm: float = 5.0
    id_marcador_objetivo: int = 0
    escalado_aruco: bool = True

    # --- RF-03 / RN-01: frecuencia ---
    cpm_minimo: float = 100.0
    cpm_maximo: float = 120.0
    amplitud_minima_compresion_cm: float = 1.5
    intervalo_minimo_compresion_s: float = 0.30
    muestras_para_frecuencia: int = 5

    # --- RF-04 / RN-02: profundidad ---
    profundidad_minima_cm: float = 5.0
    profundidad_maxima_cm: float = 6.0
    muestras_para_profundidad: int = 5
    #: Tamaño de la ventana de suavizado de la señal vertical de muñecas.
    muestras_suavizado: int = 3

    # --- RF-05 / RN-03: posición de las manos ---
    distancia_maxima_munecas_cm: float = 12.0
    tolerancia_desalineacion_esternon: float = 0.35

    # --- RF-06 / RN-04: retorno torácico ---
    tolerancia_retorno_cm: float = 2.0
    muestras_linea_base_hombros: int = 10

    # --- RF-07 / RN-05: rectitud de brazos ---
    angulo_brazo_minimo: float = 150.0

    # --- RNF-01 / CP-10: rendimiento ---
    tiempo_maximo_proceso_ms: float = 100.0

    # --- RNF-02 / CP-11: precisión en frecuencia (±5 %, <= 6 cpm) ---
    error_maximo_cpm: float = 6.0

    # --- RNF-03 / CP-12: precisión en profundidad ---
    error_maximo_profundidad_cm: float = 0.5

    # --- Registro de errores con marca de tiempo (CA-05, CA-06, CA-07) ---
    enfriamiento_error_s: float = 1.0

    # --- Cuenta regresiva de posicionamiento (RNF-04 usabilidad) ---
    #: Segundos que el usuario tiene para ubicarse antes de analizar.
    #: Durante este periodo se muestra el video y los landmarks pero no se
    #: mide nada ni corre la duración de la sesión.
    cuenta_atras_s: int = 5
    #: Texto mostrado durante la cuenta regresiva.
    mensaje_cuenta_atras: str = "Pongase en posicion frente a la camara"

    # --- Longitud del historial para la mini-gráfica de la señal ---
    muestras_historial: int = 90

    #: Índices que el analizador espera recibir en cada fotograma.
    indices_requeridos: tuple = field(default=INDICES_REQUERIDOS)