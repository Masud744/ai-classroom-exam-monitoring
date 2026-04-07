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

def get_student_credentials():
    result = {"email": None, "name": None, "success": False}

    root = tk.Tk()
    root.title("AI Exam Monitor — Login")
    root.geometry("380x300")
    root.configure(bg="#0a0a0f")
    root.resizable(False, False)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 190
    y = (root.winfo_screenheight() // 2) - 150
    root.geometry(f"+{x}+{y}")

    tk.Label(root, text="AI EXAM MONITOR", fg="#00d4ff", bg="#0a0a0f",
             font=("Arial", 14, "bold")).pack(pady=(24, 4))
    tk.Label(root, text="Student Monitoring Login", fg="#666666", bg="#0a0a0f",
             font=("Arial", 10)).pack(pady=(0, 20))

    tk.Label(root, text="EMAIL", fg="#888888", bg="#0a0a0f",
             font=("Arial", 8)).pack(anchor="w", padx=40)
    email_var = tk.StringVar()
    tk.Entry(root, textvariable=email_var, bg="#12121a", fg="white",
             insertbackground="white", relief="flat",
             font=("Arial", 11), width=28).pack(padx=40, pady=(2, 12), ipady=6)

    tk.Label(root, text="PASSWORD", fg="#888888", bg="#0a0a0f",
             font=("Arial", 8)).pack(anchor="w", padx=40)
    pass_var = tk.StringVar()
    pass_entry = tk.Entry(root, textvariable=pass_var, show="•",
                          bg="#12121a", fg="white", insertbackground="white",
                          relief="flat", font=("Arial", 11), width=28)
    pass_entry.pack(padx=40, pady=(2, 16), ipady=6)

    msg_label = tk.Label(root, text="", fg="#f87171", bg="#0a0a0f",
                         font=("Arial", 9))
    msg_label.pack()

    def do_login():
        email    = email_var.get().strip()
        password = pass_var.get().strip()
        if not email or not password:
            msg_label.config(text="Please fill all fields", fg="#f87171")
            return
        try:
            msg_label.config(text="Connecting...", fg="#00d4ff")
            root.update()
            res = requests.post(
                "https://ai-classroom-exam-monitoring.onrender.com/api/auth/login",
                json={"email": email, "password": password},
                timeout=20
            )
            data = res.json()
            if res.ok:
                role = data["user"]["user_metadata"].get("role", "student")
                if role != "student":
                    msg_label.config(text="Only students can use this app", fg="#f87171")
                    return
                result["email"]   = email
                result["name"]    = data["user"]["user_metadata"].get("full_name", email)
                result["success"] = True
                root.destroy()
            else:
                msg_label.config(text="Invalid email or password", fg="#f87171")
        except Exception:
            msg_label.config(text="Server error. Try again.", fg="#f87171")

    btn = tk.Button(root, text="Start Monitoring", command=do_login,
                    bg="#00d4ff", fg="black", font=("Arial", 11, "bold"),
                    relief="flat", cursor="hand2", width=22, pady=6)
    btn.pack(pady=8)
    pass_entry.bind("<Return>", lambda e: do_login())

    root.mainloop()
    return result


# ─── Login ────────────────────────────────────────────────────────────────────
creds = get_student_credentials()
if not creds["success"]:
    exit()

STUDENT_ID   = creds["email"]
STUDENT_NAME = creds["name"]

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


# ─── YOLO Thread ──────────────────────────────────────────────────────────────
def yolo_worker():
    global phone_detected_global, phone_boxes_global, yolo_frame
    while True:
        with yolo_lock:
            frame = yolo_frame.copy() if yolo_frame is not None else None
        if frame is None:
            continue
        results = yolo_model(frame, verbose=False, conf=0.4)
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
    cv2.putText(frame, "AI EXAM MONITOR", (10, 32),
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
    color  = (80, 200, 80) if attention_score >= 50 else (60, 60, 220)
    if filled > 0:
        cv2.rectangle(frame, (12, y), (12 + filled, y + 16), color, -1)
    cv2.rectangle(frame, (12, y), (248, y + 16), (100, 100, 100), 1)
    y += 30
    cv2.putText(frame, f"Suspicious: {suspicious_score}", (12, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    y += 18
    cv2.rectangle(frame, (12, y), (248, y + 16), (50, 50, 50), -1)
    filled = int(236 * suspicious_score / 100)
    color  = (80, 200, 80) if suspicious_score < 50 else (60, 60, 220)
    if filled > 0:
        cv2.rectangle(frame, (12, y), (12 + filled, y + 16), color, -1)
    cv2.rectangle(frame, (12, y), (248, y + 16), (100, 100, 100), 1)


def send_log(attention_score, suspicious_score, phone_detected,
             talking, eyes_closed, looking_forward,
             face_count, multiple_faces, face_present):
    try:
        requests.post(
            "https://ai-classroom-exam-monitoring.onrender.com/api/log",
            json={
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
            },
            timeout=5
        )
    except:
        pass


# ─── Main Loop ────────────────────────────────────────────────────────────────
last_log_time = time.time()
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

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

    # Face mesh
    mesh_results    = face_mesh.process(rgb)
    looking_forward = face_present
    eyes_closed     = False
    talking         = False
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

    cv2.imshow("AI Exam Monitoring System", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()