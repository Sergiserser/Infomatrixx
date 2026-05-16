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
# Face detection uses OpenCV HOG — no model needed
HAND_URL   = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

def download_model(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return
    name = os.path.basename(path)
    print(f"\n  Model missing: {name}")
    print(f"  Google now blocks direct downloads. Download manually:")
    print(f"  URL: {url}")
    print(f"  Save to: {path}")
    print(f"\n  Opening download link in browser...")
    try:
        webbrowser.open(url)
    except: pass
    print(f"  Waiting for {name} to appear in {os.path.dirname(path)} ...")
    # Wait up to 120 seconds for manual download
    for i in range(120):
        time.sleep(1)
        if os.path.exists(path) and os.path.getsize(path) > 10000:
            print(f"  Found {name}! ({os.path.getsize(path)//1024} KB)")
            return
        if i % 10 == 9:
            print(f"  Still waiting... ({i+1}s) — save the file to: {path}")
    print(f"\n  ERROR: {name} not found after 120s.")
    print(f"  Please download it and place at: {path}")
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

    PERSON_COLS = [GREEN, (0,200,255)]   # colour per person
    HAND_CONN = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),
                 (10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),
                 (18,19),(19,20),(5,9),(9,13),(13,17)]

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)   # keep auto-focus on
    print(f"  Camera: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    pose_opts = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_MODEL),
        running_mode=RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.1,   # minimum possible
        min_pose_presence_confidence=0.1,
        min_tracking_confidence=0.1,
        output_segmentation_masks=False,
    )
    hand_opts = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL),
        running_mode=RunningMode.VIDEO,
        num_hands=4,
        min_hand_detection_confidence=0.4,
        min_hand_presence_confidence=0.4,
        min_tracking_confidence=0.3,
    )

    prev_wrists_list = [deque(maxlen=5) for _ in range(NUM_PERSONS)]
    fps_q = deque(maxlen=20)
    last_sos = 0
    frame_ts = 0

    # HOG person detector (built into OpenCV, no model file needed)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    try:
        pose_det = PoseLandmarker.create_from_options(pose_opts)
        hand_det = HandLandmarker.create_from_options(hand_opts)
    except Exception as e:
        print(f"  ERROR creating detectors: {e}")
        with lock:
            status_data["running"] = False
        return

    print("  Detectors ready — streaming...")
    with lock:
        status_data["running"] = True

    while True:
      try:
        t0 = time.time()
        ok, frame = cap.read()
        if not isinstance(ok, bool):
            ok = bool(ok)
        if not ok:
            time.sleep(0.05)
            continue

        frame    = cv2.flip(frame, 1)
        h, w     = frame.shape[:2]
        frame_ts += int(1000/30)

        # Run pose on 640x480 — sweet spot for multi-person
        small = cv2.resize(frame, (640, 480))
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        pose_res = pose_det.detect_for_video(mp_img, frame_ts)
        hand_res = hand_det.detect_for_video(mp_img, frame_ts)

        # HOG person detection — works on partial bodies, no model needed
        hog_frame = cv2.resize(frame, (640, 480))
        hog_rects, _ = hog.detectMultiScale(
            hog_frame, winStride=(8,8), padding=(4,4), scale=1.05,
            useMeanshiftGrouping=False)
        n_hog = len(hog_rects)

        # Draw HOG detections scaled to full frame
        HOG_COLS = [(0,200,255), (255,200,0), (200,0,255)]
        for hi2, (hx,hy,hw2,hh2) in enumerate(hog_rects[:4]):
            hc = HOG_COLS[hi2 % len(HOG_COLS)]
            rx1 = int(hx/640*w); ry1 = int(hy/480*h)
            rx2 = int((hx+hw2)/640*w); ry2 = int((hy+hh2)/480*h)
            cv2.rectangle(frame, (rx1,ry1), (rx2,ry2), hc, 2)
            cv2.putText(frame, f"HOG P{hi2+1}", (rx1+4,ry1+22),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, hc, 2)

        all_threats = []
        confirmed   = []
        pose_list   = []
        hand_list   = []

        # ── Draw + analyse each detected person ───────────────────
        for pi, plms in enumerate(pose_res.pose_landmarks or []):
            col = PERSON_COLS[pi % len(PERSON_COLS)]

            # Draw skeleton scaled to full frame
            pts = [(int(lm.x*w), int(lm.y*h)) for lm in plms]
            for a,b2 in [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(24,26)]:
                if a<len(pts) and b2<len(pts):
                    cv2.line(frame, pts[a], pts[b2], col, 2)
            for i2 in [0,11,12,13,14,15,16,23,24]:
                if i2<len(pts):
                    cv2.circle(frame, pts[i2], 4, col, -1)

            pd = analyse_pose(plms)
            pose_list.append(pd)

            # Bounding box
            xs = [lm.x for lm in plms]
            ys = [lm.y for lm in plms]
            if xs and ys:
                bx1 = max(0,   int(min(xs)*w - 24))
                by1 = max(0,   int(min(ys)*h - 24))
                bx2 = min(w-1, int(max(xs)*w + 24))
                by2 = min(h-1, int(max(ys)*h + 24))
                cv2.rectangle(frame, (bx1,by1), (bx2,by2), col, 2)
                label = f" P{pi+1} "
                (lw2, lh2), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.75, 2)
                cv2.rectangle(frame, (bx1, by1-lh2-10), (bx1+lw2+6, by1), col, -1)
                cv2.putText(frame, label, (bx1+3, by1-6),
                            cv2.FONT_HERSHEY_DUPLEX, 0.75, WHITE, 2)

            # Collision zone
            nx = int(pd["nose"].x * w)
            ny = int(pd["nose"].y * h)
            cr = int(pd["body_width"] * w * 0.6)
            cv2.circle(frame, (nx, ny), cr, col, 1)

        # ── Draw + analyse each detected hand ─────────────────────
        for hi, hlms in enumerate(hand_res.hand_landmarks or []):
            col = ORANGE if hi % 2 == 0 else (0,200,255)
            # Draw hand scaled to full frame
            hpts = [(int(lm.x*w), int(lm.y*h)) for lm in hlms]
            for a,b2 in HAND_CONN:
                cv2.line(frame, hpts[a], hpts[b2], col, 2)
            for hp in hpts:
                cv2.circle(frame, hp, 3, WHITE, -1)
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

        with lock:
            status_data["people_count"] = max(len(pose_list), n_hog)

        if away_on:
            away_threats = detect_away(frame, pose_list, w, h)
            all_threats.extend(away_threats)
            # Away mode overlay
            cv2.rectangle(frame,(0,h-36),(w,h),(30,0,100),-1)
            cv2.putText(frame,"AWAY MODE — ARMED",(12,h-10),
                        cv2.FONT_HERSHEY_DUPLEX,.7,(180,100,255),2)

        # ── Only detect threats when 2+ people are in frame ─────────
        # Two people = 2 poses OR 2 HOG detections
        n_pose_people = len(pose_list)
        two_people = n_pose_people >= 2 or n_hog >= 2

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
        bar_col = (0,30,180) if (confirmed and (two_people or away_trigger)) else (0,110,0)
        cv2.rectangle(frame,(0,0),(w,52),bar_col,-1)

        n_people = max(len(pose_list), n_hog)
        n_hands  = len(hand_list)

        if confirmed and (two_people or away_trigger):
            status_txt = "SOS! " + " | ".join(LABELS.get(c,c) for c in confirmed[:2])
        elif away_on and n_people == 0:
            status_txt = "AWAY MODE — Area Clear"
        elif away_on:
            status_txt = f"AWAY MODE — {n_people} person(s) detected!"
        elif n_people == 0:
            status_txt = "No people detected"
        elif n_people == 1:
            status_txt = f"1 person detected — need 2nd person in frame"
        else:
            status_txt = f"OK — {n_people} people detected | monitoring"
        cv2.putText(frame, status_txt, (12,36), cv2.FONT_HERSHEY_DUPLEX, .8, WHITE, 2)

        # Counter top-right
        info = f"HOG:{n_hog} Poses:{n_pose_people} Hands:{n_hands}"
        cv2.putText(frame, info, (w-300,36), cv2.FONT_HERSHEY_SIMPLEX, .55, WHITE, 1)

        # If only 1 person, show hint at bottom
        if n_people == 1 and not away_on:
            cv2.rectangle(frame, (0,h-32), (w,h), (0,80,0), -1)
            cv2.putText(frame, "  Waiting for 2nd person to enter frame...",
                        (8, h-8), cv2.FONT_HERSHEY_SIMPLEX, .55, WHITE, 1)
        elif n_people == 0 and not away_on:
            cv2.rectangle(frame, (0,h-32), (w,h), (40,40,40), -1)
            cv2.putText(frame, "  No people detected — stand in frame",
                        (8, h-8), cv2.FONT_HERSHEY_SIMPLEX, .55, WHITE, 1)

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

      except Exception as e:
        import traceback
        print(f"  Frame error: {e}")
        traceback.print_exc()
        time.sleep(0.1)
        continue

    cap.release()
    try: pose_det.close()
    except: pass
    try: hand_det.close()
    except: pass


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

@app.route('/snapshot_latest')
def snapshot_latest():
    """Single JPEG frame — for JS polling fallback"""
    with lock:
        buf = frame_buffer
    if buf is None:
        # Return a black 1x1 pixel if no frame yet
        import base64
        blank = base64.b64decode(
            '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U'
            'HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN'
            'DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy'
            'MjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAA'
            'AAAAAAAAAAAAAP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA'
            '/9oADAMBAAIRAxEAPwCwABmX/9k='
        )
        return Response(blank, mimetype='image/jpeg')
    resp = Response(buf, mimetype='image/jpeg')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route('/status')
def status():
    with lock:
        s = dict(status_data)
    s["sos_log"] = sos_log[-10:]
    return jsonify(s)


@app.route('/')
def index():
    return render_template_string(WEB_PAGE)

@app.route('/app')
def app_page():
    return APP_HTML

APP_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">\n<title>StepPrep</title>\n<style>\n*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}\nhtml,body{height:100%;font-family:system-ui,sans-serif;background:#111;display:flex;align-items:center;justify-content:center}\n#app{width:100%;max-width:420px;height:100vh;display:flex;flex-direction:column;background:#fff;position:relative;overflow:hidden}\n#app{--p:#1a1a1a;--a:#3b82f6;--d:#ef4444;--s:#10b981;--w:#f59e0b;--bg:#fff;--bg2:#f9fafb;--bd:#e5e7eb;--t:#111827;--t2:#6b7280}\n#hdr{background:var(--p);padding:12px 16px;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}\n#hdr h1{font-size:18px;font-weight:700;color:#fff}\n#hdr small{font-size:11px;color:rgba(255,255,255,.6);display:block}\n#clk{font-size:12px;color:rgba(255,255,255,.7)}\n#cnt{flex:1;overflow:hidden;position:relative}\n.sc{position:absolute;inset:0;overflow-y:auto;padding:14px 14px 76px;display:none}\n.sc.on{display:block}\n#nav{display:flex;border-top:1px solid var(--bd);background:var(--bg);flex-shrink:0;min-height:52px}\n.nb{flex:1;display:flex;flex-direction:column;align-items:center;padding:6px 1px 4px;gap:2px;font-size:8.5px;font-weight:600;color:var(--t2);background:none;border:none;cursor:pointer;font-family:inherit}\n.nb .ic{font-size:18px;line-height:1.2}\n.nb.on{color:var(--a)}\n.nb.rn{color:var(--d)}\n.nb.rn.on{color:var(--d)}\n/* cards */\n.c1{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.05)}\n.c2{background:var(--bg2);border:1px solid var(--bd);border-radius:10px;padding:11px;margin-bottom:8px}\n/* buttons */\n.btn{padding:11px 18px;border-radius:10px;font-size:14px;font-weight:600;border:none;cursor:pointer;font-family:inherit;width:100%;display:block;margin-top:8px}\n.bp{background:var(--a);color:#fff}\n.bd{background:var(--d);color:#fff}\n.bg{background:var(--bg2);color:var(--t2);border:1px solid var(--bd)}\n.bsm{font-size:12px;font-weight:600;padding:5px 11px;border-radius:7px;border:none;cursor:pointer;font-family:inherit}\n.bsmp{background:var(--a);color:#fff}\n/* inputs */\ninput{width:100%;border:1.5px solid var(--bd);border-radius:8px;padding:10px 12px;font-size:14px;font-family:inherit;color:var(--t);background:var(--bg2);outline:none;display:block;margin:4px 0 10px}\ninput:focus{border-color:var(--a)}\n/* section header */\n.sh{display:flex;justify-content:space-between;align-items:center;margin:12px 0 8px}\n.sh h3{font-size:14px;font-weight:600;color:var(--t)}\n/* badges */\n.bk,.bl,.bm,.be{display:inline-flex;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer}\n.bk{background:rgba(16,185,129,.12);color:#059669}\n.bl{background:rgba(245,158,11,.12);color:#d97706}\n.bm{background:rgba(239,68,68,.12);color:#dc2626}\n.be{background:rgba(245,158,11,.12);color:#92400e}\n/* modal */\n.ov{position:absolute;inset:0;background:rgba(0,0,0,.5);z-index:100;display:flex;align-items:flex-end;justify-content:center;opacity:0;pointer-events:none;transition:opacity .2s}\n.ov.on{opacity:1;pointer-events:all}\n.sh2{background:var(--bg);border-radius:20px 20px 0 0;padding:18px;width:100%;transform:translateY(100%);transition:transform .25s}\n.ov.on .sh2{transform:none}\n.hndl{width:36px;height:4px;background:var(--bd);border-radius:2px;margin:0 auto 14px}\n/* confirm */\n.cov{position:absolute;inset:0;background:rgba(0,0,0,.5);z-index:200;display:flex;align-items:center;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity .15s}\n.cov.on{opacity:1;pointer-events:all}\n.cbox{background:var(--bg);border-radius:14px;padding:22px;width:100%;max-width:280px;text-align:center}\n/* sos */\n.sosb{width:150px;height:150px;border-radius:50%;background:linear-gradient(145deg,#f87171,#dc2626);border:3px solid rgba(255,255,255,.25);display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 8px 28px rgba(239,68,68,.4);font-family:inherit;user-select:none}\n@keyframes rp{0%{transform:scale(1);opacity:.5}100%{transform:scale(2);opacity:0}}\n.rng{position:absolute;width:150px;height:150px;border-radius:50%;border:2px solid var(--d);animation:rp 2s ease-out infinite;pointer-events:none}\n.rng:nth-child(2){animation-delay:.66s}\n.rng:nth-child(3){animation-delay:1.33s}\n/* hazards */\n.hz{border:1px solid var(--bd);border-radius:12px;margin-bottom:8px;overflow:hidden;cursor:pointer;background:var(--bg)}\n.hzh{display:flex;align-items:center;gap:12px;padding:12px 14px}\n/* misc */\n.row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--bd)}\n.row:last-child{border:none}\n.av{width:36px;height:36px;border-radius:50%;background:rgba(59,130,246,.12);color:var(--a);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}\n.dl{color:var(--t2);font-size:16px;cursor:pointer;opacity:.4;margin-left:auto;padding:4px}\n.empty{text-align:center;padding:28px 14px;color:var(--t2);font-size:13px}\n.segs{display:flex;gap:2px;height:7px;margin:6px 0}\n.segs span{flex:1;border-radius:2px;background:var(--bd)}\n.tbr{display:flex;gap:6px;margin-bottom:10px}\n.tb{flex:1;padding:7px;border-radius:8px;font-size:11px;font-weight:600;border:none;cursor:pointer;font-family:inherit}\n.dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}\n.mbar{background:var(--bd);border-radius:4px;height:7px;overflow:hidden;margin:5px 0}\n.mfill{height:100%;border-radius:4px;transition:width .3s}\n</style>\n</head>\n<body>\n<div id="app">\n<div id="hdr">\n  <div><h1>StepPrep</h1><small>Emergency Preparedness</small></div>\n  <span id="clk"></span>\n</div>\n<div id="cnt">\n\n<div class="sc on" id="s-home">\n  <div class="c1" id="rcard"></div>\n  <div class="c2" onclick="om(\'shelter\')" style="cursor:pointer;display:flex;align-items:center;gap:10px">\n    <span style="font-size:18px">🏠</span><span id="sht" style="font-size:14px"></span>\n  </div>\n  <div class="sh"><h3>Tasks</h3><button class="bsm bsmp" onclick="om(\'task\')">+ Add</button></div>\n  <div id="tlist"></div>\n</div>\n\n<div class="sc" id="s-kit">\n  <div class="sh"><h3>Supply Kit</h3><button class="bsm bsmp" onclick="om(\'supply\')">+ Add</button></div>\n  <p style="font-size:12px;color:var(--t2);margin-bottom:8px">Tap badge to cycle: OK → Low → Missing → Expired</p>\n  <div id="klist"></div>\n</div>\n\n<div class="sc" id="s-sos">\n  <div style="display:flex;flex-direction:column;align-items:center;padding:20px 0 14px;position:relative">\n    <div class="rng"></div><div class="rng"></div><div class="rng"></div>\n    <button class="sosb" onmousedown="ss()" ontouchstart="ss()" onmouseup="cs()" ontouchend="cs()">\n      <span style="font-size:42px;font-weight:800;color:#fff;letter-spacing:2px">SOS</span>\n      <span style="font-size:10px;color:rgba(255,255,255,.7);margin-top:3px">HOLD 3 SEC</span>\n    </button>\n  </div>\n  <div id="sst" style="text-align:center;font-size:13px;color:var(--t2);margin-bottom:12px">Hold 3 seconds to activate</div>\n  <div class="c2"><b style="font-size:12px">National:</b> <span style="font-size:12px;color:var(--t2)">112 · Fire:101 · Police:102 · Ambulance:103</span></div>\n  <div class="sh"><h3>Contacts</h3><button class="bsm bsmp" onclick="om(\'contact\')">+ Add</button></div>\n  <div id="clist"></div>\n</div>\n\n<div class="sc" id="s-ai">\n  <h2 style="font-size:17px;font-weight:700;margin-bottom:4px">AI Hazard Scout</h2>\n  <p style="font-size:12px;color:var(--t2);margin-bottom:12px">Gemini detects hazards for your region and auto-fills Kit &amp; Tasks</p>\n  <div id="aibody"></div>\n</div>\n\n<div class="sc" id="s-cam" style="padding:10px 10px 76px">\n  <h2 style="font-size:16px;font-weight:700;margin-bottom:2px">Threat Detector</h2>\n  <p style="font-size:11px;color:var(--t2);margin-bottom:8px">CV2 + MediaPipe · 2 people needed · HOG fallback</p>\n  <div id="tdbody"></div>\n</div>\n\n<div class="sc" id="s-hz">\n  <h2 style="font-size:17px;font-weight:700;margin-bottom:4px">Natural Hazards</h2>\n  <p style="font-size:12px;color:var(--t2);margin-bottom:10px">Tap a hazard for action steps</p>\n  <div id="hzlist"></div>\n</div>\n\n<div class="sc" id="s-set">\n  <h2 style="font-size:17px;font-weight:700;margin-bottom:12px">Settings</h2>\n  <p style="font-size:11px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Theme</p>\n  <div id="thbtns" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px"></div>\n  <div style="border-top:1px solid var(--bd);padding-top:12px">\n    <div style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--bd)"><span>Tasks</span><span id="stt" style="color:var(--t2)">0</span></div>\n    <div style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--bd)"><span>Supplies</span><span id="sts" style="color:var(--t2)">0</span></div>\n    <div style="display:flex;justify-content:space-between;padding:9px 0"><span>Contacts</span><span id="stc" style="color:var(--t2)">0</span></div>\n  </div>\n  <button class="btn bd" style="margin-top:16px" onclick="if(confirm(\'Clear ALL data?\')){localStorage.clear();location.reload()}">Clear All Data</button>\n</div>\n\n</div>\n\n<nav id="nav">\n  <button class="nb on" onclick="sw(\'home\',this)"><span class="ic">🏠</span>Home</button>\n  <button class="nb" onclick="sw(\'kit\',this)"><span class="ic">📦</span>Kit</button>\n  <button class="nb rn" onclick="sw(\'sos\',this)"><span class="ic">🚨</span>SOS</button>\n  <button class="nb" onclick="sw(\'ai\',this)"><span class="ic">🤖</span>AI</button>\n  <button class="nb" onclick="sw(\'cam\',this)"><span class="ic">📷</span>Camera</button>\n  <button class="nb" onclick="sw(\'hz\',this)"><span class="ic">☁️</span>Hazards</button>\n  <button class="nb" onclick="sw(\'set\',this)"><span class="ic">⚙️</span>Settings</button>\n</nav>\n\n<!-- modal -->\n<div class="ov" id="mod" onclick="if(event.target===this)cm()">\n  <div class="sh2">\n    <div class="hndl"></div>\n    <div id="mtit" style="font-size:17px;font-weight:700;text-align:center;margin-bottom:12px"></div>\n    <div id="mbdy"></div>\n    <div style="display:flex;gap:8px;margin-top:12px">\n      <button class="btn bg" style="flex:1;margin:0" onclick="cm()">Cancel</button>\n      <button class="btn bp" style="flex:1;margin:0" onclick="sm()">Save</button>\n    </div>\n  </div>\n</div>\n<!-- confirm -->\n<div class="cov" id="conf">\n  <div class="cbox">\n    <div id="cmsg" style="font-size:15px;font-weight:700;margin-bottom:6px"></div>\n    <div style="font-size:12px;color:var(--t2);margin-bottom:16px">Cannot be undone.</div>\n    <div style="display:flex;gap:8px">\n      <button class="btn bg" style="flex:1;margin:0" onclick="cc()">Cancel</button>\n      <button class="btn bd" style="flex:1;margin:0" onclick="dc()">Delete</button>\n    </div>\n  </div>\n</div>\n\n<script>\n// ── THEMES\nconst TH={modern:{p:\'#1a1a1a\',a:\'#3b82f6\',d:\'#ef4444\',s:\'#10b981\',w:\'#f59e0b\',bg:\'#fff\',bg2:\'#f9fafb\',bd:\'#e5e7eb\',t:\'#111827\',t2:\'#6b7280\'},bold:{p:\'#dc2626\',a:\'#ea580c\',d:\'#b91c1c\',s:\'#16a34a\',w:\'#d97706\',bg:\'#fef2f2\',bg2:\'#fee2e2\',bd:\'#fca5a5\',t:\'#450a0a\',t2:\'#991b1b\'},calm:{p:\'#0891b2\',a:\'#06b6d4\',d:\'#f43f5e\',s:\'#14b8a6\',w:\'#f59e0b\',bg:\'#f0fdfa\',bg2:\'#ccfbf1\',bd:\'#5eead4\',t:\'#134e4a\',t2:\'#0f766e\'},vibrant:{p:\'#8b5cf6\',a:\'#ec4899\',d:\'#f43f5e\',s:\'#22c55e\',w:\'#fbbf24\',bg:\'#faf5ff\',bg2:\'#f3e8ff\',bd:\'#d8b4fe\',t:\'#581c87\',t2:\'#7c3aed\'}};\nlet curTh=\'modern\';\nfunction at(n){curTh=n;const th=TH[n]||TH.modern;const a=document.getElementById(\'app\');Object.entries({\'--p\':th.p,\'--a\':th.a,\'--d\':th.d,\'--s\':th.s,\'--w\':th.w,\'--bg\':th.bg,\'--bg2\':th.bg2,\'--bd\':th.bd,\'--t\':th.t,\'--t2\':th.t2}).forEach(([k,v])=>a.style.setProperty(k,v));rset();}\n\n// ── DATA\nconst SK=\'sp3\';\nlet D={tasks:[],supplies:[],contacts:[],shelter:\'\',gemini_key:\'\',gemini_region:\'\',theme:\'modern\'};\nfunction ld(){try{const s=localStorage.getItem(SK);if(s){const d=JSON.parse(s);Object.assign(D,d);if(d.theme)at(d.theme)}}catch(e){}}\nfunction sv(){try{localStorage.setItem(SK,JSON.stringify(D))}catch(e){}}\nld();\n\n// ── CLOCK\nfunction tick(){const n=new Date();document.getElementById(\'clk\').textContent=String(n.getHours()).padStart(2,\'0\')+\':\'+String(n.getMinutes()).padStart(2,\'0\')}\nsetInterval(tick,1000);tick();\n\n// ── NAV\nfunction sw(tab,el){\n  document.querySelectorAll(\'.sc\').forEach(s=>s.classList.remove(\'on\'));\n  document.getElementById(\'s-\'+tab).classList.add(\'on\');\n  document.querySelectorAll(\'.nb\').forEach(b=>b.classList.remove(\'on\'));\n  if(el)el.classList.add(\'on\');\n  ra();\n  if(tab===\'cam\') setTimeout(startCamAuto, 100);\n}\n\n// ── RENDER ALL\nfunction ra(){rh();rk();rs();rai();rtd();rhz();rset();}\n\n// ── HOME\nfunction rh(){\n  const ok=D.supplies.filter(s=>s.status===\'ok\').length,tot=D.supplies.length;\n  const p=tot?Math.round(ok/tot*100):0;\n  const pc=p>=70?\'var(--s)\':p>=40?\'var(--w)\':\'var(--d)\';\n  const dt=D.tasks.filter(t=>t.done).length;\n  const rc=document.getElementById(\'rcard\');\n  rc.innerHTML=\'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px"><span style="font-size:11px;font-weight:600;color:var(--t2)">READINESS</span><span style="font-size:22px;font-weight:800;color:\'+pc+\'">\'+p+\'%</span></div><div class="segs" id="segs"></div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px"><div class="c2" style="margin:0;text-align:center"><div style="font-size:16px;font-weight:700;color:var(--s)">\'+ok+\'/\'+tot+\'</div><div style="font-size:10px;color:var(--t2)">supplies</div></div><div class="c2" style="margin:0;text-align:center"><div style="font-size:16px;font-weight:700;color:var(--a)">\'+dt+\'/\'+D.tasks.length+\'</div><div style="font-size:10px;color:var(--t2)">tasks</div></div><div class="c2" style="margin:0;text-align:center"><div style="font-size:16px;font-weight:700;color:var(--w)">\'+D.contacts.length+\'</div><div style="font-size:10px;color:var(--t2)">contacts</div></div></div>\';\n  const bar=document.getElementById(\'segs\');\n  if(bar){for(let i=0;i<20;i++){const s=document.createElement(\'span\');s.style.background=i<Math.round(p/100*20)?pc:\'var(--bd)\';bar.appendChild(s)}}\n  const sh=document.getElementById(\'sht\');sh.textContent=D.shelter||\'Tap to set shelter location\';sh.style.color=D.shelter?\'var(--t)\':\'var(--t2)\';\n  const tl=document.getElementById(\'tlist\');\n  if(!D.tasks.length){tl.innerHTML=\'<div class="empty">No tasks — tap + Add</div>\';return}\n  tl.innerHTML=D.tasks.map((t,i)=>\'<div class="c2" style="display:flex;align-items:center;gap:10px;cursor:pointer" onclick="tt(\'+i+\')"><div style="width:20px;height:20px;border-radius:5px;border:2px solid \'+(t.done?\'var(--s)\':\'var(--bd)\')+\';background:\'+(t.done?\'var(--s)\':\'transparent\')+\';display:flex;align-items:center;justify-content:center;flex-shrink:0">\'+(t.done?\'<span style="color:#fff;font-size:12px">✓</span>\':\'\')+\'</div><span style="flex:1;font-size:14px;\'+(t.done?\'text-decoration:line-through;opacity:.5\':\'\')+\'">\'+e(t.text)+\'</span><span class="dl" onclick="event.stopPropagation();ad(\'Delete task?\',()=>{D.tasks.splice(\'+i+\',1);sv();rh()})">✕</span></div>\').join(\'\');\n}\nfunction tt(i){D.tasks[i].done=!D.tasks[i].done;sv();rh()}\n\n// ── KIT\nfunction rk(){\n  const kl=document.getElementById(\'klist\');\n  if(!D.supplies.length){kl.innerHTML=\'<div class="empty">Kit empty — tap + Add</div>\';return}\n  kl.innerHTML=D.supplies.map((s,i)=>{const bc={\'ok\':\'bk\',\'low\':\'bl\',\'missing\':\'bm\',\'expired\':\'be\'}[s.status]||\'bk\';const bt={\'ok\':\'OK\',\'low\':\'Low\',\'missing\':\'Missing\',\'expired\':\'Expired\'}[s.status]||\'OK\';return \'<div class="c2" style="display:flex;align-items:center;gap:10px"><div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">\'+e(s.name)+\'</div><div style="font-size:11px;color:var(--t2)">\'+e(s.qty||\'\')+\'</div></div><span class="\'+bc+\'" onclick="cs2(\'+i+\')">\'+bt+\'</span><span class="dl" onclick="ad(\'Delete supply?\',()=>{D.supplies.splice(\'+i+\',1);sv();rk()})">✕</span></div>\'}).join(\'\');\n}\nfunction cs2(i){const c=[\'ok\',\'low\',\'missing\',\'expired\'];D.supplies[i].status=c[(c.indexOf(D.supplies[i].status)+1)%c.length];sv();rk()}\n\n// ── SOS\nfunction rs(){\n  const cl=document.getElementById(\'clist\');\n  cl.innerHTML=D.contacts.length?D.contacts.map((c,i)=>\'<div class="row"><div class="av">\'+e((c.name||\'?\')[0].toUpperCase())+\'</div><div style="flex:1"><div style="font-size:14px;font-weight:600">\'+e(c.name)+\'</div><div style="font-size:12px;color:var(--t2)">\'+e(c.phone||\'\')+\'</div></div><span class="dl" onclick="ad(\'Delete contact?\',()=>{D.contacts.splice(\'+i+\',1);sv();rs()})">✕</span></div>\').join(\'\'):\'<div class="empty">No contacts — tap + Add</div>\';\n}\nlet stmr=null,spg=0;\nfunction ss(){spg=0;stmr=setInterval(()=>{spg+=100;const p=Math.min(100,Math.round(spg/3000*100));const s=document.getElementById(\'sst\');s.textContent=\'Activating... \'+p+\'%\';s.style.color=\'var(--d)\';if(spg>=3000){clearInterval(stmr);stmr=null;s.textContent=\'SOS ACTIVATED\';s.style.fontWeight=\'700\'}},100)}\nfunction cs(){if(stmr){clearInterval(stmr);stmr=null}if(spg<3000){const s=document.getElementById(\'sst\');s.textContent=\'Hold 3 seconds to activate\';s.style.color=\'var(--t2)\';s.style.fontWeight=\'400\'}spg=0}\n\n// ── AI SCOUT\nfunction rai(){\n  const b=document.getElementById(\'aibody\');\n  if(!b)return;\n  if(!D.gemini_key){\n    b.innerHTML=\'<div class="c2" style="text-align:center"><div style="font-size:26px;margin-bottom:8px">🤖</div><div style="font-size:14px;font-weight:600;margin-bottom:4px">Gemini API Key</div><div style="font-size:12px;color:var(--t2);margin-bottom:10px">Free at aistudio.google.com</div><input id="gk" type="password" placeholder="AIza..."><button class="btn bp" onclick="sgk()">Save Key</button></div>\';\n  } else {\n    b.innerHTML=\'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span style="font-size:12px;color:var(--s)">✓ Key saved</span><span style="font-size:12px;color:var(--a);cursor:pointer" onclick="D.gemini_key=\'\';sv();rai()">Change</span></div><input id="gr" placeholder="Region e.g. Kyiv, California..." value="\'+e(D.gemini_region||\'\')+\'"><button class="btn bp" id="scnb" onclick="scan()">🔍 Scan My Region</button><div id="airesult" style="margin-top:10px"></div>\';\n  }\n}\nfunction sgk(){const k=(document.getElementById(\'gk\')||{value:\'\'}).value.trim();if(!k||!k.startsWith(\'AIza\')){alert(\'Enter a valid Gemini key (starts AIza)\');return}D.gemini_key=k;sv();rai()}\nasync function scan(){\n  const reg=(document.getElementById(\'gr\')||{value:\'\'}).value.trim();\n  if(!reg){alert(\'Enter a region first\');return}\n  D.gemini_region=reg;sv();\n  const btn=document.getElementById(\'scnb\');\n  if(btn){btn.textContent=\'Scanning...\';btn.disabled=true}\n  try{\n    const r=await fetch(\'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=\'+D.gemini_key,{\n      method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify({contents:[{parts:[{text:\'You are a disaster preparedness expert. For "\'+reg+\'", return ONLY a JSON object with "kit" (array of 8-12 supply item strings) and "tasks" (array of 6-10 task strings). No explanation, just JSON.\'}]}]})\n    });\n    const data=await r.json();\n    if(data.error)throw new Error(data.error.message);\n    let txt=data.candidates[0].content.parts[0].text.trim();\n    if(txt.includes(\'```\'))txt=txt.split(\'```\')[1].replace(/^json/,\'\').trim();\n    const p=JSON.parse(txt);let kn=0,tn=0;\n    (p.kit||[]).forEach(x=>{if(typeof x===\'string\'&&x.trim()){D.supplies.push({name:x.trim(),qty:\'\',status:\'ok\'});kn++}});\n    (p.tasks||[]).forEach(x=>{if(typeof x===\'string\'&&x.trim()){D.tasks.push({text:x.trim(),done:false});tn++}});\n    sv();\n    const res=document.getElementById(\'airesult\');\n    if(res)res.innerHTML=\'<div class="c2" style="background:rgba(16,185,129,.08)"><b style="color:var(--s)">Done!</b> Added \'+kn+\' kit items &amp; \'+tn+\' tasks for \'+e(reg)+\'</div>\';\n  }catch(ex){alert(\'Error: \'+(ex.message||\'Check API key and region\'))}\n  if(btn){btn.textContent=\'🔍 Scan My Region\';btn.disabled=false}\n}\n\n// ── THREAT DETECTOR\nlet tdpi=null,tdsi=null,tdaw=false,tdtab=\'live\';\nfunction rtd(){\n  const b=document.getElementById(\'tdbody\');\n  if(!b)return;\n  b.innerHTML=\'<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:10px;border:1px solid var(--bd);background:var(--bg2);margin-bottom:10px"><div class="dot" id="tdd" style="background:var(--d)"></div><span id="tdt" style="font-size:13px;font-weight:500;flex:1">Connecting...</span><span id="tdm" style="font-size:11px;color:var(--t2)"></span></div><div id="tdalert" style="display:none;background:rgba(239,68,68,.1);border:1.5px solid var(--d);border-radius:10px;padding:12px;margin-bottom:10px"><div style="font-size:15px;font-weight:800;color:var(--d);margin-bottom:4px">THREAT DETECTED</div><div id="tdthr" style="font-size:13px;color:var(--d)"></div></div><div class="tbr"><button class="tb" id="tb-live" onclick="stdt(\'live\')">📹 Live</button><button class="tb" id="tb-away" onclick="stdt(\'away\')">🏠 Away</button><button class="tb" id="tb-log" onclick="stdt(\'log\')">📋 Log</button><button class="tb" id="tb-snaps" onclick="stdt(\'snaps\')">📸 Snaps</button></div><div id="tdlive"><div style="border-radius:10px;overflow:hidden;border:2px solid var(--bd);background:#000;margin-bottom:8px"><img id="camfeed" style="width:100%;display:block;min-height:180px" alt=""></div><div style="display:flex;gap:8px;margin-bottom:8px;align-items:center"><div id="camst" style="flex:1;font-size:12px;color:var(--w);font-weight:600">● Starting...</div><button onclick="startCam()" style="font-size:11px;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:4px 10px;cursor:pointer;font-family:inherit">▶ Start</button><button onclick="stopCam()" style="font-size:11px;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:4px 10px;cursor:pointer;font-family:inherit">■ Stop</button></div></div><div id="tdaway" style="display:none"><button onclick="tgaw()" id="awbtn" class="btn bp" style="margin-bottom:10px">🏠 ARM Away Mode</button><div class="c2" style="margin-bottom:8px"><div style="font-size:11px;font-weight:600;color:var(--t2);margin-bottom:5px">MOTION LEVEL</div><div class="mbar"><div class="mfill" id="mfl" style="width:0%;background:var(--a)"></div></div><div id="mvl" style="font-size:11px;color:var(--t2)">0 px</div></div><div class="c2"><div style="font-size:11px;font-weight:600;color:var(--t2);margin-bottom:4px">PEOPLE IN FRAME</div><div id="pct2" style="font-size:24px;font-weight:800;color:var(--t)">0</div><div style="font-size:11px;color:var(--t2);margin-top:2px">Need 2 people for threat detection</div></div></div><div id="tdlog" style="display:none"><div id="loge" class="c1"><div class="empty">No events yet</div></div></div><div id="tdsnaps" style="display:none"><div id="snapg"><div class="empty">No snapshots yet</div></div></div><div class="c2" style="margin-top:8px;background:rgba(16,185,129,.06);border-color:rgba(16,185,129,.2)"><div style="font-size:12px;font-weight:600;color:var(--s);margin-bottom:4px">No setup needed!</div><div style="font-size:11px;color:var(--t2);line-height:1.5">Page served from threat_server.py — live feed and all controls work automatically.</div></div>\';\n  stdt(\'live\');\n  stp();\n}\nfunction stdt(t){\n  tdtab=t;\n  [\'live\',\'away\',\'log\',\'snaps\'].forEach(id=>{\n    const el=document.getElementById(\'td\'+id);if(el)el.style.display=id===t?\'\':\'none\';\n    const btn=document.getElementById(\'tb-\'+id);\n    if(btn){btn.style.background=id===t?\'var(--a)\':\'var(--bg2)\';btn.style.color=id===t?\'#fff\':\'var(--t2)\'}\n  });\n}\nfunction stp(){\n  if(tdpi)clearInterval(tdpi);\n  tdpi=setInterval(async()=>{\n    try{\n      const r=await fetch(\'/status\');\n      if(!r.ok)throw new Error(r.status);\n      const s=await r.json();\n      tdaw=!!s.away_mode;\n      const dd=document.getElementById(\'tdd\'),dt=document.getElementById(\'tdt\'),dm=document.getElementById(\'tdm\');\n      const da=document.getElementById(\'tdalert\'),dt2=document.getElementById(\'tdthr\');\n      const has=s.confirmed&&s.confirmed.length>0;\n      if(dd)dd.style.background=has?\'var(--d)\':\'var(--s)\';\n      if(dt){\n        if(has)dt.textContent=\'THREAT DETECTED\';\n        else if(s.people_count>=2)dt.textContent=\'Monitoring 2 people\';\n        else dt.textContent=\'Waiting for 2 people (\'+s.people_count+\' detected)\';\n      }\n      if(dm)dm.textContent=\'FPS:\'+s.fps+\' SOS:\'+s.sos_count;\n      if(da)da.style.display=has?\'\':\'none\';\n      if(dt2&&has)dt2.innerHTML=(s.confirmed||[]).map(k=>\'• \'+({FIST_FACE:\'Fist → Face\',FIST_BODY:\'Fist → Body\',GUN_POSE:\'Gun Pose\',ARM_SWING:\'Arm Swing\',PUNCH:\'Punch Motion\',PERSON_COLLISION:\'Too Close\',INTRUDER:\'Intruder!\',MOTION:\'Motion\',LOITER:\'Loitering\',ZONE_BREACH:\'Zone Breach\'}[k]||k)).join(\'<br>\');\n      const mf=document.getElementById(\'mfl\'),mv=document.getElementById(\'mvl\'),pc2=document.getElementById(\'pct2\');\n      if(mf){const pct=Math.min(100,(s.motion_level||0)/15000*100);mf.style.width=pct+\'%\';mf.style.background=pct>60?\'var(--d)\':pct>30?\'var(--w)\':\'var(--a)\'}\n      if(mv)mv.textContent=(s.motion_level||0)+\' px\';\n      if(pc2){pc2.textContent=s.people_count||0;pc2.style.color=(s.people_count||0)>=2?\'var(--s)\':tdaw&&(s.people_count||0)>0?\'var(--d)\':\'var(--t)\'}\n      const ab=document.getElementById(\'awbtn\');\n      if(ab){ab.textContent=tdaw?\'🔴 DISARM Away Mode\':\'🏠 ARM Away Mode\';ab.style.background=tdaw?\'var(--d)\':\'var(--a)\'}\n      const le=document.getElementById(\'loge\');\n      if(le&&s.sos_log)le.innerHTML=s.sos_log.length?[...s.sos_log].reverse().map(ev=>\'<div class="row"><span style="font-size:10px;color:var(--a);font-weight:600;flex-shrink:0">\'+ev.time+\'</span><span style="font-size:12px;flex:1;margin-left:8px">\'+e(ev.reason)+\'</span></div>\').join(\'\'):\'<div class="empty">No events yet</div>\';\n    }catch(err){\n      const dt=document.getElementById(\'tdt\');if(dt)dt.textContent=\'Connecting to server...\';\n    }\n  },1000);\n  if(tdsi)clearInterval(tdsi);\n  tdsi=setInterval(async()=>{\n    try{const r=await fetch(\'/snapshots\');const d=await r.json();const sg=document.getElementById(\'snapg\');if(sg)sg.innerHTML=d.snapshots&&d.snapshots.length?[...d.snapshots].reverse().slice(0,6).map(s=>\'<div style="margin-bottom:10px"><img src="/snapshots/\'+s.file+\'" style="width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;border:1px solid var(--bd);display:block"><div style="font-size:10px;color:var(--a);margin-top:3px">\'+s.time+\' - \'+e(s.reason.slice(0,35))+\'</div></div>\').join(\'\'):\'<div class="empty">No snapshots yet</div>\'}catch(err){}\n  },3000);\n}\nasync function tgaw(){tdaw=!tdaw;try{await fetch(\'/away\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({active:tdaw})})}catch(err){}}\n\n// ── HAZARDS\nconst HZD=[{i:\'🌬️\',n:\'High Wind\',c:\'var(--a)\',b:\'rgba(59,130,246,.1)\',l:\'Breezy → Hurricane\',s:[\'Secure loose outdoor objects.\',\'Stay away from windows.\',\'Park away from trees/power lines.\',\'Avoid driving in 70+ km/h winds.\'],t:\'Never shelter under trees.\'},{i:\'🌪️\',n:\'Tornado\',c:\'var(--w)\',b:\'rgba(245,158,11,.1)\',l:\'Watch → Confirmed\',s:[\'Go to lowest floor.\',\'Interior room, no windows.\',\'Cover with heavy blankets.\',\'Never outrun in a vehicle.\'],t:\'Basement is safest.\'},{i:\'🌊\',n:\'Tsunami\',c:\'var(--a)\',b:\'rgba(59,130,246,.1)\',l:\'Advisory → Warning\',s:[\'Move to 30m+ elevation.\',\'Do NOT wait to see the wave.\',\'Follow evacuation routes.\',\'Stay inland until safe.\'],t:\'Strong coastal earthquake = evacuate immediately.\'},{i:\'📳\',n:\'Earthquake\',c:\'var(--w)\',b:\'rgba(245,158,11,.1)\',l:\'Minor → Great\',s:[\'DROP to hands and knees.\',\'COVER under desk, hold on.\',\'HOLD ON until shaking stops.\',\'Check for gas leaks after.\'],t:\'DROP · COVER · HOLD ON.\'},{i:\'💧\',n:\'Flood\',c:\'var(--a)\',b:\'rgba(59,130,246,.1)\',l:\'Watch → Flash Flood\',s:[\'Move to higher ground.\',\'Never walk through 15cm floodwater.\',\'Turn off utilities.\',\'Do not return until safe.\'],t:"Turn Around, Don\'t Drown."},{i:\'🔥\',n:\'Wildfire\',c:\'var(--d)\',b:\'rgba(239,68,68,.1)\',l:\'Watch → Evacuation\',s:[\'Evacuate when ordered.\',\'Close windows and vents.\',\'Take go-bag and meds.\',\'Drive with headlights on.\'],t:\'30m defensible space around home.\'},{i:\'🌡️\',n:\'Extreme Heat\',c:\'var(--d)\',b:\'rgba(239,68,68,.1)\',l:\'Hot → Extreme\',s:[\'Stay in AC 11am–4pm.\',\'Drink water before thirsty.\',\'Never leave children in cars.\',\'Heatstroke = call emergency.\'],t:\'Heatstroke: cool rapidly with ice.\'},{i:\'❄️\',n:\'Blizzard\',c:\'var(--a)\',b:\'rgba(59,130,246,.1)\',l:\'Advisory → Warning\',s:[\'Stay indoors.\',\'Keep heating fuel stocked.\',\'Watch for frostbite.\',\'No generators indoors.\'],t:\'Stranded in car: run engine 10 min/hr.\'}];\nlet hze=null;\nfunction rhz(){const l=document.getElementById(\'hzlist\');if(!l)return;l.innerHTML=HZD.map((h,i)=>\'<div class="hz" onclick="hze=hze===\'+i+\'?null:\'+i+\';rhz()"><div class="hzh"><div style="width:36px;height:36px;border-radius:10px;background:\'+h.b+\';display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">\'+h.i+\'</div><div style="flex:1"><div style="font-size:14px;font-weight:600">\'+h.n+\'</div><div style="font-size:11px;color:var(--t2)">\'+h.l+\'</div></div><div style="font-size:13px;color:var(--t2);transition:transform .2s\'+(hze===i?\';transform:rotate(90deg)\':\'\')+\'">›</div></div>\'+(hze===i?\'<div style="border-top:1px solid var(--bd);padding:10px 14px">\'+h.s.map((s,si)=>\'<div style="display:flex;gap:10px;margin-bottom:7px;font-size:13px"><div style="width:20px;height:20px;border-radius:50%;background:\'+h.b+\';color:\'+h.c+\';display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0">\'+(si+1)+\'</div><div>\'+s+\'</div></div>\').join(\'\')+\'<div style="background:\'+h.b+\';border-radius:8px;padding:8px 10px;font-size:12px;color:\'+h.c+\';font-weight:500">💡 \'+h.t+\'</div></div>\':\'\')+\'</div>\').join(\'\');}\n\n// ── SETTINGS\nfunction rset(){const tb=document.getElementById(\'thbtns\');if(tb)tb.innerHTML=Object.entries(TH).map(([k,th])=>\'<button onclick="at(\'\'+k+\'\');D.theme=\'\'+k+\'\';sv();rset()" style="padding:7px 13px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;border:2px solid \'+(curTh===k?th.a:th.bd)+\';background:\'+th.bg2+\';color:\'+th.t+\'">\'+k.charAt(0).toUpperCase()+k.slice(1)+\'</button>\').join(\'\');const st=document.getElementById(\'stt\');if(st)st.textContent=D.tasks.length;const ss2=document.getElementById(\'sts\');if(ss2)ss2.textContent=D.supplies.length;const sc=document.getElementById(\'stc\');if(sc)sc.textContent=D.contacts.length;}\n\n// ── MODALS\nconst MDEFS={task:{title:\'New Task\',flds:[{id:\'f0\',lab:\'Description\',ph:\'e.g. Check water supply\'}]},supply:{title:\'Add Supply\',flds:[{id:\'f0\',lab:\'Item name\',ph:\'e.g. Bottled water\'},{id:\'f1\',lab:\'Quantity\',ph:\'e.g. 10 L\'}]},contact:{title:\'New Contact\',flds:[{id:\'f0\',lab:\'Name\',ph:\'Full name\'},{id:\'f1\',lab:\'Phone\',ph:\'+1 555 000 0000\'},{id:\'f2\',lab:\'Role\',ph:\'e.g. Family\'}]},shelter:{title:\'Set Shelter\',flds:[{id:\'f0\',lab:\'Location\',ph:\'e.g. Basement of Block 3\'}]}};\nlet mk=null,ccb=null;\nfunction om(k){mk=k;const m=MDEFS[k];document.getElementById(\'mtit\').textContent=m.title;document.getElementById(\'mbdy\').innerHTML=m.flds.map(f=>\'<div style="margin-bottom:10px"><label style="font-size:12px;color:var(--t2);font-weight:500;display:block;margin-bottom:4px">\'+f.lab+\'</label><input id="\'+f.id+\'" placeholder="\'+f.ph+\'" autocomplete="off"></div>\').join(\'\');if(k===\'shelter\'&&D.shelter){const i=document.getElementById(\'f0\');if(i)i.value=D.shelter}document.getElementById(\'mod\').classList.add(\'on\');setTimeout(()=>{const i=document.getElementById(\'f0\');if(i)i.focus()},250);}\nfunction cm(){document.getElementById(\'mod\').classList.remove(\'on\');mk=null}\nfunction sm(){\n  if(!mk)return;\n  const g=id=>{const el=document.getElementById(id);return el?el.value.trim():\'\'};\n  if(mk===\'task\'&&g(\'f0\'))D.tasks.push({text:g(\'f0\'),done:false});\n  else if(mk===\'supply\'&&g(\'f0\'))D.supplies.push({name:g(\'f0\'),qty:g(\'f1\')||\'\',status:\'ok\'});\n  else if(mk===\'contact\'&&g(\'f0\'))D.contacts.push({name:g(\'f0\'),phone:g(\'f1\')||\'\',role:g(\'f2\')||\'\'});\n  else if(mk===\'shelter\'&&g(\'f0\'))D.shelter=g(\'f0\');\n  sv();cm();ra();\n}\ndocument.addEventListener(\'keydown\',ev=>{if(ev.key===\'Enter\'&&document.getElementById(\'mod\').classList.contains(\'on\'))sm();if(ev.key===\'Escape\'){cm();cc()}});\nfunction ad(msg,cb){document.getElementById(\'cmsg\').textContent=msg;ccb=cb;document.getElementById(\'conf\').classList.add(\'on\')}\nfunction cc(){document.getElementById(\'conf\').classList.remove(\'on\');ccb=null}\nfunction dc(){if(ccb)ccb();cc()}\nfunction e(s){const d=document.createElement(\'div\');d.textContent=String(s||\'\');return d.innerHTML}\n\n// ── BOOT\nra();\n\n// ── CAMERA — rapid snapshot polling (works in all browsers)\nlet camInt = null;\nlet camTs  = 0;\n\nfunction startCam() {\n  stopCam();\n  const img = document.getElementById(\'camfeed\');\n  const st  = document.getElementById(\'camst\');\n  if(!img) return;\n  if(st){ st.textContent=\'● Live\'; st.style.color=\'var(--s)\'; }\n  // Load new snapshot every 80ms (~12fps) — same-origin so no CORS\n  camInt = setInterval(() => {\n    camTs++;\n    const next = new Image();\n    next.onload = () => { img.src = next.src; };\n    next.onerror = () => {\n      if(st){ st.textContent=\'✕ No feed — check server\'; st.style.color=\'var(--d)\'; }\n    };\n    next.src = \'/snapshot_latest?t=\' + camTs;\n  }, 80);\n}\n\nfunction stopCam() {\n  if(camInt){ clearInterval(camInt); camInt=null; }\n  const st = document.getElementById(\'camst\');\n  if(st){ st.textContent=\'■ Stopped\'; st.style.color=\'var(--t2)\'; }\n}\n\n// Auto-start camera — use snapshot polling (reliable in all browsers)\n// ── CAMERA — snapshot polling\nlet camInt = null;\nlet camTs  = 0;\n\nfunction startCam() {\n  stopCam();\n  const img = document.getElementById(\'camfeed\');\n  const st  = document.getElementById(\'camst\');\n  if(!img) return;\n  if(st){ st.textContent=\'● Live\'; st.style.color=\'var(--s)\'; }\n  camInt = setInterval(() => {\n    camTs++;\n    const next = new Image();\n    next.onload = () => {\n      img.src = next.src;\n      const s = document.getElementById(\'camst\');\n      if(s && s.textContent.includes(\'No feed\')){ s.textContent=\'● Live\'; s.style.color=\'var(--s)\'; }\n    };\n    next.onerror = () => {\n      const s = document.getElementById(\'camst\');\n      if(s){ s.textContent=\'✕ No feed — server may be starting\'; s.style.color=\'var(--d)\'; }\n    };\n    next.src = \'/snapshot_latest?t=\' + camTs;\n  }, 100);\n}\n\nfunction stopCam() {\n  if(camInt){ clearInterval(camInt); camInt=null; }\n  const st = document.getElementById(\'camst\');\n  if(st){ st.textContent=\'■ Stopped\'; st.style.color=\'var(--t2)\'; }\n}\n\nfunction startCamAuto() { startCam(); }\n</script>\n</body>\n</html>'

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
    print("━"*52)
    print("  Checking MediaPipe models...")
    print("  If models are missing, download links will open.")
    print("  Save files to the mp_models/ folder shown.")
    print("━"*52)
    download_model(POSE_URL,  POSE_MODEL)
    download_model(HAND_URL,  HAND_MODEL)
    # Person counting uses OpenCV HOG (built-in, no download)
    print("  All models ready!")
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
