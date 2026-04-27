
import cv2
import numpy as np
from tensorflow.keras.models import load_model
import json
import mediapipe as mp

model = load_model(r'C:\Users\yasha\OneDrive\Desktop\asl_project\asl_model.h5')
with open(r'C:\Users\yasha\OneDrive\Desktop\asl_project\classes.json', 'r') as f:
    classes = json.load(f)

# MediaPipe new way
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Old style bhi try karte hain
import mediapipe as mp
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

print("Ready! Q dabao band karne ke liye")
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame, hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=4),
                mp_draw.DrawingSpec(color=(255,0,0), thickness=2)
            )

            x_list = [lm.x * w for lm in hand_landmarks.landmark]
            y_list = [lm.y * h for lm in hand_landmarks.landmark]

            x1 = max(0, int(min(x_list)) - 30)
            y1 = max(0, int(min(y_list)) - 30)
            x2 = min(w, int(max(x_list)) + 30)
            y2 = min(h, int(max(y_list)) + 30)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            roi_resized = cv2.resize(roi, (64, 64))
            roi_normalized = roi_resized / 255.0
            roi_input = np.expand_dims(roi_normalized, axis=0)

            prediction = model.predict(roi_input, verbose=0)
            predicted_idx = np.argmax(prediction)
            confidence = prediction[0][predicted_idx] * 100
            predicted_class = classes[predicted_idx]

            if confidence > 60:
                color = (0, 255, 0)
                label = f"{predicted_class}  {confidence:.1f}%"
            else:
                color = (0, 0, 255)
                label = f"? ({confidence:.1f}%)"

            cv2.putText(frame, label, (x1, y1 - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    else:
        cv2.putText(frame, "Haath dikhao!", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("ASL Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
