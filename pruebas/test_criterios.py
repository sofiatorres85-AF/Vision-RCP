"""Pruebas de los criterios de aceptación sin cámara.

Ejecutar::

    venv\\Scripts\\python -m pruebas.test_criterios

Cubre los criterios verificables sin hardware:
* CP-03 / CA-03 y CP-11 / RNF-02: frecuencia con metrónomo de 100, 110 y 120 cpm.
* CP-04 / CA-04 y CP-12 / RNF-03: profundidad de 5.0, 5.5 y 6.0 cm.
* CP-07 / CA-07: ángulo hombro-codo-muñeca.
* CP-06 / CA-06: retorno torácico incompleto.
* CP-05 / CA-05: posición de manos.
* CP-10 / RNF-01: tiempo de análisis y feedback por fotograma.
* CA-02: índices de landmarks requeridos.
* RNF-04: cuenta regresiva de posicionamiento de 5 s.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rcp.analisis import AnalizadorRCP, Metricas, angulo_abc  # noqa: E402
from rcp.configuracion import (  # noqa: E402
    Configuracion,
    INDICES_REQUERIDOS,
)
from rcp.reglas import MotorReglas  # noqa: E402
from rcp.retroalimentacion import GeneradorFeedback  # noqa: E402
from rcp.sesion import CuentaAtras  # noqa: E402

FPS_SIMULADO = 60.0
DURACION_S = 30.0

_fallos: list = []


def comprobar(nombre: str, condicion: bool, detalle: str = "") -> None:
    estado = "PASS" if condicion else "FALLA"
    print(f"[{estado}] {nombre}{(' -> ' + detalle) if detalle else ''}")
    if not condicion:
        _fallos.append(nombre)


# ----------------------------------------------------------- utilidades ---
def senal_compresiones(t: float, cpm: float, amplitud_cm: float) -> float:
    """Desplazamiento vertical en cm de las muñecas."""
    return amplitud_cm / 2.0 * (1.0 - math.cos(2.0 * math.pi * cpm / 60.0 * t))


def landmarks_sinteticos(compresion_px: float, angulo_brazos: float = 170.0,
                         separacion_munecas_px: float = 30.0,
                         inclinacion_postural_px: float = 0.0):
    """Construye un mapa de landmarks plausible para las pruebas.

    ``compresion_px`` es el hundimiento del tórax durante la compresión. Con
    brazos rígidos las muñecas se desplazan lo mismo que los hombros, que es
    justamente lo que mide el sistema (desplazamiento vertical de muñecas).
    ``inclinacion_postural_px`` simula una deriva postural global.
    """
    ancho = 640
    centro_x = ancho / 2.0
    hombro_y = 150.0 + compresion_px + inclinacion_postural_px
    semiancho_hombros = 90.0
    largo_brazo = 110.0
    rad = math.radians(180.0 - angulo_brazos)  # 0 grados = brazo recto
    dx = largo_brazo * math.cos(math.pi + rad / 2.0)
    dy = largo_brazo * math.sin(math.pi + rad / 2.0)

    hombro_izq = (centro_x - semiancho_hombros, hombro_y)
    hombro_der = (centro_x + semiancho_hombros, hombro_y)
    codo_izq = (hombro_izq[0] + dx * 0.5, hombro_y + dy * 0.5)
    codo_der = (hombro_der[0] + dx * 0.5, hombro_y + dy * 0.5)
    # Brazos rígidos: las muñecas acompañan a los hombros.
    muneca_izq = (centro_x - separacion_munecas_px / 2.0, hombro_y + dy)
    muneca_der = (centro_x + separacion_munecas_px / 2.0, hombro_y + dy)
    return {
        11: hombro_izq,
        12: hombro_der,
        13: codo_izq,
        14: codo_der,
        15: muneca_izq,
        16: muneca_der,
        23: (centro_x - 55.0, 330.0 + inclinacion_postural_px),
        24: (centro_x + 55.0, 330.0 + inclinacion_postural_px),
    }


def ejecutar_sesion_sintetica(cpm_real: float, amplitud_cm: float, angulo: float = 170.0,
                             separacion_munecas_px: float = 30.0, px_por_cm: float = 20.0,
                             colapso_postural_cm: float = 0.0):
    """Simula una sesión completa y devuelve las métricas del analizador.

    ``amplitud_cm`` es la profundidad pico a pico de la compresión, que es la
    magnitud que el sistema debe estimar. ``colapso_postural_cm`` es la
    deriva global de hombros que aparece progresivamente a los 10 s y sirve
    para verificar la detección de retorno torácico incompleto (CA-06).
    """
    config = Configuracion()
    analizador = AnalizadorRCP(config)
    total_frames = int(DURACION_S * FPS_SIMULADO)
    lado_aruco_px = config.tamano_marcador_cm * px_por_cm
    centro_aruco = (320.0, 220.0)
    metricas = Metricas()
    for i in range(total_frames):
        t = i / FPS_SIMULADO
        # La señal del usuario está en centímetros; la cámara la observa en píxeles.
        compresion_px = senal_compresiones(t, cpm_real, amplitud_cm) * px_por_cm
        # El colapso postural aparece de forma progresiva a partir del segundo 10.
        progreso = min(1.0, max(0.0, (t - 10.0) / 5.0))
        inclinacion_px = colapso_postural_cm * px_por_cm * progreso
        landmarks = landmarks_sinteticos(
            compresion_px, angulo, separacion_munecas_px, inclinacion_px
        )
        metricas = analizador.actualizar(t, landmarks, centro_aruco, lado_aruco_px)
    return metricas


# --------------------------------------------------------------- pruebas ---
def prueba_ca03_cpm() -> None:
    """CA-03: clasificación de frecuencia baja / correcta / alta."""
    config = Configuracion()
    reglas = MotorReglas(config)
    for cpm, esperado in ((80.0, "Aumente"), (110.0, "correcto"), (140.0, "Reduzca")):
        m = Metricas(cpm=cpm, profundidad_cm=5.5, pose_detectada=True)
        resultado = next(r for r in reglas.evaluar(m) if r.id == "RN-01")
        comprobar(
            f"CA-03 clasificacion {cpm:.0f} cpm",
            esperado in resultado.mensaje,
            resultado.mensaje,
        )


def prueba_cp11_precision_frecuencia() -> None:
    """CP-11 / RNF-02: error absoluto <= 6 cpm con metrónomo conocido."""
    config = Configuracion()
    for cpm_real in (100.0, 110.0, 120.0):
        metricas = ejecutar_sesion_sintetica(cpm_real, 5.5)
        error = abs(metricas.cpm - cpm_real)
        comprobar(
            f"CP-11 frecuencia {cpm_real:.0f} cpm (medido {metricas.cpm:.1f})",
            error <= config.error_maximo_cpm,
            f"error {error:.2f} cpm (limite {config.error_maximo_cpm:.0f})",
        )


def prueba_cp12_precision_profundidad() -> None:
    """CP-12 / RNF-03: error absoluto <= 0.5 cm con profundidad conocida."""
    config = Configuracion()
    for profundidad_real in (5.0, 5.5, 6.0):
        metricas = ejecutar_sesion_sintetica(110.0, profundidad_real)
        error = abs(metricas.profundidad_cm - profundidad_real)
        comprobar(
            f"CP-12 profundidad {profundidad_real:.1f} cm (medido {metricas.profundidad_cm:.2f})",
            error <= config.error_maximo_profundidad_cm,
            f"error {error:.2f} cm",
        )


def prueba_ca04_clasificacion_profundidad() -> None:
    """CA-04: insuficiente / correcta / excesiva."""
    reglas = MotorReglas(Configuracion())
    for profundidad, esperado in ((3.5, "más hondo"), (5.5, "correcta"), (8.0, "menos hondo")):
        m = Metricas(cpm=110.0, profundidad_cm=profundidad, pose_detectada=True)
        resultado = next(r for r in reglas.evaluar(m) if r.id == "RN-02")
        comprobar(
            f"CA-04 clasificacion {profundidad:.1f} cm",
            esperado in resultado.mensaje,
            resultado.mensaje,
        )


def prueba_ca07_angulo_brazos() -> None:
    """CA-07: ángulo hombro-codo-muñeca con umbral de 150 grados."""
    angulo = angulo_abc((0.0, 0.0), (10.0, 0.0), (20.0, 0.0))
    comprobar("CA-07 angulo recto = 180", abs(angulo - 180.0) < 1e-6, f"{angulo:.2f}")
    angulo_90 = angulo_abc((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))
    comprobar("CA-07 angulo recto de brazo = 90", abs(angulo_90 - 90.0) < 1e-6, f"{angulo_90:.2f}")
    reglas = MotorReglas(Configuracion())
    flexionado = Metricas(cpm=110.0, profundidad_cm=5.5, pose_detectada=True,
                          angulo_brazo_grados=120.0)
    resultado = next(r for r in reglas.evaluar(flexionado) if r.id == "RN-05")
    comprobar("CA-07 detecta brazos flexionados", "Estire" in resultado.mensaje, resultado.mensaje)
    extendidos = Metricas(cpm=110.0, profundidad_cm=5.5, pose_detectada=True,
                          angulo_brazo_grados=168.0)
    resultado_ok = next(r for r in reglas.evaluar(extendidos) if r.id == "RN-05")
    comprobar("CA-07 acepta brazos extendidos", resultado_ok.cumple, resultado_ok.mensaje)


def prueba_ca06_retorno_toracico() -> None:
    """CA-06: retorno completo vs retorno insuficiente."""
    reglas = MotorReglas(Configuracion())
    completo = Metricas(cpm=110.0, profundidad_cm=5.5, pose_detectada=True,
                        desvio_hombros_cm=0.4, retorno_ok=True)
    resultado = next(r for r in reglas.evaluar(completo) if r.id == "RN-04")
    comprobar("CA-06 retorno completo aceptado", resultado.cumple, resultado.mensaje)

    simulado = ejecutar_sesion_sintetica(110.0, 5.5, colapso_postural_cm=4.0)
    resultado_inc = next(r for r in reglas.evaluar(simulado) if r.id == "RN-04")
    comprobar(
        "CA-06 retorno insuficiente detectado",
        not resultado_inc.cumple,
        resultado_inc.mensaje,
    )


def prueba_ca05_posicion_manos() -> None:
    """CA-05: manos juntas sobre el esternón vs manos separadas."""
    metricas_ok = ejecutar_sesion_sintetica(110.0, 5.5, separacion_munecas_px=30.0)
    comprobar(
        "CA-05 manos juntas y centradas",
        metricas_ok.esternon_ok,
        f"separacion {metricas_ok.distancia_munecas_cm} cm",
    )
    metricas_mal = ejecutar_sesion_sintetica(110.0, 5.5, separacion_munecas_px=400.0)
    comprobar(
        "CA-05 manos separadas detectadas",
        not metricas_mal.esternon_ok,
        f"separacion {metricas_mal.distancia_munecas_cm} cm",
    )


def prueba_ca08_feedback() -> None:
    """CA-08: el feedback muestra mensajes y color por desviación."""
    reglas = MotorReglas(Configuracion())
    generador = GeneradorFeedback()
    bien = Metricas(cpm=110.0, profundidad_cm=5.5, pose_detectada=True,
                    angulo_brazo_grados=168.0, distancia_munecas_cm=8.0, esternon_ok=True,
                    retorno_ok=True, desvio_hombros_cm=0.2)
    mensaje, color, _ = generador.generar(reglas.evaluar(bien))
    comprobar("CA-08 feedback correcto en verde", color == "green", f"{mensaje} ({color})")

    mal = Metricas(cpm=60.0, profundidad_cm=2.0, pose_detectada=True)
    mensaje, color, completo = generador.generar(reglas.evaluar(mal))
    comprobar(
        "CA-08 feedback con dos correcciones",
        "frecuencia" in completo.lower() and "hondo" in completo.lower(),
        completo,
    )
    comprobar("CA-08 color de desviacion", color in ("red", "orange"), color)


def prueba_cp10_tiempo_proceso() -> None:
    """CP-10 / RNF-01: análisis + feedback por debajo de 100 ms."""
    config = Configuracion()
    analizador = AnalizadorRCP(config)
    motor = MotorReglas(config)
    generador = GeneradorFeedback()
    lado_aruco = config.tamano_marcador_cm * 20.0
    peor = 0.0
    for i in range(600):
        t = i / 60.0
        landmarks = landmarks_sinteticos(senal_compresiones(t, 110.0, 5.5) * 20.0)
        inicio = time.perf_counter()
        metricas = analizador.actualizar(t, landmarks, (320.0, 220.0), lado_aruco)
        reglas = motor.evaluar(metricas)
        generador.generar(reglas)
        peor = max(peor, (time.perf_counter() - inicio) * 1000.0)
    comprobar(
        "CP-10 tiempo de proceso < 100 ms",
        peor < config.tiempo_maximo_proceso_ms,
        f"peor fotograma {peor:.2f} ms",
    )


def prueba_ca02_indices() -> None:
    """CA-02: los ocho landmarks requeridos están definidos."""
    comprobar(
        "CA-02 indices 11,12,13,14,15,16,23,24",
        set(INDICES_REQUERIDOS) == {11, 12, 13, 14, 15, 16, 23, 24},
        str(INDICES_REQUERIDOS),
    )
    metricas = ejecutar_sesion_sintetica(110.0, 5.5)
    comprobar("CA-02 postura detectada", metricas.pose_detectada)


def prueba_sesion_registro_errores() -> None:
    """CA-05/06/07: los errores se registran con marca de tiempo."""
    from rcp.sesion import Sesion

    sesion = Sesion(Configuracion())
    sesion.iniciar(time.time())
    motor = MotorReglas(Configuracion())
    metricas = Metricas(cpm=50.0, profundidad_cm=2.0, pose_detectada=True,
                        angulo_brazo_grados=100.0, retorno_ok=False,
                        desvio_hombros_cm=5.0)
    errores = sesion.registrar_reglas(motor.evaluar(metricas))
    comprobar("Registro de errores con marca de tiempo", len(errores) >= 3,
              f"{len(errores)} errores: {[e.regla_id for e in errores]}")
    comprobar("Marca de tiempo formato HH:MM:SS.mmm",
              all(len(e.marca_tiempo) == 12 for e in errores),
              errores[0].marca_tiempo if errores else "-")
    # El enfriamiento evita duplicados inmediatos.
    repetidos = sesion.registrar_reglas(motor.evaluar(metricas))
    comprobar("Sin errores duplicados por enfriamiento", len(repetidos) == 0,
              f"{len(repetidos)} nuevos")
    resumen = sesion.finalizar(time.time() + 30.0)
    comprobar("Resumen de sesion con duracion", resumen.duracion_s >= 29.0, f"{resumen.duracion_s} s")
    comprobar("Resumen con errores detectados", len(resumen.errores) >= 3,
              f"{len(resumen.errores)} errores")


def prueba_cuenta_atras() -> None:
    """RNF-04 / CA-09: cuenta regresiva de posicionamiento de 5 segundos."""
    cuenta = CuentaAtras(5)
    comprobar("Cuenta atras inicia detenida", cuenta.terminada)
    comprobar("Cuenta atras arranca en 5 s", cuenta.iniciar() == 5, str(cuenta.restantes))
    comprobar("Cuenta atras en curso", cuenta.en_ejecucion and not cuenta.terminada)

    recorrido = [cuenta.avanzar() for _ in range(5)]
    comprobar("Cuenta atras 5->0", recorrido == [4, 3, 2, 1, 0], str(recorrido))
    comprobar("Cuenta atras terminada en 0", cuenta.terminada and cuenta.restantes == 0)
    comprobar("Avanzar tras terminar devuelve 0", cuenta.avanzar() == 0)

    comprobar("Reinicio de la cuenta atras", cuenta.iniciar() == 5 and cuenta.en_ejecucion)
    cuenta.cancelar()
    comprobar("Cancelacion inmediata", cuenta.terminada and cuenta.restantes == 0)

    # Sin margen configurable, la sesión debe arrancar directo (config = 0).
    directa = CuentaAtras(0)
    comprobar("Cuenta atras desactivada arranca en 0", directa.iniciar() == 0)
    comprobar("Cuenta atras desactivada termina ya", directa.terminada)

    comprobar("Duracion por defecto de 5 s",
              CuentaAtras().segundos_totales == 5, str(CuentaAtras().segundos_totales))


def prueba_configuracion_cuenta_atras() -> None:
    """La cuenta regresiva vive en la configuración, no hardcodeada en la UI."""
    config = Configuracion()
    comprobar("cuenta_atras_s = 5", config.cuenta_atras_s == 5, str(config.cuenta_atras_s))
    comprobar("mensaje de cuenta atras definido", bool(config.mensaje_cuenta_atras))
    comprobar("Cuenta atras enlazada con la configuracion",
              CuentaAtras(config.cuenta_atras_s).segundos_totales == 5)


def main() -> int:
    pruebas = (
        prueba_ca02_indices,
        prueba_ca03_cpm,
        prueba_ca04_clasificacion_profundidad,
        prueba_cp11_precision_frecuencia,
        prueba_cp12_precision_profundidad,
        prueba_ca05_posicion_manos,
        prueba_ca06_retorno_toracico,
        prueba_ca07_angulo_brazos,
        prueba_ca08_feedback,
        prueba_cp10_tiempo_proceso,
        prueba_sesion_registro_errores,
        prueba_cuenta_atras,
        prueba_configuracion_cuenta_atras,
    )
    print("=== Pruebas de criterios de aceptacion ===")
    for prueba in pruebas:
        print(f"\n-- {prueba.__name__}")
        prueba()
    print("\n=== Resultado ===")
    if _fallos:
        print(f"FALLARON {len(_fallos)} pruebas:")
        for nombre in _fallos:
            print(f"  - {nombre}")
        return 1
    print("Todas las pruebas pasaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())