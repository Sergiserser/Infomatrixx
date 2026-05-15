#!/usr/bin/env python3
"""
StepPrep — Threat Detector (Fixed for mediapipe 0.10+)
Uses NEW mediapipe Tasks API. Downloads models automatically.

Install:
    pip install opencv-python mediapipe requests

Run:
    python threat_detector.py
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
import os
import sys
import urllib.request
from collections import deque

# ── Download models ───────────────────────────────────────────────
MODEL_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mp_models")
POSE_MODEL = os.path.join(MODEL_DIR, "pose_landmarker_lite.task")
HAND_MODEL = os.path.join(MODEL_DIR, "hand_landmarker.task")
POSE_URL   = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
HAND_URL   = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

def download_model(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return
    print(f"Downloading {os.path.basename(path)} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path,"wb") as f:
            total = int(r.headers.get("Content-Length",0))
            done  = 0
            while True:
                chunk = r.read(65536)
                if not chunk: break
                f.write(chunk); done += len(chunk)
                if total:
                    print(f"\r  {done/total*100:.0f}% ({done//1024}KB)", end="", flush=True)
        print(f"\r  Done: {os.path.getsize(path)//1024} KB          ")
    except Exception as e:
        print(f"\nERROR: {e}")
        print(f"Manually download from:\n  {url}")
        print(f"Save as: {path}"); sys.exit(1)

print("StepPrep Threat Detector")
print("Checking models...")
download_model(POSE_URL, POSE_MODEL)
download_model(HAND_URL, HAND_MODEL)
print("Models ready.\n")

# ── MediaPipe new Tasks API ───────────────────────────────────────
vision      = mp.tasks.vision
BaseOptions = mp.tasks.BaseOptions
RunningMode = vision.RunningMode
PoseLandmarker        = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
HandLandmarker        = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions

# ── Landmark indices ──────────────────────────────────────────────
NOSE=0; L_SH=11; R_SH=12; L_EL=13; R_EL=14; L_WR=15; R_WR=16

# ── Config ────────────────────────────────────────────────────────
THREAT_FRAMES    = 7
COLLISION_DIST   = 0.13
SWING_VEL_THRESH = 0.036
SOS_COOLDOWN     = 4.0

# ── Colours (BGR) ─────────────────────────────────────────────────
GREEN=(0,210,90); RED=(30,30,220); ORANGE=(0,155,255)
WHITE=(255,255,255); BLUE=(200,100,30)

# ── State ─────────────────────────────────────────────────────────
threat_counter={}; sos_count=0; sos_log=[]
last_sos=0.0; sos_flash_t=0.0
prev_wrists=deque(maxlen=5); fps_q=deque(maxlen=20)

LABELS={"FIST_FACE":"FIST -> FACE","FIST_BODY":"FIST -> BODY",
        "FIST_FIST":"FIST COLLISION","GUN_POSE":"GUN POSE",
        "ARM_SWING":"ARM SWING","THREAT_STANCE":"THREAT STANCE","PUNCH":"PUNCH"}

def d2(a,b): return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2)

def angle3(a,b,c):
    ba=np.array([a.x-b.x,a.y-b.y]); bc=np.array([c.x-b.x,c.y-b.y])
    return math.degrees(math.acos(np.clip(np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-6),-1,1)))

def tick(key,detected):
    threat_counter[key]=max(0,threat_counter.get(key,0)+(1 if detected else -1))
    return threat_counter[key]>=THREAT_FRAMES

def analyse_hand(lms):
    tips=[4,8,12,16,20]; pips=[3,7,11,15,19]; ext=[]
    ext.append(lms[4].x<lms[3].x if lms[0].x<lms[9].x else lms[4].x>lms[3].x)
    for t,p in zip(tips[1:],pips[1:]): ext.append(lms[t].y<lms[p].y)
    return {"is_fist":not any(ext[1:]),
            "is_gun": ext[1] and not ext[2] and not ext[3] and not ext[4],
            "wrist":lms[0],"idx_tip":lms[8]}

def analyse_pose(lms):
    l_sh=lms[L_SH]; r_sh=lms[R_SH]; l_el=lms[L_EL]; r_el=lms[R_EL]
    l_wr=lms[L_WR]; r_wr=lms[R_WR]; nose=lms[NOSE]; bw=d2(l_sh,r_sh)
    return {"nose":nose,"l_wrist":l_wr,"r_wrist":r_wr,
            "l_elbow":l_el,"r_elbow":r_el,"l_shoulder":l_sh,"r_shoulder":r_sh,
            "l_wrist_raise":l_sh.y-l_wr.y,"r_wrist_raise":r_sh.y-r_wr.y,
            "l_arm_angle":angle3(l_sh,l_el,l_wr),"r_arm_angle":angle3(r_sh,r_el,r_wr),
            "l_elbow_flare":abs(l_el.x-l_sh.x)/(bw+1e-6),
            "r_elbow_flare":abs(r_el.x-r_sh.x)/(bw+1e-6),"body_width":bw}

def get_threats(pose,hands):
    found=[]
    fists=[h for h in hands if h["is_fist"]]
    for f in fists:
        if d2(f["wrist"],pose["nose"])<COLLISION_DIST*1.5: found.append("FIST_FACE")
        for s in ["l_shoulder","r_shoulder"]:
            if d2(f["wrist"],pose[s])<COLLISION_DIST: found.append("FIST_BODY")
    if len(fists)>=2 and d2(fists[0]["wrist"],fists[1]["wrist"])<COLLISION_DIST*.7:
        found.append("FIST_FIST")
    for h in hands:
        if h["is_gun"]: found.append("GUN_POSE")
    lw,rw=pose["l_wrist"],pose["r_wrist"]
    if prev_wrists:
        pl,pr=prev_wrists[-1]
        if d2(lw,pl)>SWING_VEL_THRESH and pose["l_wrist_raise"]>0.05: found.append("ARM_SWING")
        if d2(rw,pr)>SWING_VEL_THRESH and pose["r_wrist_raise"]>0.05: found.append("ARM_SWING")
    lwr=pose["l_wrist_raise"]; rwr=pose["r_wrist_raise"]
    lf=pose["l_elbow_flare"]; rf=pose["r_elbow_flare"]
    if lwr>.08 and rwr>.08 and lf>.4 and rf>.4: found.append("THREAT_STANCE")
    if lwr>.1 and lf>.6 and pose["l_arm_angle"]>140: found.append("PUNCH")
    if rwr>.1 and rf>.6 and pose["r_arm_angle"]>140: found.append("PUNCH")
    return found

POSE_CONN=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24)]
HAND_CONN=[(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),
           (10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),
           (18,19),(19,20),(5,9),(9,13),(13,17)]

def draw_pose(frame,lms,w,h):
    pts=[(int(l.x*w),int(l.y*h)) for l in lms]
    for a,b in POSE_CONN:
        if a<len(pts) and b<len(pts): cv2.line(frame,pts[a],pts[b],GREEN,2)
    for i in [0,11,12,13,14,15,16]: 
        if i<len(pts): cv2.circle(frame,pts[i],4,BLUE,-1)

def draw_hand(frame,lms,w,h,col):
    pts=[(int(l.x*w),int(l.y*h)) for l in lms]
    for a,b in HAND_CONN: cv2.line(frame,pts[a],pts[b],col,2)
    for p in pts: cv2.circle(frame,p,3,WHITE,-1)

def main():
    global sos_count,last_sos,sos_flash_t
    cap=cv2.VideoCapture(0)
    if not cap.isOpened(): print("ERROR: Cannot open webcam."); return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
    cap.set(cv2.CAP_PROP_FPS,30)

    pose_opts=PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_MODEL),
        running_mode=RunningMode.VIDEO, num_poses=2,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6)
    hand_opts=HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL),
        running_mode=RunningMode.VIDEO, num_hands=4,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.55)

    print("Running. Q=quit  S=manual SOS  R=reset")

    with PoseLandmarker.create_from_options(pose_opts) as pose_det, \
         HandLandmarker.create_from_options(hand_opts) as hand_det:
        frame_ts=0
        while True:
            t0=time.time()
            ok,frame=cap.read()
            if not ok: break
            frame=cv2.flip(frame,1)
            h,w=frame.shape[:2]
            frame_ts+=int(1000/30)

            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            mp_img=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
            pose_res=pose_det.detect_for_video(mp_img,frame_ts)
            hand_res=hand_det.detect_for_video(mp_img,frame_ts)

            pose_data=None; hand_list=[]

            if pose_res.pose_landmarks:
                lms=pose_res.pose_landmarks[0]
                draw_pose(frame,lms,w,h)
                pose_data=analyse_pose(lms)
                nx,ny=int(pose_data["nose"].x*w),int(pose_data["nose"].y*h)
                cv2.circle(frame,(nx,ny),int(pose_data["body_width"]*w*.55),GREEN,1)

            if hand_res.hand_landmarks:
                for i,hlms in enumerate(hand_res.hand_landmarks):
                    col=ORANGE if i%2==0 else (0,200,255)
                    draw_hand(frame,hlms,w,h,col)
                    ha=analyse_hand(hlms)
                    hand_list.append(ha)
                    wx,wy=int(ha["wrist"].x*w),int(ha["wrist"].y*h)
                    if ha["is_fist"]:
                        cv2.rectangle(frame,(wx-28,wy-32),(wx+66,wy+6),(0,0,180),-1)
                        cv2.putText(frame,"FIST",(wx-24,wy-8),cv2.FONT_HERSHEY_DUPLEX,.7,WHITE,2)
                    elif ha["is_gun"]:
                        cv2.rectangle(frame,(wx-28,wy-32),(wx+130,wy+6),(0,60,180),-1)
                        cv2.putText(frame,"GUN POSE",(wx-24,wy-8),cv2.FONT_HERSHEY_DUPLEX,.7,WHITE,2)

            all_threats=[]; confirmed=[]
            if pose_data:
                all_threats=get_threats(pose_data,hand_list)
                prev_wrists.append((pose_data["l_wrist"],pose_data["r_wrist"]))
            for th in set(all_threats):
                if tick(th,True): confirmed.append(LABELS.get(th,th))
            for k in list(threat_counter):
                if k not in all_threats: tick(k,False)

            if confirmed and time.time()-last_sos>SOS_COOLDOWN:
                last_sos=time.time(); sos_count+=1; sos_flash_t=time.time()
                reason=" | ".join(confirmed[:2])
                sos_log.append(f"{time.strftime('%H:%M:%S')} - {reason}")
                print(f"SOS #{sos_count}: {reason}")

            bar=(0,30,180) if confirmed else (0,100,0)
            cv2.rectangle(frame,(0,0),(w,52),bar,-1)
            txt="SOS! "+" | ".join(confirmed[:2]) if confirmed else "OK - Monitoring"
            cv2.putText(frame,txt,(12,36),cv2.FONT_HERSHEY_DUPLEX,.85,WHITE,2)
            fps_q.append(1.0/max(time.time()-t0,1e-6))
            cv2.putText(frame,f"FPS:{sum(fps_q)/len(fps_q):.0f} SOS:{sos_count}",
                        (w-180,36),cv2.FONT_HERSHEY_SIMPLEX,.6,WHITE,1)

            if time.time()-sos_flash_t<.7:
                ov=frame.copy()
                cv2.rectangle(ov,(0,0),(w,h),(0,0,200),-1)
                cv2.addWeighted(ov,.3,frame,.7,0,frame)
                cv2.putText(frame,"!!! SOS !!!",(w//2-140,h//2),
                            cv2.FONT_HERSHEY_DUPLEX,2.2,WHITE,5)

            for i,e in enumerate(sos_log[-3:]):
                cv2.putText(frame,e,(10,h-70+i*22),cv2.FONT_HERSHEY_SIMPLEX,.42,(0,220,220),1)
            cv2.putText(frame,"Q=Quit S=SOS R=Reset",(w-215,h-12),
                        cv2.FONT_HERSHEY_SIMPLEX,.45,(180,180,180),1)

            cv2.imshow("StepPrep - Threat Detector",frame)
            key=cv2.waitKey(1)&0xFF
            if key==ord("q"): break
            elif key==ord("s"):
                last_sos=time.time(); sos_count+=1; sos_flash_t=time.time()
                sos_log.append(f"{time.strftime('%H:%M:%S')} - MANUAL SOS")
                print(f"MANUAL SOS #{sos_count}")
            elif key==ord("r"):
                threat_counter.clear(); print("Reset.")

    cap.release(); cv2.destroyAllWindows()
    print(f"Done. SOS alerts: {sos_count}")

if __name__=="__main__":
    main()