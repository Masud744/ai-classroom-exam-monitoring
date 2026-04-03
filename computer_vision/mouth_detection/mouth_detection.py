import cv2
import mediapipe as mp
import numpy as np
from collections import deque

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()

MOUTH = [61, 81, 13, 311, 308, 402, 14, 178]

mar_history = deque(maxlen=10)

def mouth_aspect_ratio(mouth_points):
    A = np.linalg.norm(mouth_points[1] - mouth_points[7])
    B = np.linalg.norm(mouth_points[2] - mouth_points[6])
    C = np.linalg.norm(mouth_points[3] - mouth_points[5])
    D = np.linalg.norm(mouth_points[0] - mouth_points[4])
    mar = (A + B + C) / (2.0 * D)
    return mar

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    h, w, _ = frame.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            mouth_points = []

            for idx in MOUTH:
                x = int(face_landmarks.landmark[idx].x * w)
                y = int(face_landmarks.landmark[idx].y * h)
                mouth_points.append([x, y])
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            mouth_points = np.array(mouth_points)
            mar = mouth_aspect_ratio(mouth_points)

            mar_history.append(mar)

            if len(mar_history) == 10:
                mar_var = np.var(mar_history)

                if mar_var > 0.002:
                    text = "Talking"
                elif mar > 0.5:
                    text = "Mouth Open"
                else:
                    text = "Mouth Closed"
            else:
                text = "Detecting..."

            cv2.putText(frame, text, (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Mouth Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()