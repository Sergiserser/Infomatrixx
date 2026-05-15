import subprocess
import time
import webbrowser
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# Path to the MediaPipe hand landmarker model in this project folder.
MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")
DOTA_APP_ID = "570"
DOTA_STEAM_URI = f"steam://run/{DOTA_APP_ID}"
STEAM_EXE_PATH = r"C:\Program Files (x86)\Steam\Steam.exe"
CLOSE_AFTER_OPEN_SECONDS = 1

# Finger landmark numbers:
# thumb tip = 4, index tip = 8, middle tip = 12, ring tip = 16, pinky tip = 20
THUMB_TIP = 4
THUMB_IP = 3
INDEX_TIP = 8
INDEX_PIP = 6
MIDDLE_TIP = 12
MIDDLE_PIP = 10
RING_TIP = 16
RING_PIP = 14
PINKY_TIP = 20
PINKY_PIP = 18

# Hold the same gesture this many seconds before running its action.
GESTURE_HOLD_SECONDS = 1
dota_start_time = 0
dota_action_done = False


def open_dota_2():
    """Open Dota 2 through Steam without blocking this app."""
    try:
        if webbrowser.open(DOTA_STEAM_URI, new=0, autoraise=False):
            return True
    except webbrowser.Error as error:
        print(f"Steam URI did not open through the default browser: {error}")

    try:
        popen_options = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            popen_options["creationflags"] = subprocess.CREATE_NO_WINDOW

        subprocess.Popen([STEAM_EXE_PATH, "-applaunch", DOTA_APP_ID], **popen_options)
        return True
    except OSError as error:
        print(f"Could not open Dota 2. Check that Steam is installed: {error}")
        return False


def get_hand_label(detection_result, hand_index):
    """Return Left or Right for one detected hand."""
    if not detection_result.handedness or hand_index >= len(detection_result.handedness):
        return "Unknown"

    return detection_result.handedness[hand_index][0].category_name


def is_finger_open(hand_landmarks, tip_index, pip_index):
    """Return True when a finger is extended upward on the camera image."""
    return hand_landmarks[tip_index].y < hand_landmarks[pip_index].y


def is_thumb_open(hand_landmarks, hand_label):
    """Return True when the thumb is extended sideways."""
    thumb_tip_x = hand_landmarks[THUMB_TIP].x
    thumb_ip_x = hand_landmarks[THUMB_IP].x

    if hand_label == "Right":
        return thumb_tip_x > thumb_ip_x

    return thumb_tip_x < thumb_ip_x


def is_dota_time(hand_landmarks, hand_label):
    """Detect only the Dota Time gesture: thumb and pinky open, others closed."""
    return (
        is_thumb_open(hand_landmarks, hand_label)
        and not is_finger_open(hand_landmarks, INDEX_TIP, INDEX_PIP)
        and not is_finger_open(hand_landmarks, MIDDLE_TIP, MIDDLE_PIP)
        and not is_finger_open(hand_landmarks, RING_TIP, RING_PIP)
        and is_finger_open(hand_landmarks, PINKY_TIP, PINKY_PIP)
    )


def run_dota_action(dota_time_detected):
    """Open Dota after the Dota Time gesture is held long enough."""
    global dota_start_time, dota_action_done

    now = time.time()

    if not dota_time_detected:
        dota_start_time = 0
        dota_action_done = False
        return False

    if dota_start_time == 0:
        dota_start_time = now
        return False

    # Do nothing until the gesture has been held long enough.
    if now - dota_start_time < GESTURE_HOLD_SECONDS:
        return False

    # Do the action only once for each held gesture.
    if dota_action_done:
        return False

    action_started = open_dota_2()
    dota_action_done = True
    return action_started


def detect_dota_time(detection_result):
    """Return True when any detected hand is making the Dota Time gesture."""
    for hand_index, hand_landmarks in enumerate(detection_result.hand_landmarks):
        hand_label = get_hand_label(detection_result, hand_index)
        if is_dota_time(hand_landmarks, hand_label):
            return True

    return False


def main():
    """Run real-time hand detection from the webcam."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Could not find model file: {MODEL_PATH}")

    # Create the MediaPipe hand detector.
    base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    # Open webcam 0. Change this number if you have more than one camera.
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Could not open webcam.")

    # Make the camera image bigger and clearer.
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    with vision.HandLandmarker.create_from_options(options) as detector:
        while True:
            success, frame = camera.read()
            if not success:
                print("Could not read frame from webcam.")
                break

            # Flip the frame so it behaves like a mirror.
            frame = cv2.flip(frame, 1)

            # MediaPipe expects RGB images, while OpenCV reads BGR images.
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # VIDEO mode needs a timestamp in milliseconds for tracking.
            timestamp_ms = int(time.time() * 1000)
            detection_result = detector.detect_for_video(mp_image, timestamp_ms)

            dota_time_detected = detect_dota_time(detection_result)
            action_started = run_dota_action(dota_time_detected)
            if action_started:
                time.sleep(CLOSE_AFTER_OPEN_SECONDS)
                break

    camera.release()


if __name__ == "__main__":
    main()
