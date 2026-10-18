"""Interfaz gráfica Tkinter (RF-09 / CA-09, RNF-04 usabilidad).

Muestra el video con la superposición de landmarks y los indicadores de
calidad. Incluye un botón siempre visible para finalizar la sesión, tras el
cual se detienen la captura y el análisis y se presenta el resumen.
"""

from __future__ import annotations

import csv
import time
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
from typing import Optional

import cv2
from PIL import Image, ImageTk

from .analisis import AnalizadorRCP
from .captura import CapturaVideo
from .configuracion import Configuracion
from .procesamiento import Dibujante, ProcesadorArUco, ProcesadorPose
from .reglas import MotorReglas
from .retroalimentacion import GeneradorFeedback
from .sesion import Sesion


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
        self.marca_tiempo_ms = 0
        self.fps = 0.0
        self.ultimo_fotograma = None
        self.tiempo_proceso_ms = 0.0
        self._instante_fotograma_anterior: Optional[float] = None
        self._archivo_csv = None
        self._escritor_csv = None

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

        ttk.Label(derecha, text="Indicadores de calidad", font=("Segoe UI", 12, "bold")).pack(pady=4)

        self.etiqueta_frecuencia = ttk.Label(derecha, text="Frecuencia: 0 cpm", font=("Segoe UI", 12))
        self.etiqueta_frecuencia.pack(anchor="w")
        self.etiqueta_profundidad = ttk.Label(derecha, text="Profundidad: 0.0 cm", font=("Segoe UI", 12))
        self.etiqueta_profundidad.pack(anchor="w")
        self.etiqueta_conteo = ttk.Label(derecha, text="Compresiones: 0", font=("Segoe UI", 11))
        self.etiqueta_conteo.pack(anchor="w")
        self.etiqueta_brazos = ttk.Label(derecha, text="Angulo brazos: -", font=("Segoe UI", 10))
        self.etiqueta_brazos.pack(anchor="w")
        self.etiqueta_munecas = ttk.Label(derecha, text="Separacion munecas: -", font=("Segoe UI", 10))
        self.etiqueta_munecas.pack(anchor="w")
        self.etiqueta_sistema = ttk.Label(derecha, text="FPS: 0 | Proceso: 0 ms", font=("Segoe UI", 9))
        self.etiqueta_sistema.pack(anchor="w", pady=4)

        # RF-08: mensaje breve de corrección con color.
        self.etiqueta_feedback = ttk.Label(
            derecha, text="Presione Iniciar sesion", font=("Segoe UI", 11, "bold"),
            foreground="gray", wraplength=330, justify="left",
        )
        self.etiqueta_feedback.pack(anchor="w", pady=6)

        ttk.Separator(derecha).pack(fill="x", pady=6)

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

        ttk.Label(derecha, text="Registro de eventos:").pack(anchor="w", pady=(10, 2))
        self.registro = scrolledtext.ScrolledText(derecha, width=42, height=14, state="disabled")
        self.registro.pack(fill="both", expand=True)

        self.etiqueta_estado = ttk.Label(derecha, text="Estado: detenida")
        self.etiqueta_estado.pack(pady=4)

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
            self.etiqueta_feedback.config(text=resultado.mensaje, foreground="red")
            messagebox.showerror("Camara no disponible", resultado.mensaje)
            return

        self._anotar(resultado.mensaje)
        self.en_curso = True
        self.marca_tiempo_ms = 0
        self._instante_fotograma_anterior = None
        self.fps = 0.0
        self.sesion.iniciar()
        self.analizador.reiniciar()
        self.boton_finalizar.config(state="normal")
        self.etiqueta_estado.config(text="Estado: sesion en curso", foreground="green")
        self.etiqueta_video.config(text="Iniciando...")
        self._actualizar()

    def finalizar_sesion(self) -> None:
        """Detiene captura y análisis, y muestra el resumen (CA-09)."""
        if not self.en_curso:
            return
        self.en_curso = False
        self.captura.liberar()
        resumen = self.sesion.finalizar()
        self.alternar_csv(finalizar=True)
        self.boton_finalizar.config(state="disabled")
        self.etiqueta_estado.config(text="Estado: sesion finalizada", foreground="blue")
        self.etiqueta_feedback.config(text="Sesion finalizada", foreground="blue")
        self.ultimo_fotograma = None
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

        # Análisis.
        metricas = self.analizador.actualizar(
            instante=instante,
            landmarks_px=landmarks,
            centro_aruco_px=resultado_aruco.centro_px,
            lado_aruco_px=resultado_aruco.lado_px,
        )

        # Reglas y retroalimentación (RF-08).
        reglas = self.motor_reglas.evaluar(metricas)
        mensaje, color, mensaje_completo = self.generador.generar(reglas)

        # Registro de errores con marca de tiempo (CA-05, CA-06, CA-07).
        for error in self.sesion.registrar_reglas(reglas):
            self._anotar(str(error), color_error=True)

        # Superposición sobre el video (RF-09).
        self.dibujante.dibujar_landmarks(frame, landmarks)
        self.dibujante.dibujar_indicadores(
            frame, metricas, mensaje_completo, self.generador.color_bgr_por_estado(reglas[0].estado)
        )
        self.dibujante.dibujar_senal(frame, self.analizador.senal_historial())

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

        if self._escritor_csv is not None:
            self._escritor_csv.writerow([
                datetime.now().isoformat(timespec="milliseconds"),
                f"{self.sesion.duracion_s():.2f}",
                f"{self.fps:.1f}", f"{self.tiempo_proceso_ms:.1f}",
                f"{metricas.cpm:.1f}", f"{metricas.profundidad_cm:.2f}", metricas.compresiones,
                metricas.distancia_munecas_cm, metricas.distancia_esternon_cm,
                metricas.angulo_brazo_grados, int(metricas.esternon_ok), int(metricas.retorno_ok),
                metricas.px_por_cm,
            ])

        self._refrescar_paneles(metricas, mensaje, color)
        self._mostrar_video(frame)
        self.root.after(1, self._actualizar)

    # ---------------------------------------------------- presentation ---
    def _refrescar_paneles(self, metricas, mensaje: str, color: str) -> None:
        self.etiqueta_frecuencia.config(text=f"Frecuencia: {metricas.cpm:.0f} cpm")
        self.etiqueta_profundidad.config(text=f"Profundidad: {metricas.profundidad_cm:.1f} cm")
        self.etiqueta_conteo.config(text=f"Compresiones: {metricas.compresiones}")
        self.etiqueta_brazos.config(
            text=f"Angulo brazos: {metricas.angulo_brazo_grados:.0f} deg"
            if metricas.angulo_brazo_grados is not None else "Angulo brazos: -"
        )
        self.etiqueta_munecas.config(
            text=f"Separacion munecas: {metricas.distancia_munecas_cm:.1f} cm"
            if metricas.distancia_munecas_cm is not None else "Separacion munecas: -"
        )
        self.etiqueta_sistema.config(
            text=f"FPS: {self.fps:.0f} | Proceso: {self.tiempo_proceso_ms:.0f} ms"
        )
        if self.tiempo_proceso_ms > self.config.tiempo_maximo_proceso_ms:
            self.etiqueta_sistema.config(foreground="red")
        else:
            self.etiqueta_sistema.config(foreground="black")
        self.etiqueta_feedback.config(text=mensaje, foreground=color)

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
        self.captura.liberar()
        self.alternar_csv(finalizar=True)
        self.procesador_pose.cerrar()
        self.root.destroy()