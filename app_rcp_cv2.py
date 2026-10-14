"""
RCP solo-OpenCV (sin Tkinter) — evita error Tcl init.tcl en venv Windows.
Cumple RF-01..RF-09. Teclas: Q salir, R reset, C grabar CSV.
"""
import csv, time, urllib.request
from collections import deque
from datetime import datetime
from pathlib import Path
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python import vision as mpv
from app_rcp_aruco_pose import CompressionCounter, POSE_URL, HAND_URL, POSE_PATH, HAND_PATH, ensure_model, POSE_LINES

def angle(a,b,c):
    a,b,c=np.array(a),np.array(b),np.array(c)
    ba,bc=a-b,c-b
    cosang=np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-6)
    return float(np.degrees(np.arccos(np.clip(cosang,-1,1))))

def main():
    pose_model=ensure_model(POSE_URL,POSE_PATH)
    pose=mpv.PoseLandmarker.create_from_options(mpv.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=pose_model),
        running_mode=mpv.RunningMode.VIDEO,num_poses=1,
        min_pose_detection_confidence=0.5,min_tracking_confidence=0.5))
    aruco_dict=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    try:
        detector=cv2.aruco.ArucoDetector(aruco_dict,cv2.aruco.DetectorParameters()); new_api=True
    except AttributeError:
        detector=None; new_api=False
    MARKER_CM=5.0
    cap=cv2.VideoCapture(0,cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: no cámara"); return
    counter=CompressionCounter(); hist=deque(maxlen=90); hsh=deque(maxlen=90)
    base_y=None; base_s=None; ts=0; rec=None; wri=None; last_t=None; fps=0
    print("Q salir | R reset | C CSV")
    while True:
        ret,frame=cap.read()
        if not ret: break
        frame=cv2.flip(frame,1); h,w=frame.shape[:2]; ts+=33
        t0=time.time()
        # ArUco
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        if new_api: corners,ids,_=detector.detectMarkers(gray)
        else: corners,ids,_=cv2.aruco.detectMarkers(gray,aruco_dict)
        acx=acy=lado=None; pxcm=None
        if ids is not None and len(ids):
            cv2.aruco.drawDetectedMarkers(frame,corners,ids)
            c=corners[0][0]; acx,acy=float(c[:,0].mean()),float(c[:,1].mean())
            lado=float(np.mean([np.linalg.norm(c[i]-c[(i+1)%4]) for i in range(4)]))
            pxcm=lado/MARKER_CM
        # Pose 11,12,13,14,15,16,23,24
        mpi=mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
        wx=wy=sy=brazo=None; wd_cm=None; est_ok=False; rec_ok=True
        try:
            res=pose.detect_for_video(mpi,ts)
            if res.pose_landmarks:
                lms=res.pose_landmarks[0]
                for a,b in POSE_LINES:
                    xa,ya=int(lms[a].x*w),int(lms[a].y*h); xb,yb=int(lms[b].x*w),int(lms[b].y*h)
                    cv2.line(frame,(xa,ya),(xb,yb),(0,255,0),2)
                for i in (11,12,13,14,15,16,23,24):
                    cv2.circle(frame,(int(lms[i].x*w),int(lms[i].y*h)),4,(0,255,0),-1)
                x15,y15=lms[15].x*w,lms[15].y*h; x16,y16=lms[16].x*w,lms[16].y*h
                wx,wy=(x15+x16)/2,(y15+y16)/2
                sx=(lms[11].x+lms[12].x)/2*w; sy=(lms[11].y+lms[12].y)/2*h
                aw=np.hypot(lms[11].x-lms[12].x,lms[11].y-lms[12].y)*w
                brazo=(angle((lms[11].x,lms[11].y),(lms[13].x,lms[13].y),(lms[15].x,lms[15].y))+angle((lms[12].x,lms[12].y),(lms[14].x,lms[14].y),(lms[16].x,lms[16].y)))/2
                if pxcm:
                    wd_cm=np.hypot(lms[15].x-lms[16].x,lms[15].y-lms[16].y)*w/pxcm
                    est_ok=(abs(wx-sx)/max(aw,1)<0.35) and (wd_cm<12.0)
                hsh.append(float(sy))
                if base_s is None and len(hsh)>10: base_s=float(np.mean(list(hsh)[-10:]))
                if base_s is not None and pxcm:
                    rec_ok=abs(float(np.mean(list(hsh)[-5:]))-base_s)/pxcm<2.0
        except Exception as e:
            print("pose:",e)
        if wy is not None:
            hist.append(float(wy))
            ys=float(np.mean(list(hist)[-5:]))
            if base_y is None: base_y=ys
            ycm=(ys-base_y)/pxcm if pxcm else (ys-base_y)/10.0
            counter.update(ycm,time.time())
        n=counter.count; frec=counter.frequency(); prof=counter.mean_depth()
        msgs=[]
        if wx is None: msgs.append("Muestra torso/manos")
        elif acx is None: msgs.append("Muestra ArUco")
        else:
            if frec==0: msgs.append("Inicia compresiones")
            else:
                msgs.append("Ritmo OK" if 100<=frec<=120 else ("Aumente la frecuencia" if frec<100 else "Reduzca la frecuencia"))
                msgs.append("Prof OK" if 5<=prof<=6 else ("Presione más hondo" if prof<5 else "Presione menos hondo"))
            if brazo is not None and brazo<150: msgs.append("Estira brazos")
            if not est_ok: msgs.append("Centra manos")
            if not rec_ok: msgs.append("Permite retorno")
        txt=" | ".join(msgs)
        cv2.putText(frame,f"{frec} cpm | {prof} cm",(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,0,0),2)
        cv2.putText(frame,txt,(10,60),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)
        cv2.putText(frame,f"FPS:{fps:.0f} ArUco:{'SI' if acx is not None else 'NO'}",(10,90),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),2)
        if rec and wri:
            wri.writerow([datetime.now().isoformat(timespec="milliseconds"),n,frec,prof,
                          f"{wx:.1f}" if wx else "",f"{wy:.1f}" if wy else "",
                          f"{wd_cm:.2f}" if wd_cm is not None else "",int(est_ok),int(rec_ok),
                          f"{brazo:.1f}" if brazo else ""])
        cv2.imshow("RCP RF-01..RF-09 (Q/R/C)",frame)
        if last_t: fps=fps*0.9+(1/max(1e-3,time.time()-t0))*0.1 if fps else 1/max(1e-3,time.time()-t0)
        last_t=t0
        k=cv2.waitKey(1)&0xFF
        if k==ord('q'): break
        if k==ord('r'):
            counter.reset(); hist.clear(); hsh.clear(); base_y=base_s=None; print("reset")
        if k==ord('c'):
            if rec is None:
                p=f"rcp_{datetime.now():%Y%m%d_%H%M%S}.csv"
                rec=open(p,"w",newline="",encoding="utf-8"); wri=csv.writer(rec)
                wri.writerow(["ts","n","frec","prof","wx","wy","dist_manos","esternon","recoil","brazo"])
                print("grabando",p)
            else:
                rec.close(); rec=None; print("csv cerrado")
    cap.release()
    if rec: rec.close()
    try: pose.close()
    except Exception: pass
    cv2.destroyAllWindows()

if __name__=="__main__":
    main()
