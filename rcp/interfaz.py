"""Interfaz gráfica Tkinter (RF-09 / CA-09, RNF-04 usabilidad).

Muestra el video con la superposición de landmarks, un panel «¿Qué está mal?»
con una fila por regla y un banner de corrección. Antes de medir, ofrece una
cuenta regresiva de posicionamiento (RNF-04); tras finalizar la sesión se
presenta el resumen.
"""

from __future__ import annotations

import csv
import time
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
from PIL import Image, ImageTk

from .analisis import AnalizadorRCP, Metricas
from .captura import CapturaVideo
from .configuracion import Configuracion
from .procesamiento import Dibujante, ProcesadorArUco, ProcesadorPose
from .reglas import (
    ESTADO_ALERTA,
    ESTADO_ERROR,
    ESTADO_ESPERA,
    ESTADO_OK,
    MotorReglas,
    ResultadoRegla,
)
from .retroalimentacion import FONDO_ESPERA, GeneradorFeedback
from .sesion import CuentaAtras, Sesion

#: Fases de la aplicación: nada, posicionándose, midiendo.
FASE_INACTIVA = "inactiva"
FASE_POSICIONAMIENTO = "posicionamiento"
FASE_ACTIVA = "activa"

#: Fondo del banner de corrección por color de Tkinter (contraste con texto blanco).
FONDO_BANNER = {
    "green": "#14532d",
    "red": "#7f1d1d",
    "orange": "#7c2d12",
    "gray": "#3f3f46",
}

#: Fondo de la fila del panel «¿Qué está mal?» por estado de regla.
#: El orden es el de la lista de verificación que lee el alumno.
FILAS_ESTADO: Sequence[Tuple[str, str]] = (
    ("RF-02", "Postura visible"),
    ("RN-01", "Frecuencia"),
    ("RN-02", "Profundidad"),
    ("RN-03", "Posicion de manos"),
    ("RN-04", "Retorno toracico"),
    ("RN-05", "Rectitud de brazos"),
)

#: Gravedad para ordenar las filas del video (menor = más grave, se dibuja antes).
GRAVEDAD = {ESTADO_ERROR: 0, ESTADO_ALERTA: 1, ESTADO_ESPERA: 2, ESTADO_OK: 3}


class AplicacionRCP:
    """Interfaz del sistema de análisis de RCP."""

    def __init__(self, root: tk.Tk, config: Optional[Configuracion] = None) -> None:
        self.root = root
        self.config = config or Configuracion()

        # Módulos del sistema (ver Figura 10).
        self.captura = CapturaVideo(self.config)
        self.procesador_pose = ProcesadorPose(self.config)
        self.procesador_aruco = ProcesadorArUco(self.config)
        self.analizador = AnalizadorRCP(self.config)
        self.motor_reglas = MotorReglas(self.config)
        self.generador = GeneradorFeedback()
        self.sesion = Sesion(self.config)
        self.dibujante = Dibujante()

        # Estado de la sesión.
        self.en_curso = False
        self._fase = FASE_INACTIVA
        self.cuenta = CuentaAtras(self.config.cuenta_atras_s)
        self.marca_tiempo_ms = 0
        self.fps = 0.0
        self.ultimo_fotograma = None
        self.tiempo_proceso_ms = 0.0
        self._instante_fotograma_anterior: Optional[float] = None
        self._archivo_csv = None
        self._escritor_csv = None
        #: id de regla -> (cuadro de color, etiqueta) del panel «¿Qué está mal?».
        self._filas_estado: Dict[str, Tuple[tk.Widget, tk.Label]] = {}
        #: Último (fondo, texto) aplicado a cada fila, para no redibujar sin cambios.
        self._estado_filas: Dict[str, Tuple[str, str]] = {}

        self._construir_interfaz()
        self._iniciar_modelos()

    # ------------------------------------------------------------- UI ---
    def _construir_interfaz(self) -> None:
        self.root.title("Sistema de analisis de tecnica RCP - OpenCV + MediaPipe + ArUco")
        self.root.geometry("1280x760")

        izquierda = ttk.Frame(self.root, padding=8)
        izquierda.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.etiqueta_video = ttk.Label(izquierda, text="Sesion no iniciada")
        self.etiqueta_video.pack(fill=tk.BOTH, expand=True)

        derecha = ttk.Frame(self.root, padding=8, width=360)
        derecha.pack(side=tk.RIGHT, fill=tk.Y)
        derecha.pack_propagate(False)

        ttk.Label(derecha, text="Indicadores de calidad",
                  font=("Segoe UI", 12, "bold")).pack(pady=(4, 2))

        self.etiqueta_frecuencia = ttk.Label(derecha, text="Frecuencia: 0 cpm", font=("Segoe UI", 12))
        self.etiqueta_frecuencia.pack(anchor="w")
        self.etiqueta_profundidad = ttk.Label(derecha, text="Profundidad: 0.0 cm", font=("Segoe UI", 12))
        self.etiqueta_profundidad.pack(anchor="w")
        self.etiqueta_conteo = ttk.Label(derecha, text="Compresiones: 0", font=("Segoe UI", 11))
        self.etiqueta_conteo.pack(anchor="w")
        # Los dos indicadores secundarios comparten línea para no consumir alto.
        marco_angulos = ttk.Frame(derecha)
        marco_angulos.pack(anchor="w")
        self.etiqueta_brazos = ttk.Label(marco_angulos, text="Angulo: -", font=("Segoe UI", 10))
        self.etiqueta_brazos.pack(side=tk.LEFT)
        self.etiqueta_munecas = ttk.Label(marco_angulos, text=" | Munecas: -", font=("Segoe UI", 10))
        self.etiqueta_munecas.pack(side=tk.LEFT)
        self.etiqueta_sistema = ttk.Label(derecha, text="FPS: 0 | Proceso: 0 ms", font=("Segoe UI", 9))
        self.etiqueta_sistema.pack(anchor="w", pady=2)

        # RF-08: banner de corrección grande y de alto contraste.
        self.etiqueta_feedback = tk.Label(
            derecha, text="Presione Iniciar sesion",
            font=("Segoe UI", 13, "bold"), foreground="white", background=FONDO_BANNER["gray"],
            wraplength=318, justify="center", anchor="center", padx=8, pady=6,
        )
        self.etiqueta_feedback.pack(fill="x", pady=(4, 4))

        # RF-08 / RNF-04: checklist de una fila por regla, con fondo por estado.
        ttk.Label(derecha, text="¿Qué está mal?", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        marco_filas = ttk.Frame(derecha)
        marco_filas.pack(fill="x", pady=(2, 4))
        for id_regla, nombre in FILAS_ESTADO:
            fila = ttk.Frame(marco_filas)
            fila.pack(fill="x", pady=1)
            cuadro = tk.Frame(fila, width=12, height=12, bg=FONDO_ESPERA)
            cuadro.pack(side=tk.LEFT, padx=(2, 6), pady=4)
            etiqueta = tk.Label(
                fila, text=f"{nombre}: —", font=("Segoe UI", 10),
                foreground="#111111", background=FONDO_ESPERA,
                wraplength=302, justify="left", anchor="w", padx=5, pady=1,
            )
            etiqueta.pack(side=tk.LEFT, fill="both", expand=True)
            self._filas_estado[id_regla] = (cuadro, etiqueta)

        ttk.Separator(derecha).pack(fill="x", pady=(4, 4))

        # Botones de sesión: "Finalizar sesión" siempre visible (CA-09).
        ttk.Button(derecha, text="1. Iniciar sesion", command=self.iniciar_sesion).pack(fill="x", pady=2)
        self.boton_finalizar = ttk.Button(
            derecha, text="2. Finalizar sesion", command=self.finalizar_sesion, state="disabled"
        )
        self.boton_finalizar.pack(fill="x", pady=2)
        ttk.Button(derecha, text="Reiniciar contador", command=self.reiniciar_contador).pack(fill="x", pady=2)
        self.boton_csv = ttk.Button(derecha, text="Grabar CSV", command=self.alternar_csv)
        self.boton_csv.pack(fill="x", pady=2)
        ttk.Button(derecha, text="Generar marcador ArUco", command=self.generar_marcador).pack(fill="x", pady=2)

        ttk.Label(derecha, text="Registro de eventos:").pack(anchor="w", pady=(6, 2))
        # Alto mínimo corto: el marco absorbe el espacio que sobre y, en el peor
        # caso de textos largos, evita que el panel se desborde de la ventana.
        self.registro = scrolledtext.ScrolledText(derecha, width=42, height=4, state="disabled")
        self.registro.pack(fill="both", expand=True)

        self.etiqueta_estado = ttk.Label(derecha, text="Estado: detenida")
        self.etiqueta_estado.pack(pady=2)

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

    def _iniciar_modelos(self) -> None:
        if self.procesador_pose.iniciar():
            self._anotar("Modelo de pose cargado.")
        else:
            self._anotar("ERROR: no se pudo cargar MediaPipe Pose. Revisa models/ e internet.")

    # --------------------------------------------------------sesión ---
    def iniciar_sesion(self) -> None:
        if self.en_curso:
            return
        resultado = self.captura.activar()
        if not resultado.ok:
            # CA-01: sin cámara no se muestra video y la sesión no inicia.
            self._anotar(f"ERROR: {resultado.mensaje}")
            self.etiqueta_estado.config(text="Estado: error de camara", foreground="red")
            self._poner_banner(resultado.mensaje, "red")
            messagebox.showerror("Camara no disponible", resultado.mensaje)
            return

        self._anotar(resultado.mensaje)
        self.en_curso = True
        # No se reinicia marca_tiempo_ms: detect_for_video exige marcas de
        # tiempo monótonamente crecientes. Si volviera a 0 en la segunda
        # sesión, MediaPipe rechazaría todos los fotogramas ("Input timestamp
        # must be monotonically increasing") y no habría landmarks.
        self._instante_fotograma_anterior = None
        self.fps = 0.0
        self.analizador.reiniciar()
        self.boton_finalizar.config(state="normal")
        self.etiqueta_video.config(text="Iniciando...")

        # RNF-04: margen para ubicarse antes de empezar a medir.
        restantes = self.cuenta.iniciar()
        if restantes > 0:
            self._fase = FASE_POSICIONAMIENTO
            self.etiqueta_estado.config(
                text=f"Estado: pongase en posicion ({restantes} s)", foreground="orange"
            )
            self._anotar(f"Cuenta atras de {restantes} s para ubicarse frente a la camara.")
            self.root.after(1000, self._tick_cuenta_atras)
        else:
            self._iniciar_analisis()
        self._actualizar()

    def _tick_cuenta_atras(self) -> None:
        """Descuenta un segundo; al llegar a 0 arranca la sesión."""
        if not self.en_curso or self._fase != FASE_POSICIONAMIENTO:
            return
        restantes = self.cuenta.avanzar()
        if restantes > 0:
            self.etiqueta_estado.config(
                text=f"Estado: pongase en posicion ({restantes} s)", foreground="orange"
            )
            self.root.after(1000, self._tick_cuenta_atras)
        else:
            self._iniciar_analisis()

    def _iniciar_analisis(self) -> None:
        """Pasa de la fase de posicionamiento a la medición real (RF-08/RF-09)."""
        self._fase = FASE_ACTIVA
        self.cuenta.cancelar()
        # El inicio aquí hace que la duración del resumen excluya la espera.
        self.sesion.iniciar()
        self.analizador.reiniciar()
        self.etiqueta_estado.config(text="Estado: sesion en curso", foreground="green")
        self._anotar("Cuenta atras finalizada; sesion iniciada.")

    def finalizar_sesion(self) -> None:
        """Detiene captura y análisis, y muestra el resumen (CA-09)."""
        if not self.en_curso:
            return
        en_analisis = self._fase == FASE_ACTIVA
        self.en_curso = False
        self._fase = FASE_INACTIVA
        self.cuenta.cancelar()
        self.captura.liberar()
        resumen = self.sesion.finalizar() if en_analisis else None
        self.alternar_csv(finalizar=True)
        self.boton_finalizar.config(state="disabled")
        self.ultimo_fotograma = None
        if resumen is None:
            # Cancelada durante la cuenta regresiva: la sesión no llegó a medir.
            self.etiqueta_estado.config(text="Estado: cuenta atras cancelada", foreground="blue")
            self._poner_banner("Cuenta atras cancelada", "gray")
            self.etiqueta_video.config(image="", text="Cuenta atras cancelada.")
            self._anotar("Cuenta atras cancelada; la sesion no llego a iniciar.")
            return
        self.etiqueta_estado.config(text="Estado: sesion finalizada", foreground="blue")
        self._poner_banner("Sesion finalizada", "gray")
        self.etiqueta_video.config(image="", text="Sesion finalizada. Resumen:")
        self._anotar("Sesion finalizada.")
        messagebox.showinfo("Resumen de la sesion", resumen.como_texto())

    def reiniciar_contador(self) -> None:
        self.analizador.reiniciar()
        self._anotar("Contador y lineas base reiniciados.")

    # ---------------------------------------------------------- CSV ---
    def alternar_csv(self, finalizar: bool = False) -> None:
        if finalizar:
            if self._archivo_csv is not None:
                self._archivo_csv.close()
                self._archivo_csv = None
                self._escritor_csv = None
                self.boton_csv.config(text="Grabar CSV")
            return
        if self._archivo_csv is None:
            ruta = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"rcp_{datetime.now():%Y%m%d_%H%M%S}.csv",
                filetypes=[("CSV", "*.csv")],
            )
            if not ruta:
                return
            self._archivo_csv = open(ruta, "w", newline="", encoding="utf-8")
            self._escritor_csv = csv.writer(self._archivo_csv)
            self._escritor_csv.writerow([
                "timestamp", "t_s", "fps", "tiempo_proceso_ms", "cpm", "profundidad_cm",
                "compresiones", "dist_munecas_cm", "dist_esternon_cm", "ang_brazo_grados",
                "esternon_ok", "retorno_ok", "px_por_cm",
            ])
            self.boton_csv.config(text="Detener CSV")
            self._anotar(f"Grabando CSV en {ruta}")
        else:
            self._archivo_csv.close()
            self._archivo_csv = None
            self._escritor_csv = None
            self.boton_csv.config(text="Grabar CSV")
            self._anotar("CSV cerrado.")

    def generar_marcador(self) -> None:
        ruta = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"aruco_ID{self.config.id_marcador_objetivo}.png",
            filetypes=[("PNG", "*.png")],
        )
        if not ruta:
            return
        try:
            imagen = cv2.aruco.generateImageMarker(
                self.procesador_aruco.diccionario, self.config.id_marcador_objetivo, 600
            )
        except AttributeError:  # pragma: no cover - OpenCV < 4.7
            imagen = cv2.aruco.drawMarker(
                self.procesador_aruco.diccionario, self.config.id_marcador_objetivo, 600, 1
            )
        cv2.imwrite(ruta, imagen)
        self._anotar(
            f"Marcador ID {self.config.id_marcador_objetivo} guardado en {ruta}. "
            f"Imprima a {self.config.tamano_marcador_cm:.1f} cm sin escalar."
        )

    # ------------------------------------------------------- bucle ---
    def _actualizar(self) -> None:
        if not self.en_curso:
            return
        inicio_proceso = time.perf_counter()

        ok, frame = self.captura.leer()
        if not ok:
            self._anotar("ERROR: no se pudo capturar el fotograma.")
            self.finalizar_sesion()
            return

        frame = cv2.flip(frame, 1)  # vista espejada (cómodo para el usuario)
        self.marca_tiempo_ms += 33
        instante = time.time()

        # Procesamiento: ArUco (escala) y Pose (landmarks).
        resultado_aruco = self.procesador_aruco.detectar(frame)
        landmarks = self.procesador_pose.procesar(frame, self.marca_tiempo_ms)

        # Durante la cuenta regresiva solo se comprueba que la postura sea
        # visible: no se mide nada y la duración de la sesión no avanza.
        posicionandose = self._fase == FASE_POSICIONAMIENTO
        if posicionandose:
            metricas = Metricas(pose_detectada=bool(landmarks))
        else:
            metricas = self.analizador.actualizar(
                instante=instante,
                landmarks_px=landmarks,
                centro_aruco_px=resultado_aruco.centro_px,
                lado_aruco_px=resultado_aruco.lado_px,
            )

        # Reglas y retroalimentación (RF-08).
        reglas = self.motor_reglas.evaluar(metricas)
        if posicionandose:
            mensaje, color, mensaje_completo = self._mensaje_posicionamiento(metricas)
        else:
            mensaje, color, mensaje_completo = self.generador.generar(reglas)

        # Registro de errores con marca de tiempo (CA-05, CA-06, CA-07).
        for error in self.sesion.registrar_reglas(reglas):
            self._anotar(str(error), color_error=True)

        # Superposición sobre el video (RF-09).
        self.dibujante.dibujar_landmarks(frame, landmarks)
        self.dibujante.dibujar_indicadores(
            frame, metricas, mensaje_completo, self.generador.color_bgr_por_estado(reglas[0].estado)
        )
        if posicionandose:
            self.dibujante.dibujar_cuenta_atras(
                frame, self.cuenta.restantes, self.config.mensaje_cuenta_atras
            )
        else:
            self.dibujante.dibujar_senal(frame, self.analizador.senal_historial())
            self.dibujante.dibujar_errores(frame, self._filas_video(reglas))

        # Rendimiento (RNF-01 / CP-10).
        self.tiempo_proceso_ms = (time.perf_counter() - inicio_proceso) * 1000.0
        if self._instante_fotograma_anterior is not None:
            delta = instante - self._instante_fotograma_anterior
            if delta > 0:
               self.fps = self.fps * 0.9 + (1.0 / delta) * 0.1 if self.fps else 1.0 / delta
        self._instante_fotograma_anterior = instante

        self.sesion.registrar_fotograma(
            compresiones=metricas.compresiones,
            cpm=metricas.cpm,
            profundidad_cm=metricas.profundidad_cm,
            fps=self.fps,
            tiempo_proceso_ms=self.tiempo_proceso_ms,
        )

        if self._escritor_csv is not None and not posicionandose:
            self._escritor_csv.writerow([
                datetime.now().isoformat(timespec="milliseconds"),
                f"{self.sesion.duracion_s():.2f}",
                f"{self.fps:.1f}", f"{self.tiempo_proceso_ms:.1f}",
                f"{metricas.cpm:.1f}", f"{metricas.profundidad_cm:.2f}", metricas.compresiones,
                metricas.distancia_munecas_cm, metricas.distancia_esternon_cm,
                metricas.angulo_brazo_grados, int(metricas.esternon_ok), int(metricas.retorno_ok),
                metricas.px_por_cm,
            ])

        self._refrescar_paneles(metricas, mensaje, color, reglas)
        self._mostrar_video(frame)
        self.root.after(1, self._actualizar)

    def _mensaje_posicionamiento(self, metricas: Metricas) -> Tuple[str, str, str]:
        """Texto mostrado durante la cuenta regresiva (RNF-04).

        El color avisa al alumno si la cámara ya ve su postura o si aún no.
        """
        restantes = max(0, self.cuenta.restantes)
        if metricas.pose_detectada:
            texto = f"Postura visible. Comienza en {restantes} s"
            color = "green"
        else:
            texto = f"Coloquese frente a la camara. Comienza en {restantes} s"
            color = "orange"
        return texto, color, texto

    @staticmethod
    def _filas_video(reglas: Sequence[ResultadoRegla]) -> List[Tuple[Tuple[int, int, int], str]]:
        """Filas del panel del video, de la regla más grave a la menos grave."""
        orden = sorted(reglas, key=lambda r: GRAVEDAD.get(r.estado, 9))
        return [
            (GeneradorFeedback.color_bgr_por_estado(regla.estado), f"{regla.nombre}: {regla.mensaje}")
            for regla in orden
        ]

    # ---------------------------------------------------- presentation ---
    def _refrescar_paneles(self, metricas, mensaje: str, color: str,
                           reglas: Sequence[ResultadoRegla]) -> None:
        self.etiqueta_frecuencia.config(text=f"Frecuencia: {metricas.cpm:.0f} cpm")
        self.etiqueta_profundidad.config(text=f"Profundidad: {metricas.profundidad_cm:.1f} cm")
        self.etiqueta_conteo.config(text=f"Compresiones: {metricas.compresiones}")
        self.etiqueta_brazos.config(
            text=f"Angulo: {metricas.angulo_brazo_grados:.0f} deg"
            if metricas.angulo_brazo_grados is not None else "Angulo: -"
        )
        self.etiqueta_munecas.config(
            text=f" | Munecas: {metricas.distancia_munecas_cm:.1f} cm"
            if metricas.distancia_munecas_cm is not None else " | Munecas: -"
        )
        self.etiqueta_sistema.config(
            text=f"FPS: {self.fps:.0f} | Proceso: {self.tiempo_proceso_ms:.0f} ms"
        )
        if self.tiempo_proceso_ms > self.config.tiempo_maximo_proceso_ms:
            self.etiqueta_sistema.config(foreground="red")
        else:
            self.etiqueta_sistema.config(foreground="black")
        self._poner_banner(mensaje, color)
        self._refrescar_panel_errores(reglas)

    def _poner_banner(self, texto: str, color: str) -> None:
        """Banner principal de alto contraste: texto blanco sobre fondo saturado."""
        self.etiqueta_feedback.config(
            text=texto, background=FONDO_BANNER.get(color, FONDO_BANNER["gray"]), foreground="white"
        )

    def _refrescar_panel_errores(self, reglas: Sequence[ResultadoRegla]) -> None:
        """Colorea cada fila de «¿Qué está mal?» según el estado de su regla.

        El fondo hace visible el problema incluso con un vistazo rápido
        (RF-08 / RNF-04 usabilidad). Solo se toca Tk cuando algo cambió: doce
        llamadas a ``config`` por fotograma costaban ~20 ms de refresco.
        """
        por_id = {regla.id: regla for regla in reglas}
        for id_regla, (cuadro, etiqueta) in self._filas_estado.items():
            regla = por_id.get(id_regla)
            if regla is None:
                fondo, texto = FONDO_ESPERA, "—"
            else:
                fondo = self.generador.fondo_por_estado(regla.estado)
                texto = f"{regla.nombre}: {regla.mensaje}"
            fondo_anterior, texto_anterior = self._estado_filas.get(id_regla, ("", ""))
            if fondo != fondo_anterior:
                cuadro.config(background=fondo)
                etiqueta.config(background=fondo)
            if texto != texto_anterior:
                etiqueta.config(text=texto)
            self._estado_filas[id_regla] = (fondo, texto)

    def _mostrar_video(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(rgb).resize(
            (self.config.ancho_ventana_video, self.config.alto_ventana_video)
        )
        self.ultimo_fotograma = ImageTk.PhotoImage(image=imagen)
        self.etiqueta_video.imgtk = self.ultimo_fotograma
        self.etiqueta_video.config(image=self.ultimo_fotograma, text="")

    def _anotar(self, mensaje: str, color_error: bool = False) -> None:
        self.registro.config(state="normal")
        marca = datetime.now().strftime("%H:%M:%S")
        prefijo = "ERROR" if color_error else "INFO"
        self.registro.insert(tk.END, f"{marca} {prefijo}: {mensaje}\n")
        self.registro.see(tk.END)
        self.registro.config(state="disabled")

    def cerrar(self) -> None:
        self.en_curso = False
        self._fase = FASE_INACTIVA
        self.cuenta.cancelar()
        self.captura.liberar()
        self.alternar_csv(finalizar=True)
        self.procesador_pose.cerrar()
        self.root.destroy()