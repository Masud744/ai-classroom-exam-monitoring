import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import threading
import requests
import time
import tkinter as tk
import sys
import os
from ultralytics import YOLO

if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_PATH, 'computer_vision'))

from computer_vision.behavior_analysis.attention_score import AttentionScorer
from computer_vision.behavior_analysis.suspicious_score import SuspiciousScorer

# ─── Login Window ─────────────────────────────────────────────────────────────

API_URL = os.getenv("API_URL", "http://localhost:8000/api")
FALLBACK_API_URL = "https://ai-classroom-exam-monitoring.onrender.com/api"

def get_student_credentials():
    result = {"email": None, "name": None, "camera_source": 0, "success": False}

    root = tk.Tk()
    root.title("ProctorAI — Login")
    root.geometry("400x380")
    root.configure(bg="#0a0a0f")
    root.resizable(False, False)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 200
    y = (root.winfo_screenheight() // 2) - 190
    root.geometry(f"+{x}+{y}")

    tk.Label(root, text="ProctorAI", fg="#00d4ff", bg="#0a0a0f",
             font=("Arial", 14, "bold")).pack(pady=(20, 2))
    tk.Label(root, text="Student Monitoring Login", fg="#666666", bg="#0a0a0f",
             font=("Arial", 10)).pack(pady=(0, 15))

    tk.Label(root, text="EMAIL", fg="#888888", bg="#0a0a0f",
             font=("Arial", 8)).pack(anchor="w", padx=40)
    email_var = tk.StringVar()
    tk.Entry(root, textvariable=email_var, bg="#12121a", fg="white",
             insertbackground="white", relief="flat",
             font=("Arial", 11), width=30).pack(padx=40, pady=(2, 10), ipady=5)

    tk.Label(root, text="PASSWORD", fg="#888888", bg="#0a0a0f",
             font=("Arial", 8)).pack(anchor="w", padx=40)
    pass_var = tk.StringVar()
    pass_entry = tk.Entry(root, textvariable=pass_var, show="*",
                          bg="#12121a", fg="white", insertbackground="white",
                          relief="flat", font=("Arial", 11), width=30)
    pass_entry.pack(padx=40, pady=(2, 10), ipady=5)

    tk.Label(root, text="CAMERA SOURCE (0 for Webcam or IP URL)", fg="#888888", bg="#0a0a0f",
             font=("Arial", 8)).pack(anchor="w", padx=40)
    camera_var = tk.StringVar(value="http://172.16.115.203:8080/video")
    camera_entry = tk.Entry(root, textvariable=camera_var,
                            bg="#12121a", fg="white", insertbackground="white",
                            relief="flat", font=("Arial", 10), width=30)
    camera_entry.pack(padx=40, pady=(2, 12), ipady=5)

    msg_label = tk.Label(root, text="", fg="#f87171", bg="#0a0a0f",
                         font=("Arial", 9))
    msg_label.pack()

    def do_login():
        email    = email_var.get().strip()
        password = pass_var.get().strip()
        camera   = camera_var.get().strip() or "0"
        if not email or not password:
            msg_label.config(text="Please fill all fields", fg="#f87171")
            return
        try:
            msg_label.config(text="Connecting to server...", fg="#00d4ff")
            root.update()
            
            # Try local API first, fallback to Render
            target_url = f"{API_URL}/auth/login"
            try:
                res = requests.post(target_url, json={"email": email, "password": password}, timeout=3)
            except Exception:
                target_url = f"{FALLBACK_API_URL}/auth/login"
                res = requests.post(target_url, json={"email": email, "password": password}, timeout=25)

            try:
                data = res.json()
            except Exception:
                data = {}
            if res.ok and "user" in data:
                role = data["user"].get("user_metadata", {}).get("role", "student")
                if role != "student":
                    msg_label.config(text="Only students can use this app", fg="#f87171")
                    return
                result["email"]         = email
                result["name"]          = data["user"].get("user_metadata", {}).get("full_name", email)
                result["camera_source"] = camera
                result["success"]       = True
                root.destroy()
            else:
                err_detail = data.get("detail", "Invalid email or password")
                msg_label.config(text=err_detail, fg="#f87171")
        except requests.exceptions.Timeout:
            msg_label.config(text="Server timeout. Try again.", fg="#f87171")
        except Exception as e:
            msg_label.config(text="Connection error. Try again.", fg="#f87171")

    btn = tk.Button(root, text="Start Monitoring", command=do_login,
                    bg="#00d4ff", fg="black", font=("Arial", 11, "bold"),
                    relief="flat", cursor="hand2", width=22, pady=6)
    btn.pack(pady=8)
    pass_entry.bind("<Return>", lambda e: do_login())
    camera_entry.bind("<Return>", lambda e: do_login())

    root.mainloop()
    return result


# ─── Login ────────────────────────────────────────────────────────────────────
creds = get_student_credentials()
if not creds["success"]:
    exit()

STUDENT_ID    = creds["email"]
STUDENT_NAME  = creds["name"]
CAMERA_SOURCE = creds.get("camera_source", 0)
if isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.isdigit():
    CAMERA_SOURCE = int(CAMERA_SOURCE)

# ─── Debug Print ──────────────────────────────────────────────────────────
print(f"BASE_PATH: {BASE_PATH}")
import os
yolo_path = os.path.join(BASE_PATH, "yolov8n.pt")
print(f"YOLO model path: {yolo_path}")
print(f"YOLO file exists: {os.path.exists(yolo_path)}")

# ─── MediaPipe Setup ──────────────────────────────────────────────────────────
mp_face_detection = mp.solutions.face_detection
mp_face_mesh      = mp.solutions.face_mesh

face_detection = mp_face_detection.FaceDetection(
    model_selection=0, min_detection_confidence=0.5
)
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False, max_num_faces=2,
    min_detection_confidence=0.5, min_tracking_confidence=0.5
)

yolo_model = YOLO(os.path.join(BASE_PATH, "yolov8n.pt"))

LEFT_EYE      = [33, 160, 158, 133, 153, 144]
RIGHT_EYE     = [362, 385, 387, 263, 373, 380]
MOUTH         = [61, 81, 13, 311, 308, 402, 14, 178]
HEAD_POSE_IDS = [33, 263, 1, 61, 291, 199]

mar_history       = deque(maxlen=10)
attention_scorer  = AttentionScorer()
suspicious_scorer = SuspiciousScorer()

phone_detected_global = False
phone_boxes_global    = []
yolo_frame            = None
yolo_lock             = threading.Lock()


# ─── Threaded Camera with Dynamic Auto-Reconnect ─────────────────────────────
class ThreadedCamera:
    def __init__(self, source):
        self.source = source
        self.ret = False
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        self.cap = None
        self._connect()
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def _connect(self):
        try:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
            self.cap = cv2.VideoCapture(self.source)
            if isinstance(self.source, str) and self.source.startswith("http"):
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
            return self.cap.isOpened()
        except Exception:
            return False

    def update(self):
        failed_count = 0
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                if not self._connect():
                    time.sleep(1)
                    continue
            ret, frame = self.cap.read()
            if not ret or frame is None:
                failed_count += 1
                if failed_count > 15:
                    self._connect()
                    failed_count = 0
                    time.sleep(0.5)
                else:
                    time.sleep(0.04)
                continue
            failed_count = 0
            with self.lock:
                self.ret = True
                self.frame = frame
            time.sleep(0.005)

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()

    def isOpened(self):
        return True

    def release(self):
        self.stopped = True
        if hasattr(self, 'thread'):
            self.thread.join(timeout=0.5)
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass


# ─── YOLO Thread ──────────────────────────────────────────────────────────────
def yolo_worker():
    global phone_detected_global, phone_boxes_global, yolo_frame
    while True:
        with yolo_lock:
            frame = yolo_frame.copy() if yolo_frame is not None else None
        if frame is None:
            time.sleep(0.02)
            continue
        try:
            results = yolo_model(frame, verbose=False, conf=0.4, imgsz=320)
            detected = False
            boxes = []
            for r in results:
                for box in r.boxes:
                    if yolo_model.names[int(box.cls[0])] == "cell phone":
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        box_area   = (x2 - x1) * (y2 - y1)
                        frame_area = frame.shape[0] * frame.shape[1]
                        if box_area >= frame_area * 0.02:
                            detected = True
                            boxes.append((x1, y1, x2, y2))
            phone_detected_global = detected
            phone_boxes_global    = boxes
        except Exception:
            pass
        time.sleep(0.06)


yolo_thread = threading.Thread(target=yolo_worker, daemon=True)
yolo_thread.start()


# ─── Helper Functions ─────────────────────────────────────────────────────────
def eye_aspect_ratio(eye_points):
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    return (A + B) / (2.0 * C)


def mouth_aspect_ratio(mouth_points):
    A = np.linalg.norm(mouth_points[1] - mouth_points[7])
    B = np.linalg.norm(mouth_points[2] - mouth_points[6])
    C = np.linalg.norm(mouth_points[3] - mouth_points[5])
    D = np.linalg.norm(mouth_points[0] - mouth_points[4])
    return (A + B + C) / (2.0 * D)


def get_head_pose(face_landmarks, img_w, img_h):
    face_2d, face_3d = [], []
    for idx, lm in enumerate(face_landmarks.landmark):
        if idx in HEAD_POSE_IDS:
            x, y = int(lm.x * img_w), int(lm.y * img_h)
            face_2d.append([x, y])
            face_3d.append([x, y, lm.z])
    if len(face_2d) < 6:
        return True
    face_2d = np.array(face_2d, dtype=np.float64)
    face_3d = np.array(face_3d, dtype=np.float64)
    focal_length = img_w
    cam_matrix = np.array([
        [focal_length, 0,            img_w / 2],
        [0,            focal_length, img_h / 2],
        [0,            0,            1         ]
    ])
    dist_matrix = np.zeros((4, 1), dtype=np.float64)
    success, rot_vec, _ = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
    if not success:
        return True
    rmat, _ = cv2.Rodrigues(rot_vec)
    angles, *_ = cv2.RQDecomp3x3(rmat)
    return (-15 <= angles[1] * 360 <= 15) and (-15 <= angles[0] * 360 <= 15)


def draw_panel(frame, flags, attention_score, suspicious_score):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (260, frame.shape[0]), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, "ProctorAI", (10, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 200, 255), 1)
    cv2.putText(frame, STUDENT_NAME[:28], (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)
    cv2.line(frame, (10, 60), (248, 60), (60, 60, 60), 1)
    y = 82
    for label, ok in flags:
        color = (80, 220, 80) if ok else (60, 60, 220)
        cv2.putText(frame, f"* {label}", (14, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1)
        y += 24
    y += 8
    cv2.putText(frame, f"Attention: {attention_score}", (12, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    y += 18
    cv2.rectangle(frame, (12, y), (248, y + 16), (50, 50, 50), -1)
    filled = int(236 * attention_score / 100)
    cv2.rectangle(frame, (12, y), (12 + filled, y + 16), (0, 200, 255), -1)
    cv2.rectangle(frame, (12, y), (248, y + 16), (100, 100, 100), 1)
    y += 26
    cv2.putText(frame, f"Suspicious: {suspicious_score}", (12, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    y += 18
    color = (60, 60, 220) if suspicious_score >= 50 else (80, 220, 80)
    cv2.rectangle(frame, (12, y), (248, y + 16), (50, 50, 50), -1)
    filled = int(236 * suspicious_score / 100)
    cv2.rectangle(frame, (12, y), (12 + filled, y + 16), color, -1)
    cv2.rectangle(frame, (12, y), (248, y + 16), (100, 100, 100), 1)


def send_log(attention_score, suspicious_score, phone_detected,
             talking, eyes_closed, looking_forward,
             face_count, multiple_faces, face_present):
    payload = {
        "student_id":      STUDENT_ID,
        "student_name":    STUDENT_NAME,
        "attention_score": attention_score,
        "suspicious_score": suspicious_score,
        "phone_detected":  bool(phone_detected),
        "talking":         bool(talking),
        "eyes_closed":     bool(eyes_closed),
        "looking_forward": bool(looking_forward),
        "face_count":      int(face_count),
        "multiple_faces":  bool(multiple_faces),
        "face_present":    bool(face_present)
    }
    try:
        requests.post(f"{API_URL}/log", json=payload, timeout=3)
    except Exception:
        try:
            requests.post(f"{FALLBACK_API_URL}/log", json=payload, timeout=5)
        except Exception:
            pass
    except:
        pass


# ─── Main Loop ────────────────────────────────────────────────────────────────
last_log_time = time.time()
print(f"Connecting to camera: {CAMERA_SOURCE} ...")
cap = ThreadedCamera(CAMERA_SOURCE)

window_title = f"ProctorAI - {STUDENT_NAME}"
try:
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
    cv2.resizeWindow(window_title, 640, 360)
except Exception:
    try:
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 640, 360)
    except Exception:
        pass

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        time.sleep(0.005)
        continue

    # Auto downscale to 640px for ultra-smooth FPS & low CPU
    h_orig, w_orig = frame.shape[:2]
    if w_orig > 640:
        new_w = 640
        new_h = int(h_orig * (new_w / w_orig))
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    h, w = frame.shape[:2]
    rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    with yolo_lock:
        yolo_frame = frame.copy()

    # Face detection
    det_results    = face_detection.process(rgb)
    face_present   = False
    multiple_faces = False
    face_count     = 0
    if det_results.detections:
        face_present   = True
        face_count     = len(det_results.detections)
        multiple_faces = face_count > 1
        for det in det_results.detections:
            bb = det.location_data.relative_bounding_box
            bx, by = int(bb.xmin * w), int(bb.ymin * h)
            bw, bh = int(bb.width * w), int(bb.height * h)
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 200, 255), 2)

    # Face mesh (only compute when face is present for max FPS)
    looking_forward = face_present
    eyes_closed     = False
    talking         = False
    if face_present:
        mesh_results = face_mesh.process(rgb)
        if mesh_results.multi_face_landmarks:
            for face_lm in mesh_results.multi_face_landmarks:
                looking_forward = get_head_pose(face_lm, w, h)
                left_pts  = np.array([[int(face_lm.landmark[i].x * w),
                                       int(face_lm.landmark[i].y * h)] for i in LEFT_EYE])
                right_pts = np.array([[int(face_lm.landmark[i].x * w),
                                       int(face_lm.landmark[i].y * h)] for i in RIGHT_EYE])
                ear = (eye_aspect_ratio(left_pts) + eye_aspect_ratio(right_pts)) / 2.0
                eyes_closed = ear < 0.20
                mouth_pts = np.array([[int(face_lm.landmark[i].x * w),
                                       int(face_lm.landmark[i].y * h)] for i in MOUTH])
                mar_history.append(mouth_aspect_ratio(mouth_pts))
                if len(mar_history) == 10:
                    talking = np.var(mar_history) > 0.002
                break

    # Phone detection
    phone_detected = phone_detected_global
    if phone_detected:
        for (x1, y1, x2, y2) in phone_boxes_global:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 220), 2)
            cv2.putText(frame, "PHONE", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2)

    # Scores
    attention_score  = attention_scorer.calculate(
        looking_forward, eyes_closed, talking,
        phone_detected, face_present, multiple_faces
    )
    suspicious_score = suspicious_scorer.calculate(
        looking_forward, eyes_closed, talking,
        phone_detected, face_present, multiple_faces
    )

    # Log every 5 seconds
    current_time = time.time()
    if current_time - last_log_time >= 5:
        threading.Thread(
            target=send_log,
            args=(attention_score, suspicious_score, phone_detected,
                  talking, eyes_closed, looking_forward,
                  face_count, multiple_faces, face_present),
            daemon=True
        ).start()
        last_log_time = current_time

    flags = [
        ("Face present",    face_present),
        ("Single person",   not multiple_faces),
        ("Looking forward", looking_forward),
        ("Eyes open",       not eyes_closed),
        ("Not talking",     not talking),
        ("No phone",        not phone_detected),
        (f"Faces: {face_count}", True),
    ]
    draw_panel(frame, flags, attention_score, suspicious_score)

    if suspicious_score >= 50:
        cv2.rectangle(frame, (260, 0), (w, 36), (0, 0, 180), -1)
        cv2.putText(frame, "SUSPICIOUS BEHAVIOR DETECTED", (268, 24),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow(window_title, frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()