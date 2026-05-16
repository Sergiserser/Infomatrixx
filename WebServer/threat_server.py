#!/usr/bin/env python3
"""
StepPrep — Threat Detector Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs the CV2 + MediaPipe threat detector and serves:
  • MJPEG stream  → http://localhost:5050/video
  • Threat status → http://localhost:5050/status  (JSON)
  • Web viewer    → http://localhost:5050          (browser)

The StepPrep React Native/web app connects to this server
and shows the live feed + threat alerts.

Install:
    pip install opencv-python mediapipe flask flask-cors

Run:
    python threat_server.py
    Then open http://localhost:5050 in browser
    OR connect from StepPrep app (same WiFi)
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
import json
import os
import sys
import urllib.request
import webbrowser
from collections import deque
from flask import Flask, Response, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type","Authorization"],
     methods=["GET","POST","PUT","DELETE","OPTIONS"])

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

# ── Config ────────────────────────────────────────────────────────
THREAT_FRAMES    = 6
COLLISION_DIST   = 0.13
SWING_VEL_THRESH = 0.035
SOS_COOLDOWN     = 4.0
PORT             = 5050
NUM_PERSONS      = 2   # detect up to 2 people

# ── Model download ────────────────────────────────────────────────
MODEL_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mp_models")
POSE_MODEL = os.path.join(MODEL_DIR, "pose_landmarker_lite.task")
HAND_MODEL = os.path.join(MODEL_DIR, "hand_landmarker.task")
POSE_URL   = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
HAND_URL   = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

def download_model(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return
    print(f"  Downloading {os.path.basename(path)}...")
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
        print(f"\n  ERROR: {e}")
        sys.exit(1)

# ── New MediaPipe Tasks API ───────────────────────────────────────
vision      = mp.tasks.vision
BaseOptions = mp.tasks.BaseOptions
RunningMode = vision.RunningMode
PoseLandmarker        = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
HandLandmarker        = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions

# Pose landmark indices
NOSE=0; L_SH=11; R_SH=12; L_EL=13; R_EL=14; L_WR=15; R_WR=16

# ── Colours ───────────────────────────────────────────────────────
GREEN  = (0, 210, 90)
RED    = (0, 40, 210)
ORANGE = (0, 160, 255)
WHITE  = (255, 255, 255)
BLUE   = (210, 90, 0)

# ── Shared state (thread-safe via lock) ───────────────────────────
lock         = threading.Lock()
frame_buffer = None
status_data  = {
    "threats":    [],
    "confirmed":  [],
    "sos_count":  0,
    "sos_active": False,
    "sos_reason": "",
    "last_sos":   0,
    "running":    False,
    "fps":        0,
    "away_mode":  False,
    "away_alert": False,
    "people_count": 0,
    "motion_level": 0,
}
sos_log      = []
snapshots    = []   # list of {"file","time","reason"}

SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
os.makedirs(SNAP_DIR, exist_ok=True)

# Away mode config
away_state = {
    "active":           False,
    "bg_frame":         None,    # background for motion detection
    "person_first_seen": {},     # person_id -> timestamp (loiter detection)
    "motion_cooldown":   0,
    "alert_cooldown":    0,
    "motion_threshold":  2500,   # pixel diff sum to count as motion
    "loiter_seconds":    8,      # seconds before loiter alert
    "zones":             [],     # list of (x1,y1,x2,y2) normalised alert zones
}


# ══════════════════════════════════════════════════════════════════
#  DETECTION LOGIC (same as threat_detector.py)
# ══════════════════════════════════════════════════════════════════

def dist(a, b):
    return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2)

def angle_3pts(a, b, c):
    ba = np.array([a.x-b.x, a.y-b.y])
    bc = np.array([c.x-b.x, c.y-b.y])
    cos = np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-6)
    return math.degrees(math.acos(np.clip(cos,-1,1)))

def analyse_hand(lms):
    # lms = plain list of landmarks (new Tasks API)
    tips = [4,8,12,16,20]
    pips = [3,7,11,15,19]
    ext  = []
    thumb_ext = lms[4].x < lms[3].x if lms[0].x < lms[9].x else lms[4].x > lms[3].x
    ext.append(thumb_ext)
    for tip,pip in zip(tips[1:],pips[1:]):
        ext.append(lms[tip].y < lms[pip].y)
    return {
        "is_fist": not any(ext[1:]),
        "is_gun":  ext[1] and not ext[2] and not ext[3] and not ext[4],
        "wrist":   lms[0], "index_tip": lms[8],
    }

def analyse_pose(lms):
    # Use numeric indices — works with new mediapipe Tasks API
    # NOSE=0, L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16
    nose = lms[0]
    l_sh = lms[11]; r_sh = lms[12]
    l_el = lms[13]; r_el = lms[14]
    l_wr = lms[15]; r_wr = lms[16]
    bw   = math.sqrt((l_sh.x-r_sh.x)**2+(l_sh.y-r_sh.y)**2)
    return {
        "l_wrist": l_wr, "r_wrist": r_wr,
        "l_elbow": l_el, "r_elbow": r_el,
        "l_shoulder": l_sh, "r_shoulder": r_sh,
        "nose": nose,
        "l_wrist_raise": l_sh.y - l_wr.y,
        "r_wrist_raise": r_sh.y - r_wr.y,
        "l_arm_angle":  angle_3pts(l_sh, l_el, l_wr),
        "r_arm_angle":  angle_3pts(r_sh, r_el, r_wr),
        "l_elbow_flare": abs(l_el.x-l_sh.x)/(bw+1e-6),
        "r_elbow_flare": abs(r_el.x-r_sh.x)/(bw+1e-6),
        "body_width": bw,
        "shoulder_cx": (l_sh.x+r_sh.x)/2,
        "shoulder_cy": (l_sh.y+r_sh.y)/2,
    }

threat_counter = {}

def tick(key, detected):
    threat_counter[key] = threat_counter.get(key,0)+(1 if detected else -1)
    threat_counter[key] = max(0, threat_counter[key])
    return threat_counter[key] >= THREAT_FRAMES

def get_threats(pose_data, hand_list, prev_wrists):
    found = []

    # Fist collision
    fists = [h for h in hand_list if h["is_fist"]]
    for f in fists:
        if dist(f["wrist"], pose_data["nose"]) < COLLISION_DIST*1.4:
            found.append("FIST_FACE")
        for s in ["l_shoulder","r_shoulder"]:
            if dist(f["wrist"], pose_data[s]) < COLLISION_DIST:
                found.append("FIST_BODY")

    # Two fists colliding
    if len(fists) >= 2:
        if dist(fists[0]["wrist"], fists[1]["wrist"]) < COLLISION_DIST*0.7:
            found.append("FIST_FIST")

    # Gun pose
    for h in hand_list:
        if h["is_gun"]:
            found.append("GUN_POSE")

    # Arm swing
    lw = pose_data["l_wrist"]; rw = pose_data["r_wrist"]
    if prev_wrists:
        pl,pr = prev_wrists[-1]
        lv = math.sqrt((lw.x-pl.x)**2+(lw.y-pl.y)**2)
        rv = math.sqrt((rw.x-pr.x)**2+(rw.y-pr.y)**2)
        if lv > SWING_VEL_THRESH and pose_data["l_wrist_raise"] > 0.05:
            found.append("ARM_SWING")
        if rv > SWING_VEL_THRESH and pose_data["r_wrist_raise"] > 0.05:
            found.append("ARM_SWING")

    # Threatening stance
    lwr = pose_data["l_wrist_raise"]; rwr = pose_data["r_wrist_raise"]
    lf  = pose_data["l_elbow_flare"]; rf  = pose_data["r_elbow_flare"]
    if lwr>0.08 and rwr>0.08 and lf>0.4 and rf>0.4:
        found.append("THREAT_STANCE")
    if lwr>0.1 and lf>0.6 and pose_data["l_arm_angle"]>140:
        found.append("PUNCH")
    if rwr>0.1 and rf>0.6 and pose_data["r_arm_angle"]>140:
        found.append("PUNCH")

    return found


# ══════════════════════════════════════════════════════════════════
#  CAMERA THREAD
# ══════════════════════════════════════════════════════════════════

LABELS = {
    "FIST_FACE":         "FIST → FACE",
    "FIST_BODY":         "FIST → BODY",
    "FIST_FIST":         "FIST COLLISION",
    "GUN_POSE":          "GUN POSE DETECTED",
    "ARM_SWING":         "AGGRESSIVE SWING",
    "THREAT_STANCE":     "THREATENING STANCE",
    "PUNCH":             "PUNCH MOTION",
    "PERSON_COLLISION":  "PERSONS TOO CLOSE",
    # Away mode
    "INTRUDER":          "⚠ INTRUDER DETECTED",
    "MOTION":            "⚠ MOTION DETECTED",
    "LOITER":            "⚠ PERSON LOITERING",
    "ZONE_BREACH":       "⚠ RESTRICTED ZONE BREACHED",
}

# ── Away mode detection ───────────────────────────────────────────
def detect_away(frame, pose_list, w, h):
    """Run intruder/motion detection. Returns list of threat keys + annotated frame."""
    found = []
    now   = time.time()
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray  = cv2.GaussianBlur(gray, (21,21), 0)

    # ── Background subtraction / motion ──────────────────────────
    if away_state["bg_frame"] is None:
        away_state["bg_frame"] = gray.copy().astype("float")
    else:
        cv2.accumulateWeighted(gray, away_state["bg_frame"], 0.05)

    bg    = cv2.convertScaleAbs(away_state["bg_frame"])
    diff  = cv2.absdiff(bg, gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    motion_px = int(np.sum(thresh) / 255)

    with lock:
        status_data["motion_level"] = motion_px

    if motion_px > away_state["motion_threshold"] and now > away_state["motion_cooldown"]:
        found.append("MOTION")
        away_state["motion_cooldown"] = now + 3.0
        # Draw motion contours
        cnts,_ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) > 800:
                x,y,bw,bh = cv2.boundingRect(c)
                cv2.rectangle(frame,(x,y),(x+bw,y+bh),ORANGE,1)

    # ── Person detection = intruder ───────────────────────────────
    if pose_list:
        found.append("INTRUDER")
        for pi, pd in enumerate(pose_list):
            nx = int(pd["nose"].x * w)
            ny = int(pd["nose"].y * h)
            # Loiter check
            pid = f"p{pi}"
            if pid not in away_state["person_first_seen"]:
                away_state["person_first_seen"][pid] = now
            elif now - away_state["person_first_seen"][pid] > away_state["loiter_seconds"]:
                found.append("LOITER")
            # Draw intruder box
            bw2 = int(pd["body_width"] * w * 1.1)
            cv2.rectangle(frame,
                (max(0,nx-bw2), max(0,ny-bw2)),
                (min(w,nx+bw2), min(h,ny+bw2*3)),
                RED, 2)
            cv2.putText(frame, f"INTRUDER P{pi+1}",
                (max(0,nx-bw2), max(0,ny-bw2-10)),
                cv2.FONT_HERSHEY_DUPLEX, .7, RED, 2)
    else:
        away_state["person_first_seen"].clear()

    # ── Zone breach detection ─────────────────────────────────────
    for zi,(zx1,zy1,zx2,zy2) in enumerate(away_state["zones"]):
        px1=int(zx1*w); py1=int(zy1*h); px2=int(zx2*w); py2=int(zy2*h)
        cv2.rectangle(frame,(px1,py1),(px2,py2),(0,255,255),2)
        cv2.putText(frame,f"ZONE {zi+1}",(px1+4,py1+18),
                    cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),1)
        for pd in pose_list:
            nx = pd["nose"].x; ny2 = pd["nose"].y
            if zx1 < nx < zx2 and zy1 < ny2 < zy2:
                found.append("ZONE_BREACH")
                cv2.rectangle(frame,(px1,py1),(px2,py2),RED,3)

    return found

def camera_thread():
    global frame_buffer, status_data, sos_log

    # Draw connections
    POSE_CONN = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24)]
    HAND_CONN = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),
                 (10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),
                 (18,19),(19,20),(5,9),(9,13),(13,17)]
    PERSON_COLS = [GREEN, (0,200,255)]   # colour per person

    def draw_pose(frame, lms, w, h, col):
        pts = [(int(l.x*w),int(l.y*h)) for l in lms]
        for a,b in POSE_CONN:
            if a<len(pts) and b<len(pts): cv2.line(frame,pts[a],pts[b],col,2)
        for i in [0,11,12,13,14,15,16]:
            if i<len(pts): cv2.circle(frame,pts[i],4,BLUE,-1)

    def draw_hand(frame, lms, w, h, col):
        pts = [(int(l.x*w),int(l.y*h)) for l in lms]
        for a,b in HAND_CONN: cv2.line(frame,pts[a],pts[b],col,2)
        for p in pts: cv2.circle(frame,p,3,WHITE,-1)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    pose_opts = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_MODEL),
        running_mode=RunningMode.VIDEO,
        num_poses=NUM_PERSONS,
        min_pose_detection_confidence=0.55,
        min_pose_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )
    hand_opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL),
        running_mode=RunningMode.VIDEO,
        num_hands=NUM_PERSONS * 2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.5,
    )

    prev_wrists_list = [deque(maxlen=5) for _ in range(NUM_PERSONS)]
    fps_q = deque(maxlen=20)
    last_sos = 0
    frame_ts = 0

    with lock:
        status_data["running"] = True

    with PoseLandmarker.create_from_options(pose_opts) as pose_det,          HandLandmarker.create_from_options(hand_opts) as hand_det:

      while True:
        t0 = time.time()
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue

        frame    = cv2.flip(frame, 1)
        h, w     = frame.shape[:2]
        frame_ts += int(1000/30)

        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        pose_res = pose_det.detect_for_video(mp_img, frame_ts)
        hand_res = hand_det.detect_for_video(mp_img, frame_ts)

        all_threats = []
        confirmed   = []
        pose_list   = []
        hand_list   = []

        # ── Draw + analyse each detected person ───────────────────
        for pi, plms in enumerate(pose_res.pose_landmarks or []):
            col = PERSON_COLS[pi % len(PERSON_COLS)]
            draw_pose(frame, plms, w, h, col)
            pd = analyse_pose(plms)
            pose_list.append(pd)

            # Person ID label
            nx = int(pd["nose"].x * w)
            ny = int(pd["nose"].y * h)
            cv2.putText(frame, f"P{pi+1}", (nx-12, ny-30),
                        cv2.FONT_HERSHEY_DUPLEX, .7, col, 2)
            # Collision zone
            cr = int(pd["body_width"] * w * 0.55)
            cv2.circle(frame, (nx, ny), cr, col, 1)

        # ── Draw + analyse each detected hand ─────────────────────
        for hi, hlms in enumerate(hand_res.hand_landmarks or []):
            col = ORANGE if hi % 2 == 0 else (0,200,255)
            draw_hand(frame, hlms, w, h, col)
            ha = analyse_hand(hlms)
            hand_list.append(ha)
            wx = int(ha["wrist"].x * w); wy = int(ha["wrist"].y * h)
            if ha["is_fist"]:
                cv2.rectangle(frame,(wx-28,wy-32),(wx+66,wy+6),(0,0,180),-1)
                cv2.putText(frame,"FIST",(wx-24,wy-8),cv2.FONT_HERSHEY_DUPLEX,.65,WHITE,2)
            elif ha["is_gun"]:
                cv2.rectangle(frame,(wx-28,wy-32),(wx+130,wy+6),(0,60,180),-1)
                cv2.putText(frame,"GUN POSE",(wx-24,wy-8),cv2.FONT_HERSHEY_DUPLEX,.65,WHITE,2)

        # ── Away mode processing ──────────────────────────────────────
        with lock:
            away_on = status_data["away_mode"]
            status_data["people_count"] = len(pose_list)

        if away_on:
            away_threats = detect_away(frame, pose_list, w, h)
            all_threats.extend(away_threats)
            # Away mode overlay
            cv2.rectangle(frame,(0,h-36),(w,h),(30,0,100),-1)
            cv2.putText(frame,"AWAY MODE — ARMED",(12,h-10),
                        cv2.FONT_HERSHEY_DUPLEX,.7,(180,100,255),2)

        # ── Only detect threats when 2+ people are in frame ─────────
        two_people = len(pose_list) >= 2

        if two_people:
            # Cross-person checks only
            for i in range(len(pose_list)):
                for j in range(i+1, len(pose_list)):
                    p1 = pose_list[i]
                    p2 = pose_list[j]

                    # Too close together
                    d = dist(p1["nose"], p2["nose"])
                    if d < 0.22:
                        all_threats.append("PERSON_COLLISION")

                    # Fist of any hand near face/body of the OTHER person
                    for h in hand_list:
                        if h["is_fist"]:
                            # Check against p2 landmarks
                            if dist(h["wrist"], p2["nose"]) < COLLISION_DIST * 1.4:
                                all_threats.append("FIST_FACE")
                            for s in ["l_shoulder","r_shoulder"]:
                                if dist(h["wrist"], p2[s]) < COLLISION_DIST:
                                    all_threats.append("FIST_BODY")
                            # Check against p1 landmarks
                            if dist(h["wrist"], p1["nose"]) < COLLISION_DIST * 1.4:
                                all_threats.append("FIST_FACE")
                            for s in ["l_shoulder","r_shoulder"]:
                                if dist(h["wrist"], p1[s]) < COLLISION_DIST:
                                    all_threats.append("FIST_BODY")

                    # Gun pose pointed at someone
                    for h in hand_list:
                        if h["is_gun"]:
                            all_threats.append("GUN_POSE")

                    # Aggressive arm swing / punch from either person
                    for pi, pd in enumerate(pose_list):
                        pw = prev_wrists_list[pi]
                        lw = pd["l_wrist"]; rw = pd["r_wrist"]
                        if pw:
                            pl, pr = pw[-1]
                            lv = dist(lw, pl); rv = dist(rw, pr)
                            if lv > SWING_VEL_THRESH and pd["l_wrist_raise"] > 0.05:
                                all_threats.append("ARM_SWING")
                            if rv > SWING_VEL_THRESH and pd["r_wrist_raise"] > 0.05:
                                all_threats.append("ARM_SWING")
                            lf = pd["l_elbow_flare"]; rf = pd["r_elbow_flare"]
                            if pd["l_wrist_raise"]>0.1 and lf>0.6 and pd["l_arm_angle"]>140:
                                all_threats.append("PUNCH")
                            if pd["r_wrist_raise"]>0.1 and rf>0.6 and pd["r_arm_angle"]>140:
                                all_threats.append("PUNCH")
                        pw.append((lw, rw))

        else:
            # Only one person — still track wrist history but no SOS
            for pi, pd in enumerate(pose_list):
                pw = prev_wrists_list[pi]
                pw.append((pd["l_wrist"], pd["r_wrist"]))
            # Reset all threat counters so they don't carry over
            threat_counter.clear()

        # Confirm over N frames (only meaningful with 2 people)
        for th in set(all_threats):
            if tick(th, True):
                confirmed.append(th)
        for k in list(threat_counter):
            if k not in all_threats:
                tick(k, False)

        # SOS — fires when 2 people + threat (normal) OR away mode + intruder
        sos_active = False
        sos_reason = ""
        sos_count  = status_data["sos_count"]
        away_trigger = away_on and any(t in confirmed for t in ["INTRUDER","LOITER","ZONE_BREACH","MOTION"])
        if (confirmed and (two_people or away_trigger)) and time.time() - last_sos > SOS_COOLDOWN:
            last_sos   = time.time()
            sos_count += 1
            sos_active = True
            sos_reason = " | ".join(LABELS.get(c,c) for c in confirmed[:2])
            sos_log.append({"time": time.strftime("%H:%M:%S"), "reason": sos_reason})
            print(f"SOS #{sos_count}: {sos_reason}")
            # Save snapshot
            snap_name = f"snap_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            snap_path = os.path.join(SNAP_DIR, snap_name)
            cv2.imwrite(snap_path, frame)
            snapshots.append({"file": snap_name, "time": time.strftime("%H:%M:%S"), "reason": sos_reason})
            print(f"  Snapshot saved: {snap_name}")

        # Draw status overlay
        bar_col = (0,30,180) if (confirmed and two_people) else (0,110,0)
        cv2.rectangle(frame,(0,0),(w,52),bar_col,-1)
        pcount = f"[{len(pose_list)}P/{len(hand_list)}H]"
        if confirmed and (two_people or away_trigger):
            status_txt = "SOS! " + " | ".join(LABELS.get(c,c) for c in confirmed[:2])
        elif away_on and not pose_list:
            status_txt = f"AWAY MODE — Watching... {pcount}"
        elif not two_people and not away_on:
            status_txt = f"Waiting for 2 people... {pcount}"
        else:
            status_txt = f"OK - Monitoring {pcount}"
        cv2.putText(frame,status_txt,(12,36),cv2.FONT_HERSHEY_DUPLEX,.8,WHITE,2)

        fps_q.append(1.0/max(time.time()-t0,1e-6))
        fps = sum(fps_q)/len(fps_q)
        cv2.putText(frame,f"FPS:{fps:.0f}",(w-90,36),cv2.FONT_HERSHEY_SIMPLEX,.6,WHITE,1)

        if sos_active:
            ov = frame.copy()
            cv2.rectangle(ov,(0,0),(w,h),(0,0,180),-1)
            cv2.addWeighted(ov,.3,frame,.7,0,frame)
            cv2.putText(frame,"!!! SOS !!!",(w//2-130,h//2),cv2.FONT_HERSHEY_DUPLEX,2.2,WHITE,5)

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        raw = buf.tobytes()
        with lock:
            frame_buffer = raw
            status_data.update({
                "threats":    all_threats,
                "confirmed":  confirmed,
                "sos_count":  sos_count,
                "sos_active": sos_active,
                "sos_reason": sos_reason,
                "last_sos":   last_sos,
                "fps":        round(fps,1),
                "away_alert": bool(away_trigger and confirmed),
            })
        new_frame_event.set()

    cap.release()
    pose.close()
    hands.close()


# ══════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════

# Event to signal a new frame is ready
new_frame_event = threading.Event()

def gen_frames():
    last_buf = None
    while True:
        # Wait up to 1s for a new frame
        new_frame_event.wait(timeout=1.0)
        new_frame_event.clear()
        with lock:
            buf = frame_buffer
        if buf is None or buf is last_buf:
            continue
        last_buf = buf
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf + b'\r\n')


@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    with lock:
        s = dict(status_data)
    s["sos_log"] = sos_log[-10:]
    return jsonify(s)


@app.route('/')
def index():
    return render_template_string(WEB_PAGE)

# ── Proxy for Expo web app (same-origin workaround) ───────────────
@app.route('/api/status')
def api_status():
    """Same as /status but with explicit CORS for Expo web"""
    with lock:
        s = dict(status_data)
    s["sos_log"] = sos_log[-20:]
    resp = jsonify(s)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.route('/api/away', methods=['POST','OPTIONS'])
def api_away():
    if request.method == 'OPTIONS':
        resp = app.response_class(status=200)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        return resp
    data = request.get_json(force=True)
    with lock:
        status_data["away_mode"] = bool(data.get("active", False))
        away_state["bg_frame"] = None
        away_state["person_first_seen"].clear()
    resp = jsonify({"ok": True, "away_mode": status_data["away_mode"]})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/snapshots')
def api_snapshots():
    resp = jsonify({"snapshots": snapshots[-20:]})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/full_log')
def api_full_log():
    resp = jsonify({"log": sos_log, "total": len(sos_log)})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/log')
def log_page():
    return render_template_string(LOG_PAGE)

@app.route('/full_log')
def full_log():
    return jsonify({"log": sos_log, "total": len(sos_log)})

@app.route('/clear_log', methods=['POST'])
def clear_log():
    global sos_log
    sos_log = []
    return jsonify({"ok": True})

@app.route('/away', methods=['POST'])
def toggle_away():
    data = request.get_json(force=True)
    with lock:
        status_data["away_mode"] = bool(data.get("active", False))
        away_state["bg_frame"] = None  # reset background on toggle
        away_state["person_first_seen"].clear()
    state = "ARMED" if status_data["away_mode"] else "DISARMED"
    print(f"Away mode: {state}")
    return jsonify({"ok": True, "away_mode": status_data["away_mode"]})

@app.route('/snapshots')
def get_snapshots():
    return jsonify({"snapshots": snapshots[-20:]})

@app.route('/snapshots/<filename>')
def get_snapshot_img(filename):
    from flask import send_from_directory
    return send_from_directory(SNAP_DIR, filename)

@app.route('/zones', methods=['POST'])
def set_zones():
    data = request.get_json(force=True)
    away_state["zones"] = data.get("zones", [])
    return jsonify({"ok": True, "zones": len(away_state["zones"])})


# ══════════════════════════════════════════════════════════════════
#  BUILT-IN WEB VIEWER (shown at http://localhost:5050)
# ══════════════════════════════════════════════════════════════════

LOG_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>StepPrep — Event Log</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0d14;color:#ebecf8;font-family:system-ui,sans-serif;min-height:100vh}
header{background:#1a1a1a;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #2a3150}
header h1{font-size:18px;font-weight:700}
.nav-links{display:flex;gap:12px}
.nav-links a{color:#4696ff;text-decoration:none;font-size:13px;font-weight:500;padding:4px 12px;border:1px solid #2a3150;border-radius:8px}
.nav-links a:hover{background:#141720}
.nav-links a.active{background:#1c2030;color:#fff;border-color:#4696ff}
.wrap{max-width:900px;margin:0 auto;padding:20px}
.stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.stat-box{background:#141720;border:1px solid #2a3150;border-radius:12px;padding:16px;text-align:center}
.stat-val{font-size:28px;font-weight:800}
.stat-lab{font-size:11px;color:#6e7894;margin-top:4px;text-transform:uppercase;letter-spacing:.05em}
.log-table{background:#141720;border:1px solid #2a3150;border-radius:12px;overflow:hidden}
.log-header{display:grid;grid-template-columns:90px 1fr 120px;padding:10px 16px;background:#1c2030;border-bottom:1px solid #2a3150;font-size:11px;font-weight:600;color:#6e7894;text-transform:uppercase;letter-spacing:.05em}
.log-row{display:grid;grid-template-columns:90px 1fr 120px;padding:11px 16px;border-bottom:1px solid #141720;font-size:13px;transition:background .1s}
.log-row:last-child{border:none}
.log-row:hover{background:#1c2030}
.log-row:nth-child(even){background:#151b28}
.time-col{color:#4696ff;font-weight:600;font-family:monospace}
.threat-col{color:#ebecf8}
.badge-col{}
.badge{font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px}
.badge-sos{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
.badge-manual{background:rgba(70,150,255,.15);color:#4696ff;border:1px solid rgba(70,150,255,.3)}
.empty{text-align:center;padding:60px 20px;color:#6e7894;font-size:14px}
.chart-wrap{background:#141720;border:1px solid #2a3150;border-radius:12px;padding:16px;margin-bottom:20px}
.chart-wrap h3{font-size:12px;font-weight:600;color:#6e7894;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px}
.bar-chart{display:flex;align-items:flex-end;gap:6px;height:80px}
.bar{flex:1;border-radius:4px 4px 0 0;background:#4696ff;min-width:20px;transition:height .3s}
.bar-label{font-size:10px;color:#6e7894;text-align:center;margin-top:4px}
.clear-btn{background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit}
.clear-btn:hover{background:#dc2626}
.filter-row{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.filter-btn{background:#1c2030;border:1px solid #2a3150;color:#6e7894;border-radius:8px;padding:5px 14px;font-size:12px;cursor:pointer;font-family:inherit;transition:all .15s}
.filter-btn.active{background:#4696ff;border-color:#4696ff;color:#fff}
</style>
</head>
<body>
<header>
  <h1>📋 StepPrep — Event Log</h1>
  <div class="nav-links">
    <a href="/">📹 Live Feed</a>
    <a href="/log" class="active">📋 Log</a>
  </div>
</header>
<div class="wrap">

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat-box">
      <div class="stat-val" id="total-sos" style="color:#ef4444">0</div>
      <div class="stat-lab">Total SOS Alerts</div>
    </div>
    <div class="stat-box">
      <div class="stat-val" id="total-events" style="color:#e68c1e">0</div>
      <div class="stat-lab">Total Events</div>
    </div>
    <div class="stat-box">
      <div class="stat-val" id="last-event" style="color:#28c878;font-size:16px">—</div>
      <div class="stat-lab">Last Event</div>
    </div>
  </div>

  <!-- Threat breakdown chart -->
  <div class="chart-wrap">
    <h3>Threat Breakdown</h3>
    <div id="chart" class="bar-chart"></div>
    <div id="chart-labels" style="display:flex;gap:6px;margin-top:4px"></div>
  </div>

  <!-- Filter + Clear -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <div class="filter-row" id="filters">
      <button class="filter-btn active" onclick="setFilter('all',this)">All</button>
      <button class="filter-btn" onclick="setFilter('FIST',this)">Fist</button>
      <button class="filter-btn" onclick="setFilter('GUN',this)">Gun Pose</button>
      <button class="filter-btn" onclick="setFilter('PUNCH',this)">Punch</button>
      <button class="filter-btn" onclick="setFilter('SWING',this)">Arm Swing</button>
      <button class="filter-btn" onclick="setFilter('PERSON',this)">Collision</button>
      <button class="filter-btn" onclick="setFilter('MANUAL',this)">Manual</button>
    </div>
    <button class="clear-btn" onclick="clearLog()">🗑 Clear Log</button>
  </div>

  <!-- Log table -->
  <div class="log-table">
    <div class="log-header">
      <div>Time</div>
      <div>Threat / Reason</div>
      <div>Type</div>
    </div>
    <div id="log-body"></div>
  </div>
</div>

<script>
let allLog = [];
let currentFilter = 'all';

const LABELS = {
  FIST_FACE:'Fist → Face', FIST_BODY:'Fist → Body',
  FIST_FIST:'Fist Collision', GUN_POSE:'Gun Pose Detected',
  ARM_SWING:'Aggressive Arm Swing', THREAT_STANCE:'Threatening Stance',
  PUNCH:'Punch Motion', PERSON_COLLISION:'Persons Too Close',
};

function setFilter(f, btn) {
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderTable();
}

function renderTable() {
  const body = document.getElementById('log-body');
  let rows = allLog;
  if (currentFilter !== 'all') {
    rows = allLog.filter(e => e.reason.toUpperCase().includes(currentFilter));
  }
  if (!rows.length) {
    body.innerHTML = '<div class="empty">No events match this filter</div>';
    return;
  }
  body.innerHTML = [...rows].reverse().map((e,i) => {
    const isManual = e.reason.includes('MANUAL');
    return `<div class="log-row">
      <div class="time-col">${e.time}</div>
      <div class="threat-col">${e.reason}</div>
      <div class="badge-col"><span class="badge ${isManual?'badge-manual':'badge-sos'}">${isManual?'Manual':'Auto'}</span></div>
    </div>`;
  }).join('');
}

function renderChart() {
  const counts = {};
  allLog.forEach(e => {
    const key = e.reason.split('|')[0].trim().split(' ')[0];
    counts[key] = (counts[key]||0) + 1;
  });
  const keys = Object.keys(counts);
  const max  = Math.max(...Object.values(counts), 1);
  const chart  = document.getElementById('chart');
  const labels = document.getElementById('chart-labels');
  chart.innerHTML  = keys.map(k => `<div class="bar" style="height:${counts[k]/max*100}%;background:#4696ff" title="${k}: ${counts[k]}"></div>`).join('');
  labels.innerHTML = keys.map(k => `<div style="flex:1;font-size:10px;color:#6e7894;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${k}</div>`).join('');
}

async function fetchLog() {
  try {
    const r = await fetch('/full_log');
    const d = await r.json();
    allLog = d.log || [];
    const sos = allLog.filter(e=>!e.reason.includes('MANUAL')).length;
    document.getElementById('total-sos').textContent    = sos;
    document.getElementById('total-events').textContent = allLog.length;
    document.getElementById('last-event').textContent   = allLog.length ? allLog[allLog.length-1].time : '—';
    renderTable();
    renderChart();
  } catch(e) { console.error(e); }
}

async function clearLog() {
  if (!confirm('Clear all log entries?')) return;
  await fetch('/clear_log', {method:'POST'});
  allLog = [];
  renderTable(); renderChart();
  document.getElementById('total-sos').textContent    = 0;
  document.getElementById('total-events').textContent = 0;
  document.getElementById('last-event').textContent   = '—';
}

setInterval(fetchLog, 2000);
fetchLog();
</script>
</body>
</html>'''

WEB_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>StepPrep — Threat Detector</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0d14;color:#ebecf8;font-family:system-ui,sans-serif;min-height:100vh}
header{background:#1a1a1a;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #2a3150}
header h1{font-size:18px;font-weight:700}
header .badge{font-size:12px;background:#2a3150;padding:4px 10px;border-radius:20px}
.layout{display:flex;gap:16px;padding:16px;flex-wrap:wrap}
.cam-wrap{flex:2;min-width:300px}
.cam-wrap img{width:100%;border-radius:12px;border:2px solid #2a3150;display:block}
.side{flex:1;min-width:240px;display:flex;flex-direction:column;gap:12px}
.card{background:#141720;border:1px solid #2a3150;border-radius:12px;padding:14px}
.card h3{font-size:12px;font-weight:600;color:#6e7894;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}
.status-dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px}
.dot-ok{background:#28c878} .dot-threat{background:#ef4444} .dot-off{background:#6e7894}
.threat-row{background:#1c2030;border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:13px;border-left:3px solid #ef4444}
.sos-box{background:#1a0808;border:2px solid #ef4444;border-radius:12px;padding:16px;text-align:center}
.sos-box.active{background:#2a0505;animation:pulse .5s infinite alternate}
@keyframes pulse{from{border-color:#ef4444}to{border-color:#ff8080}}
.sos-num{font-size:36px;font-weight:800;color:#ef4444}
.sos-label{font-size:12px;color:#6e7894;margin-top:4px}
.log-item{font-size:11px;color:#6e7894;padding:5px 0;border-bottom:1px solid #2a3150}
.log-item .time{color:#4696ff;margin-right:8px;font-weight:600}
.fps-badge{font-size:11px;color:#6e7894;margin-top:8px;text-align:right}
.connect-info{font-size:12px;color:#4696ff;background:#102060;border-radius:8px;padding:10px;margin-top:8px;line-height:1.6}
.green{color:#28c878} .red{color:#ef4444} .orange{color:#e68c1e}
</style>
</head>
<body>
<header>
  <h1>🛡 StepPrep — Threat Detector</h1>
  <div style="display:flex;align-items:center;gap:12px">
    <a href="/" style="color:#4696ff;text-decoration:none;font-size:13px;font-weight:500;padding:4px 12px;border:1px solid #4696ff;border-radius:8px;background:#1c2030">📹 Live</a>
    <a href="/log" style="color:#6e7894;text-decoration:none;font-size:13px;font-weight:500;padding:4px 12px;border:1px solid #2a3150;border-radius:8px">📋 Log</a>
    <span class="badge" id="run-badge">Starting...</span>
  </div>
</header>
<div class="layout">
  <!-- Camera feed -->
  <div class="cam-wrap">
    <img src="/video" alt="Live feed">
    <div class="fps-badge" id="fps">FPS: —</div>
  </div>

  <!-- Side panel -->
  <div class="side">

    <!-- Status -->
    <div class="card">
      <h3>Status</h3>
      <div style="display:flex;align-items:center;font-size:15px;font-weight:600" id="status-txt">
        <span class="status-dot dot-off" id="status-dot"></span>
        Connecting...
      </div>
    </div>

    <!-- SOS -->
    <div class="sos-box" id="sos-box">
      <div class="sos-num" id="sos-count">0</div>
      <div class="sos-label">SOS Alerts Fired</div>
      <div style="font-size:12px;color:#ef4444;margin-top:8px;min-height:16px" id="sos-reason"></div>
    </div>

    <!-- Active threats -->
    <div class="card">
      <h3>Active Threats</h3>
      <div id="threat-list"><div style="font-size:13px;color:#6e7894">None detected</div></div>
    </div>

    <!-- Log -->
    <div class="card">
      <h3>SOS Log</h3>
      <div id="sos-log"><div style="font-size:12px;color:#6e7894">No events yet</div></div>
    </div>

    <!-- Away Mode -->
    <div class="card" id="away-card">
      <h3>Away Mode</h3>
      <div style="font-size:12px;color:#6e7894;margin-bottom:10px">Arms the camera when you leave home. Detects any person, motion, or zone breach.</div>
      <button id="away-btn" onclick="toggleAway()" style="width:100%;padding:12px;border-radius:10px;border:none;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;background:#2a3150;color:#ebecf8;transition:all .2s">
        🏠  ARM Away Mode
      </button>
      <div id="away-status" style="font-size:12px;color:#6e7894;text-align:center;margin-top:8px">Disarmed — you are home</div>
      <div style="margin-top:12px">
        <div style="font-size:11px;color:#6e7894;margin-bottom:6px">MOTION LEVEL</div>
        <div style="background:#1c2030;border-radius:4px;height:8px;overflow:hidden">
          <div id="motion-bar" style="height:100%;width:0%;background:#e68c1e;border-radius:4px;transition:width .3s"></div>
        </div>
        <div style="font-size:10px;color:#6e7894;margin-top:3px" id="motion-val">0 px</div>
      </div>
      <div style="margin-top:12px">
        <div style="font-size:11px;color:#6e7894;margin-bottom:6px">PEOPLE IN FRAME</div>
        <div id="people-count" style="font-size:22px;font-weight:700;color:#ebecf8">0</div>
      </div>
    </div>

    <!-- Snapshots -->
    <div class="card">
      <h3>Snapshots</h3>
      <div id="snap-list"><div style="font-size:12px;color:#6e7894">No snapshots yet</div></div>
    </div>

    <!-- Connect from app -->
    <div class="card">
      <h3>Connect from StepPrep App</h3>
      <div class="connect-info" id="connect-info">
        Same WiFi network:<br>
        Video: <b>http://YOUR_IP:5050/video</b><br>
        Status: <b>http://YOUR_IP:5050/status</b><br>
        <span style="color:#6e7894;font-size:11px">Replace YOUR_IP with your PC's IP address</span>
      </div>
    </div>
  </div>
</div>

<script>
const LABELS = {
  FIST_FACE:    "FIST → FACE",
  FIST_BODY:    "FIST → BODY",
  FIST_FIST:    "FIST COLLISION",
  GUN_POSE:     "GUN POSE DETECTED",
  ARM_SWING:    "AGGRESSIVE ARM SWING",
  THREAT_STANCE:"THREATENING STANCE",
  PUNCH:        "PUNCH MOTION",
};

async function poll() {
  try {
    const r = await fetch("/status");
    const s = await r.json();

    document.getElementById("fps").textContent = "FPS: " + s.fps;
    document.getElementById("run-badge").textContent = s.running ? "● Live" : "○ Offline";
    document.getElementById("sos-count").textContent = s.sos_count;

    const dot  = document.getElementById("status-dot");
    const stxt = document.getElementById("status-txt");
    const sosBox = document.getElementById("sos-box");

    if (s.confirmed.length > 0) {
      dot.className = "status-dot dot-threat";
      stxt.innerHTML = \'<span class="status-dot dot-threat"></span><span class="red">THREAT DETECTED</span>\';
      sosBox.classList.add("active");
    } else {
      dot.className = "status-dot dot-ok";
      stxt.innerHTML = \'<span class="status-dot dot-ok"></span><span class="green">All Clear — Monitoring</span>\';
      sosBox.classList.remove("active");
    }

    document.getElementById("sos-reason").textContent = s.sos_reason || "";

    // Threats
    const tl = document.getElementById("threat-list");
    if (s.confirmed.length === 0) {
      tl.innerHTML = \'<div style="font-size:13px;color:#6e7894">None detected</div>\';
    } else {
      tl.innerHTML = s.confirmed.map(k =>
        `<div class="threat-row">${LABELS[k] || k}</div>`
      ).join("");
    }

    // Log
    const log = document.getElementById("sos-log");
    if (!s.sos_log || s.sos_log.length === 0) {
      log.innerHTML = \'<div style="font-size:12px;color:#6e7894">No events yet</div>\';
    } else {
      log.innerHTML = [...s.sos_log].reverse().slice(0,6).map(e =>
        `<div class="log-item"><span class="time">${e.time}</span>${e.reason}</div>`
      ).join("");
    }

  } catch(e) {
    document.getElementById("status-txt").innerHTML = \'<span class="status-dot dot-off"></span>Disconnected\';
  }
}

let awayArmed = false;

async function toggleAway() {
  awayArmed = !awayArmed;
  await fetch('/away', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({active:awayArmed})});
  updateAwayUI(awayArmed);
}

function updateAwayUI(armed) {
  const btn=document.getElementById('away-btn');
  const st=document.getElementById('away-status');
  const card=document.getElementById('away-card');
  if(!btn) return;
  if (armed) {
    btn.textContent='🔴  DISARM Away Mode';
    btn.style.cssText='width:100%;padding:12px;border-radius:10px;border:2px solid #ef4444;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;background:#5a1010;color:#ff8080';
    st.textContent='Armed — monitoring for intruders'; st.style.color='#ef4444';
    card.style.borderColor='#ef4444';
  } else {
    btn.textContent='🏠  ARM Away Mode';
    btn.style.cssText='width:100%;padding:12px;border-radius:10px;border:none;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;background:#2a3150;color:#ebecf8';
    st.textContent='Disarmed — you are home'; st.style.color='#6e7894';
    card.style.borderColor='#2a3150';
  }
}

async function pollSnaps() {
  try {
    const r=await fetch('/snapshots'); const d=await r.json();
    const sl=document.getElementById('snap-list');
    if(!sl) return;
    if(!d.snapshots.length){sl.innerHTML='<div style="font-size:12px;color:#6e7894">No snapshots yet</div>';return;}
    sl.innerHTML=[...d.snapshots].reverse().slice(0,4).map(s=>`
      <div style="margin-bottom:8px">
        <a href="/snapshots/${s.file}" target="_blank">
          <img src="/snapshots/${s.file}" style="width:100%;border-radius:6px;border:1px solid #2a3150;display:block">
        </a>
        <div style="font-size:10px;color:#4696ff;margin-top:3px">${s.time} — ${s.reason.slice(0,30)}</div>
      </div>`).join('');
  } catch(e){}
}

async function pollAll() {
  await poll();
  try {
    const r=await fetch('/status'); const s=await r.json();
    const mb=document.getElementById('motion-bar');
    const mv=document.getElementById('motion-val');
    const pc=document.getElementById('people-count');
    if(mb){const pct=Math.min(100,(s.motion_level||0)/15000*100);mb.style.width=pct+'%';mb.style.background=pct>60?'#ef4444':pct>30?'#e68c1e':'#4696ff';}
    if(mv) mv.textContent=(s.motion_level||0)+' px';
    if(pc){pc.textContent=s.people_count||0;pc.style.color=(s.people_count||0)>0&&awayArmed?'#ef4444':'#ebecf8';}
    if(s.away_mode!==undefined){awayArmed=s.away_mode;updateAwayUI(awayArmed);}
    document.getElementById('fps').textContent='FPS: '+s.fps+' | People: '+(s.people_count||0);
  } catch(e){}
}

setInterval(pollAll, 800);
setInterval(pollSnaps, 3000);
pollAll(); pollSnaps();
</script>
</body>
</html>'''


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("━" * 52)
    print("  StepPrep — Threat Detector Server")
    print("━" * 52)
    print("  Checking MediaPipe models...")
    download_model(POSE_URL, POSE_MODEL)
    download_model(HAND_URL, HAND_MODEL)
    print("  Models ready.")
    print(f"  Detecting up to {NUM_PERSONS} people.")
    print(f"  Web viewer:  http://localhost:{PORT}")
    print(f"  Video feed:  http://localhost:{PORT}/video")
    print(f"  Status API:  http://localhost:{PORT}/status")
    print("━" * 52)
    print("  Starting camera thread...")

    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()

    time.sleep(2.0)
    print("  Camera running. Auto-opening browser...")
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except: pass

    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
