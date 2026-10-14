"""
Proyecto Grado RCP - OpenCV + MediaPipe Tasks (Pose/Hands) + ArUco + Tkinter
Mide: distancia mano-marcador, profundidad y frecuencia de compresiones. Guarda CSV.

MediaPipe 1.x ya NO tiene mp.solutions. Usa Tasks API (PoseLandmarker / HandLandmarker).
Modelos se descargan solos la primera vez a ./models/.

Instalar: pip install opencv-contrib-python mediapipe pillow numpy
Guia RCP (AHA): frecuencia 100-120/min, profundidad 5-6 cm.
"""

import csv
import time
import urllib.request
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from PIL import Image, ImageTk
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python import vision as mpv

POSE_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
HAND_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
POSE_PATH = Path("models/pose_landmarker_lite.task")
HAND_PATH = Path("models/hand_landmarker.task")

# Conexiones para dibujo manual con cv2 (RF-02: 11,12 hombros - 13,14 codos - 15,16 muñecas - 23,24 caderas)
POSE_LINES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
              (11, 23), (12, 24), (23, 24)]
HAND_LINES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
              (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
              (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


def ensure_model(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return str(path)
    print(f"Descargando modelo {path.name} ...")
    urllib.request.urlretrieve(url, str(path))
    return str(path)


# ---------------- Contador de compresiones ----------------
class CompressionCounter:
    """Detecta compresiones por picos en la señal vertical de la muñeca."""
    def __init__(self, min_amp_cm=1.5, min_interval_s=0.3):
        self.min_amp_cm = min_amp_cm
        self.min_interval_s = min_interval_s
        self.reset()

    def reset(self):
        self.count = 0
        self.last_peak_time = 0
        self._last_count_t = None
        self.depths = deque(maxlen=10)
        self.intervals = deque(maxlen=10)
        self.last_depth = 0.0
        self._prev = None
        self._dir = 0
        self._last_high = None
        self._extreme = None

    def update(self, y_cm, t):
        if self._prev is None:
            self._prev = y_cm
            self._extreme = y_cm
            self._last_high = y_cm
            return False
        dy = y_cm - self._prev
        thresh = 0.05
        new_dir = 1 if dy > thresh else (-1 if dy < -thresh else self._dir)
        counted = False
        if self._dir == 0:
            self._dir = new_dir
            self._extreme = y_cm
        if new_dir != 0 and new_dir != self._dir:
            if self._dir == 1 and new_dir == -1:
                valley = self._extreme
                high = self._last_high if self._last_high is not None else valley
                amp = valley - high
                if amp >= self.min_amp_cm:
                    last_t = self._last_count_t
                    if last_t is None or (t - last_t) >= self.min_interval_s:
                        self.count += 1
                        self.last_peak_time = t
                        self.last_depth = round(float(amp), 2)
                        self.depths.append(self.last_depth)
                        if last_t is not None:
                            self.intervals.append(t - last_t)
                        self._last_count_t = t
                        counted = True
            elif self._dir == -1 and new_dir == 1:
                self._last_high = self._extreme
            self._dir = new_dir
            self._extreme = y_cm
        else:
            if self._dir == 1:
                self._extreme = max(self._extreme, y_cm)
            elif self._dir == -1:
                self._extreme = min(self._extreme, y_cm)
            else:
                self._extreme = y_cm
        self._prev = y_cm
        return counted

    def frequency(self):
        if len(self.intervals) == 0:
            return 0.0
        mean_dt = float(np.mean(list(self.intervals)[-5:]))
        if mean_dt <= 0:
            return 0.0
        return round(60.0 / mean_dt, 1)

    def mean_depth(self):
        if not self.depths:
            return 0.0
        return round(float(np.mean(list(self.depths)[-5:])), 2)


# ---------------- App ----------------
class RCPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Proyecto RCP - Pose + ArUco + CSV (MediaPipe 1.x)")
        self.root.geometry("1120x700")

        self.cap = None
        self.running = False
        self.t0 = None
        self._ts_ms = 0

        # MediaPipe Tasks (nueva API, sin mp.solutions)
        self.pose = None
        self.hand = None
        try:
            pose_model = ensure_model(POSE_URL, POSE_PATH)
            opts = mpv.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=pose_model),
                running_mode=mpv.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.pose = mpv.PoseLandmarker.create_from_options(opts)
        except Exception as e:
            print(f"Aviso: no se pudo crear PoseLandmarker: {e}")
        try:
            hand_model = ensure_model(HAND_URL, HAND_PATH)
            hopts = mpv.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=hand_model),
                running_mode=mpv.RunningMode.VIDEO, num_hands=2,
                min_hand_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.hand = mpv.HandLandmarker.create_from_options(hopts)
        except Exception as e:
            print(f"Aviso: no se pudo crear HandLandmarker: {e}")

        # ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        try:
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
            self.new_api = True
        except AttributeError:
            self.detector = None
            self.new_api = False

        self.hist_y = deque(maxlen=90)
        self.hist_shoulder_y = deque(maxlen=90)  # RF-06 recoil
        self.counter = CompressionCounter()
        self.px_per_cm = None
        self.baseline_y_px = None
        self.baseline_shoulder_px = None
        self.fps = 0.0
        self._last_frame_t = None

        self.csv_file = None
        self.csv_writer = None
        self.recording = False

        self._build_ui()
        if self.pose is None:
            self._log("ERROR: PoseLandmarker no disponible. Revisa ./models/ e internet.")

    # ---------- UI ----------
    def _build_ui(self):
        left = ttk.Frame(self.root, padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.video_label = ttk.Label(left, text="Cámara detenida")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(self.root, padding=8, width=340)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        ttk.Label(right, text="Métricas RCP", font=("Segoe UI", 12, "bold")).pack()
        self.lbl_count = ttk.Label(right, text="Compresiones: 0", font=("Segoe UI", 14, "bold"))
        self.lbl_count.pack(pady=2)
        self.lbl_freq = ttk.Label(right, text="Frecuencia: 0 /min", font=("Segoe UI", 11))
        self.lbl_freq.pack()
        self.lbl_depth = ttk.Label(right, text="Profundidad: 0.0 cm", font=("Segoe UI", 11))
        self.lbl_depth.pack()
        self.lbl_dist = ttk.Label(right, text="Dist. mano-marcador: —", font=("Segoe UI", 10))
        self.lbl_dist.pack()
        self.lbl_scale = ttk.Label(right, text="Escala: sin ArUco", font=("Segoe UI", 9))
        self.lbl_scale.pack()
        self.lbl_feedback = ttk.Label(right, text="—", font=("Segoe UI", 10, "bold"))
        self.lbl_feedback.pack(pady=4)

        ttk.Separator(right).pack(fill="x", pady=6)

        self.var_pose = tk.BooleanVar(value=True)
        self.var_hands = tk.BooleanVar(value=False)
        self.var_aruco = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Pose (MediaPipe)", variable=self.var_pose).pack(anchor="w")
        ttk.Checkbutton(right, text="Manos (MediaPipe)", variable=self.var_hands).pack(anchor="w")
        ttk.Checkbutton(right, text="ArUco", variable=self.var_aruco).pack(anchor="w")

        frm = ttk.Frame(right)
        frm.pack(fill="x", pady=6)
        ttk.Label(frm, text="Tamaño marcador (cm):").grid(row=0, column=0, sticky="w")
        self.ent_marker_cm = ttk.Entry(frm, width=8)
        self.ent_marker_cm.insert(0, "5.0")
        self.ent_marker_cm.grid(row=0, column=1, padx=4)
        ttk.Label(frm, text="ID objetivo:").grid(row=1, column=0, sticky="w")
        self.ent_marker_id = ttk.Entry(frm, width=8)
        self.ent_marker_id.insert(0, "0")
        self.ent_marker_id.grid(row=1, column=1, padx=4)

        ttk.Button(right, text="Iniciar cámara", command=self.start).pack(fill="x", pady=2)
        ttk.Button(right, text="Detener", command=self.stop).pack(fill="x", pady=2)
        ttk.Button(right, text="Calibrar / Reset contador", command=self.calibrate).pack(fill="x", pady=2)
        ttk.Button(right, text="Generar marcador PNG (ID objetivo)", command=self.save_marker).pack(fill="x", pady=2)
        self.btn_rec = ttk.Button(right, text="● Grabar CSV", command=self.toggle_rec)
        self.btn_rec.pack(fill="x", pady=2)

        self.log = scrolledtext.ScrolledText(right, width=40, height=10, state="disabled")
        self.log.pack(fill="both", expand=True, pady=4)
        self.lbl_status = ttk.Label(right, text="Estado: detenido")
        self.lbl_status.pack()

    def _log(self, m):
        self.log.config(state="normal")
        self.log.insert(tk.END, m + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    # ---------- Cámara / CSV ----------
    def start(self):
        if self.running:
            return
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self._log("ERROR: no se pudo abrir la cámara.")
            return
        self.running = True
        self.t0 = time.time()
        self._ts_ms = 0
        self.lbl_status.config(text="Estado: corriendo")
        self._log("Cámara iniciada.")
        self._update()

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.recording:
            self.toggle_rec()
        self.lbl_status.config(text="Estado: detenido")
        self.video_label.config(image="", text="Cámara detenida")

    def calibrate(self):
        self.counter.reset()
        self.hist_y.clear()
        self.hist_shoulder_y.clear()
        self.baseline_y_px = None
        self.baseline_shoulder_px = None
        self.lbl_count.config(text="Compresiones: 0")
        self._log("Contador y línea base reiniciados. Mantén manos en posición de reposo.")

    def save_marker(self):
        try:
            mid = int(self.ent_marker_id.get())
        except ValueError:
            mid = 0
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            initialfile=f"aruco_ID{mid}.png",
                                            filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            img = cv2.aruco.generateImageMarker(self.aruco_dict, mid, 300)
        except AttributeError:
            img = np.zeros((300, 300), dtype=np.uint8)
            cv2.aruco.drawMarker(self.aruco_dict, mid, 300, img, 1)
        cv2.imwrite(path, img)
        self._log(f"Marcador ID {mid} guardado en {path}.")

    def toggle_rec(self):
        if not self.recording:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"rcp_{datetime.now():%Y%m%d_%H%M%S}.csv",
                filetypes=[("CSV", "*.csv")])
            if not path:
                return
            self.csv_file = open(path, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(["timestamp", "t_s", "fps", "wrist_x_px", "wrist_y_px",
                                      "shoulder_y_px", "hip_y_px", "aruco_cx", "aruco_cy",
                                      "dist_px", "dist_cm", "dist_manos_cm", "pos_esternon_ok",
                                      "recoil_ok", "ang_brazo",
                                      "px_por_cm", "compresiones", "frec_ppm", "prof_cm"])
            self.recording = True
            self.btn_rec.config(text="■ Detener grabación")
            self._log(f"Grabando CSV: {path}")
        else:
            self.recording = False
            if self.csv_file:
                self.csv_file.close()
            self.btn_rec.config(text="● Grabar CSV")
            self._log("CSV cerrado.")

    # ---------- Detección ----------
    def detect_aruco(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.new_api:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)
        if ids is None or len(ids) == 0:
            return frame, None, None, None, []
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        try:
            target = int(self.ent_marker_id.get())
        except ValueError:
            target = None
        idx = 0
        flat = ids.flatten().tolist()
        if target in flat:
            idx = flat.index(target)
        c = corners[idx][0]
        cx, cy = float(c[:, 0].mean()), float(c[:, 1].mean())
        lados = [np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]
        lado_px = float(np.mean(lados))
        cv2.circle(frame, (int(cx), int(cy)), 5, (0, 255, 0), -1)
        return frame, cx, cy, lado_px, flat

    @staticmethod
    def angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cosang = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return float(np.degrees(np.arccos(np.clip(cosang, -1, 1))))

    def _mp_image(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    def _draw_landmarks(self, frame, lms, w, h, connections, color=(0, 255, 0)):
        pts = {}
        for i, lm in enumerate(lms):
            x, y = int(lm.x * w), int(lm.y * h)
            pts[i] = (x, y)
            cv2.circle(frame, (x, y), 3, color, -1)
        for a, b in connections:
            if a in pts and b in pts:
                cv2.line(frame, pts[a], pts[b], color, 2)

    # ---------- Loop ----------
    def _update(self):
        if not self.running:
            return
        ret, frame = self.cap.read()
        if not ret:
            self._log("ERROR: frame no capturado.")
            self.stop()
            return
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        t = time.time() - (self.t0 or time.time())
        self._ts_ms += 33  # timestamp monotónico para Tasks VIDEO

        # 1) ArUco
        acx = acy = lado_px = None
        ids = []
        if self.var_aruco.get():
            frame, acx, acy, lado_px, ids = self.detect_aruco(frame)
            try:
                mcm = float(self.ent_marker_cm.get())
            except ValueError:
                mcm = 5.0
            self.px_per_cm = (lado_px / mcm) if (lado_px and mcm > 0) else None
        else:
            self.px_per_cm = None

        # 2) Pose RF-02 (Tasks API): 11,12 hombros - 13,14 codos - 15,16 muñecas - 23,24 caderas
        wx = wy = sx = sy = hx = hy = None
        wrist_dist_cm = None
        esternon_ok = False
        recoil_ok = True
        brazo_ang = None
        ancho_hombros_px = None
        if self.var_pose.get() and self.pose is not None:
            try:
                res = self.pose.detect_for_video(self._mp_image(frame), self._ts_ms)
                if res.pose_landmarks:
                    lms = res.pose_landmarks[0]
                    self._draw_landmarks(frame, lms, w, h, POSE_LINES, (0, 255, 0))
                    x15, y15 = lms[15].x * w, lms[15].y * h
                    x16, y16 = lms[16].x * w, lms[16].y * h
                    wx, wy = (x15 + x16) / 2, (y15 + y16) / 2
                    x11, y11 = lms[11].x * w, lms[11].y * h
                    x12, y12 = lms[12].x * w, lms[12].y * h
                    sx, sy = (x11 + x12) / 2, (y11 + y12) / 2
                    x23, y23 = lms[23].x * w, lms[23].y * h
                    x24, y24 = lms[24].x * w, lms[24].y * h
                    hx, hy = (x23 + x24) / 2, (y23 + y24) / 2
                    ancho_hombros_px = float(np.hypot(x11 - x12, y11 - y12))
                    try:
                        a1 = self.angle((lms[11].x, lms[11].y), (lms[13].x, lms[13].y), (lms[15].x, lms[15].y))
                        a2 = self.angle((lms[12].x, lms[12].y), (lms[14].x, lms[14].y), (lms[16].x, lms[16].y))
                        brazo_ang = (a1 + a2) / 2
                    except Exception:
                        pass
                    cv2.circle(frame, (int(wx), int(wy)), 8, (255, 0, 0), -1)
                    cv2.circle(frame, (int(sx), int(sy)), 6, (0, 0, 255), -1)
                    cv2.circle(frame, (int(hx), int(hy)), 6, (255, 0, 255), -1)
            except Exception as e:
                self._log(f"Pose error: {e}")

        # 3) Hands opcional
        n_hands = 0
        if self.var_hands.get() and self.hand is not None:
            try:
                rh = self.hand.detect_for_video(self._mp_image(frame), self._ts_ms)
                if rh.hand_landmarks:
                    n_hands = len(rh.hand_landmarks)
                    for hl in rh.hand_landmarks:
                        self._draw_landmarks(frame, hl, w, h, HAND_LINES, (255, 0, 0))
            except Exception as e:
                self._log(f"Hands error: {e}")

        # 4) RF-04/RF-05/RF-06: distancias + compresiones + recoil
        dist_px = dist_cm = None
        if wx is not None and acx is not None:
            dist_px = float(np.hypot(wx - acx, wy - acy))
            if self.px_per_cm:
                dist_cm = dist_px / self.px_per_cm
            cv2.line(frame, (int(wx), int(wy)), (int(acx), int(acy)), (0, 255, 255), 2)

        # RF-05: distancia entre muñecas (manos juntas) y alineación esternón
        if wx is not None and sy is not None:
            wrist_px = float(np.hypot((lms[15].x - lms[16].x) * w, (lms[15].y - lms[16].y) * h))
            if self.px_per_cm:
                wrist_dist_cm = wrist_px / self.px_per_cm
            # esternón: mid-muñecas alineado en X con mid-hombros
            if ancho_hombros_px and ancho_hombros_px > 1:
                dx = abs(wx - sx) / ancho_hombros_px
                manos_juntas = (wrist_dist_cm is None) or (wrist_dist_cm < 12.0)
                cerca_aruco = True if dist_cm is None else (dist_cm < 15.0)
                esternon_ok = (dx < 0.35) and manos_juntas and cerca_aruco

        # RF-06: recoil por elevación de hombros
        if sy is not None:
            self.hist_shoulder_y.append(float(sy))
            if self.baseline_shoulder_px is None and len(self.hist_shoulder_y) > 10:
                self.baseline_shoulder_px = float(np.mean(list(self.hist_shoulder_y)[-10:]))
            if self.baseline_shoulder_px is not None and self.px_per_cm:
                desvio = abs(float(np.mean(list(self.hist_shoulder_y)[-5:])) - self.baseline_shoulder_px) / self.px_per_cm
                recoil_ok = desvio < 2.0  # si hombros quedan >2cm abajo, no hubo retorno completo

        if wy is not None:
            self.hist_y.append(float(wy))
            y_smooth = float(np.mean(list(self.hist_y)[-5:]))
            if self.baseline_y_px is None:
                self.baseline_y_px = y_smooth
            y_cm = ((y_smooth - self.baseline_y_px) / self.px_per_cm) if self.px_per_cm else ((y_smooth - self.baseline_y_px) / 10.0)
            if self.counter.update(y_cm, time.time()):
                self._log(f"Compresión #{self.counter.count} prof={self.counter.last_depth}cm frec={self.counter.frequency()}/min")
            self._draw_signal(frame)

        # FPS real (RF-01 ≥15)
        now = time.time()
        if self._last_frame_t is not None:
            dt = now - self._last_frame_t
            if dt > 0:
                inst = 1.0 / dt
                self.fps = self.fps * 0.9 + inst * 0.1 if self.fps else inst
        self._last_frame_t = now

        # 5) Métricas RF-08
        n = self.counter.count
        frec = self.counter.frequency()
        prof = self.counter.mean_depth()
        self.lbl_count.config(text=f"Compresiones: {n}")
        self.lbl_freq.config(text=f"Frecuencia: {frec} /min {'OK' if 100 <= frec <= 120 else ''}")
        self.lbl_depth.config(text=f"Profundidad: {prof} cm {'OK' if 5 <= prof <= 6 else ''}")
        self.lbl_dist.config(
            text=f"Dist. mano-marcador: {dist_cm:.1f} cm" if dist_cm is not None
            else (f"Dist: {dist_px:.0f} px (sin escala)" if dist_px else "Dist. mano-marcador: —"))
        self.lbl_scale.config(
            text=f"{self.fps:.0f} fps | Escala:{self.px_per_cm:.1f}px/cm | ArUco:{ids if ids else '—'} | Manos:{n_hands} | Muñecas:{wrist_dist_cm:.1f}cm" if (self.px_per_cm and wrist_dist_cm is not None)
            else f"{self.fps:.0f} fps | ArUco:{ids if ids else '—'} | Manos:{n_hands}")

        fb, color = self.feedback_ex(frec, prof, brazo_ang, wx is not None, acx is not None,
                                     esternon_ok, recoil_ok, wrist_dist_cm)
        self.lbl_feedback.config(text=fb, foreground=color)
        cv2.putText(frame, fb.split(" | ")[0], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # 6) CSV
        if self.recording and self.csv_writer:
            self.csv_writer.writerow([
                datetime.now().isoformat(timespec="milliseconds"), f"{t:.2f}", f"{self.fps:.1f}",
                f"{wx:.1f}" if wx else "", f"{wy:.1f}" if wy else "",
                f"{sy:.1f}" if sy else "", f"{hy:.1f}" if hy else "",
                f"{acx:.1f}" if acx else "", f"{acy:.1f}" if acy else "",
                f"{dist_px:.1f}" if dist_px else "",
                f"{dist_cm:.2f}" if dist_cm is not None else "",
                f"{wrist_dist_cm:.2f}" if wrist_dist_cm is not None else "",
                int(esternon_ok), int(recoil_ok),
                f"{brazo_ang:.1f}" if brazo_ang else "",
                f"{self.px_per_cm:.2f}" if self.px_per_cm else "",
                n, frec, prof])

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img).resize((680, 500))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk, text="")
        self.root.after(15, self._update)

    def _draw_signal(self, frame):
        vals = list(self.hist_y)
        if len(vals) < 5:
            return
        base = np.mean(vals[-30:]) if len(vals) >= 30 else vals[0]
        norm = [(v - base) for v in vals[-90:]]
        x0, y0, bw, bh = 10, frame.shape[0] - 110, 220, 90
        cv2.rectangle(frame, (x0, y0), (x0 + bw, y0 + bh), (0, 0, 0), -1)
        mx = max(20.0, max(abs(v) for v in norm))
        pts = []
        for i, v in enumerate(norm):
            x = int(x0 + i / max(1, len(norm) - 1) * bw)
            y = int(y0 + bh / 2 + v / mx * (bh / 2 - 5))
            pts.append((x, y))
        for i in range(1, len(pts)):
            cv2.line(frame, pts[i - 1], pts[i], (0, 255, 0), 2)

    @staticmethod
    def feedback(frec, prof, brazo_ang, hay_manos, hay_aruco):
        return RCPApp.feedback_ex(frec, prof, brazo_ang, hay_manos, hay_aruco, True, True, None)

    @staticmethod
    def feedback_ex(frec, prof, brazo_ang, hay_manos, hay_aruco, esternon_ok=True, recoil_ok=True, wrist_dist_cm=None):
        # RF-08: indicadores en tiempo real
        if not hay_manos:
            return "Muestra tus manos/torso a la cámara", "orange"
        if not hay_aruco:
            return "Muestra el marcador ArUco (pecho)", "orange"
        msgs = []
        if frec == 0:
            msgs.append("Inicia compresiones")
        else:
            if frec < 100:
                msgs.append("Más rápido")
            elif frec > 120:
                msgs.append("Más lento")
            else:
                msgs.append("Ritmo OK")
            if prof < 5:
                msgs.append("Más profundo")
            elif prof > 6:
                msgs.append("Menos profundo")
            else:
                msgs.append("Profundidad OK")
        if brazo_ang is not None and brazo_ang < 150:
            msgs.append("Estira los brazos")
        # RF-05 RF-06
        if wrist_dist_cm is not None and wrist_dist_cm >= 12.0:
            msgs.append("Junta las manos")
        if not esternon_ok:
            msgs.append("Centra manos en esternón")
        if not recoil_ok:
            msgs.append("Permite retorno completo")
        txt = " | ".join(msgs)
        ok = ("OK" in txt and "Más" not in txt and "Junta" not in txt and "Centra" not in txt and "retorno" not in txt)
        return txt, ("green" if ok else "red")

    def on_close(self):
        self.stop()
        try:
            if self.pose:
                self.pose.close()
            if self.hand:
                self.hand.close()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RCPApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
