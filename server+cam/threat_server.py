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
from collections import deque
from flask import Flask, Response, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Config ────────────────────────────────────────────────────────
THREAT_FRAMES    = 6
COLLISION_DIST   = 0.13
SWING_VEL_THRESH = 0.035
SOS_COOLDOWN     = 4.0
PORT             = 5050

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
}
sos_log = []


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

def analyse_hand(hand_lms):
    lms  = hand_lms.landmark
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
    PL = mp.solutions.pose.PoseLandmark
    l_sh = lms[PL.LEFT_SHOULDER];  r_sh = lms[PL.RIGHT_SHOULDER]
    l_el = lms[PL.LEFT_ELBOW];     r_el = lms[PL.RIGHT_ELBOW]
    l_wr = lms[PL.LEFT_WRIST];     r_wr = lms[PL.RIGHT_WRIST]
    nose = lms[PL.NOSE]
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
    "FIST_FACE":    "FIST → FACE",
    "FIST_BODY":    "FIST → BODY",
    "FIST_FIST":    "FIST COLLISION",
    "GUN_POSE":     "GUN POSE DETECTED",
    "ARM_SWING":    "AGGRESSIVE SWING",
    "THREAT_STANCE":"THREATENING STANCE",
    "PUNCH":        "PUNCH MOTION",
}

def camera_thread():
    global frame_buffer, status_data, sos_log

    mp_pose  = mp.solutions.pose
    mp_hands = mp.solutions.hands
    mp_draw  = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    pose  = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6, model_complexity=1)
    hands = mp_hands.Hands(max_num_hands=4, min_detection_confidence=0.65, min_tracking_confidence=0.55)

    prev_wrists = deque(maxlen=5)
    fps_q       = deque(maxlen=20)
    last_sos    = 0

    with lock:
        status_data["running"] = True

    while True:
        t0 = time.time()
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        pose_res  = mp_pose.Pose().process(rgb) if False else pose.process(rgb)
        hands_res = hands.process(rgb)
        rgb.flags.writeable = True

        all_threats = []
        confirmed   = []
        pose_data   = None
        hand_list   = []

        if pose_res.pose_landmarks:
            lms = pose_res.pose_landmarks.landmark
            mp_draw.draw_landmarks(
                frame, pose_res.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_draw.DrawingSpec(color=BLUE, thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=GREEN, thickness=2),
            )
            pose_data = analyse_pose(lms)

            # Collision zone circle around head
            nx, ny = int(pose_data["nose"].x*w), int(pose_data["nose"].y*h)
            cr = int(pose_data["body_width"] * w * 0.55)
            cv2.circle(frame, (nx,ny), cr, GREEN, 1)

        if hands_res.multi_hand_landmarks:
            for hlm in hands_res.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    frame, hlm, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=ORANGE, thickness=2, circle_radius=4),
                    mp_draw.DrawingSpec(color=(0,200,255), thickness=2),
                )
                ha = analyse_hand(hlm)
                hand_list.append(ha)
                wx, wy = int(ha["wrist"].x*w), int(ha["wrist"].y*h)
                if ha["is_fist"]:
                    cv2.rectangle(frame,(wx-30,wy-30),(wx+70,wy+8),(0,0,180),-1)
                    cv2.putText(frame,"FIST",(wx-26,wy-8),cv2.FONT_HERSHEY_DUPLEX,.65,WHITE,2)
                elif ha["is_gun"]:
                    cv2.rectangle(frame,(wx-30,wy-30),(wx+130,wy+8),(0,80,180),-1)
                    cv2.putText(frame,"GUN POSE",(wx-26,wy-8),cv2.FONT_HERSHEY_DUPLEX,.65,WHITE,2)

        if pose_data and hand_list:
            all_threats = get_threats(pose_data, hand_list, prev_wrists)
        elif pose_data:
            all_threats = get_threats(pose_data, [], prev_wrists)

        if pose_data:
            prev_wrists.append((pose_data["l_wrist"], pose_data["r_wrist"]))

        # Confirm over N frames
        for th in set(all_threats):
            if tick(th, True):
                confirmed.append(th)
        for k in list(threat_counter):
            if k not in all_threats:
                tick(k, False)

        # SOS
        sos_active = False
        sos_reason = ""
        sos_count  = status_data["sos_count"]
        if confirmed and time.time() - last_sos > SOS_COOLDOWN:
            last_sos   = time.time()
            sos_count += 1
            sos_active = True
            sos_reason = " | ".join(LABELS.get(c,c) for c in confirmed[:2])
            sos_log.append({"time": time.strftime("%H:%M:%S"), "reason": sos_reason})
            print(f"🚨 SOS: {sos_reason}")

        # Draw status overlay
        bar_col = (0,30,180) if confirmed else (0,110,0)
        cv2.rectangle(frame,(0,0),(w,52),bar_col,-1)
        status_txt = "SOS! " + " | ".join(LABELS.get(c,c) for c in confirmed[:2]) if confirmed else "✓ Monitoring — No Threats"
        cv2.putText(frame, status_txt, (12,36), cv2.FONT_HERSHEY_DUPLEX, .85, WHITE, 2)

        fps_q.append(1.0/max(time.time()-t0,1e-6))
        fps = sum(fps_q)/len(fps_q)
        cv2.putText(frame, f"FPS:{fps:.0f}", (w-90,36), cv2.FONT_HERSHEY_SIMPLEX, .6, WHITE, 1)

        if sos_active:
            ov = frame.copy()
            cv2.rectangle(ov,(0,0),(w,h),(0,0,180),-1)
            cv2.addWeighted(ov,.3,frame,.7,0,frame)
            cv2.putText(frame,"!!! SOS !!!",(w//2-130,h//2),cv2.FONT_HERSHEY_DUPLEX,2.2,WHITE,5)

        # Encode frame
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        with lock:
            frame_buffer = buf.tobytes()
            status_data.update({
                "threats":    all_threats,
                "confirmed":  confirmed,
                "sos_count":  sos_count,
                "sos_active": sos_active,
                "sos_reason": sos_reason,
                "last_sos":   last_sos,
                "fps":        round(fps,1),
            })

    cap.release()
    pose.close()
    hands.close()


# ══════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════

def gen_frames():
    while True:
        with lock:
            buf = frame_buffer
        if buf is None:
            time.sleep(0.03)
            continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf + b'\r\n')
        time.sleep(0.03)


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


# ══════════════════════════════════════════════════════════════════
#  BUILT-IN WEB VIEWER (shown at http://localhost:5050)
# ══════════════════════════════════════════════════════════════════

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
  <span class="badge" id="run-badge">Starting...</span>
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

setInterval(poll, 800);
poll();
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
    print(f"  Web viewer:  http://localhost:{PORT}")
    print(f"  Video feed:  http://localhost:{PORT}/video")
    print(f"  Status API:  http://localhost:{PORT}/status")
    print("━" * 52)
    print("  Starting camera thread...")

    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()

    time.sleep(1.5)
    print("  Camera running. Opening browser...")

    import webbrowser, subprocess, sys
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except: pass

    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
