
# -*- coding: utf-8 -*-
import cv2
import numpy as np
from tensorflow.keras.models import load_model
import json
import mediapipe as mp
import time

model = load_model(r"C:\Users\yasha\OneDrive\Desktop\asl_project\asl_landmark_model.h5")
with open(r"C:\Users\yasha\OneDrive\Desktop\asl_project\classes.json", "r") as f:
    classes = json.load(f)

print("Model loaded!")
print("=" * 50)
print("CONTROLS:")
print("  SPACE sign  = add space between words")
print("  DEL sign    = delete last letter")
print("  Q key       = quit")
print("=" * 50)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)

pred_history = []
SMOOTH = 7
last_added = ""
last_add_time = 0
ADD_DELAY = 2        # 2 sec hold karo letter add karne ke liye

sentence = []        # sentence ke letters yahan store honge
hold_start = {}      # kab se hold kar raha hai

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    current_time = time.time()

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:

            mp_draw.draw_landmarks(
                frame, hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
            )

            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
            coords = np.array(coords).reshape(1, -1)

            prediction = model.predict(coords, verbose=0)
            predicted_idx = np.argmax(prediction)

            pred_history.append(predicted_idx)
            if len(pred_history) > SMOOTH:
                pred_history.pop(0)

            smooth_idx = max(set(pred_history), key=pred_history.count)
            smooth_class = classes[smooth_idx]
            smooth_conf = prediction[0][smooth_idx] * 100

            # Hold timer — kitna time se same letter dikh raha hai
            if smooth_class not in hold_start:
                hold_start = {smooth_class: current_time}

            hold_duration = current_time - hold_start.get(smooth_class, current_time)
            time_left = max(0, ADD_DELAY - hold_duration)

            # Letter add karo jab 2 sec hold ho
            if hold_duration >= ADD_DELAY and smooth_conf > 70:
                if smooth_class != last_added or current_time - last_add_time >= ADD_DELAY:

                    if smooth_class == "space":
                        sentence.append(" ")
                        print(f"[SPACE added]")
                    elif smooth_class == "del":
                        if sentence:
                            removed = sentence.pop()
                            print(f"[Deleted: {removed}]")
                    else:
                        sentence.append(smooth_class)
                        print(f"Letter added: {smooth_class}")

                    full_sentence = "".join(sentence)
                    print(f"Sentence: {full_sentence}")
                    print("-" * 40)

                    last_added = smooth_class
                    last_add_time = current_time
                    hold_start = {}

            # Bounding box
            x_list = [lm.x * w for lm in hand_landmarks.landmark]
            y_list = [lm.y * h for lm in hand_landmarks.landmark]
            x1 = max(0, int(min(x_list)) - 30)
            y1 = max(0, int(min(y_list)) - 30)
            x2 = min(w, int(max(x_list)) + 30)
            y2 = min(h, int(max(y_list)) + 30)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

            # Hold progress bar
            progress = min(1.0, hold_duration / ADD_DELAY)
            bar_width = int(progress * (x2 - x1))
            cv2.rectangle(frame, (x1, y2 + 5), (x2, y2 + 20), (50, 50, 50), -1)
            cv2.rectangle(frame, (x1, y2 + 5), (x1 + bar_width, y2 + 20), (0, 255, 0), -1)
            cv2.putText(frame, f"Hold: {hold_duration:.1f}s / {ADD_DELAY}s",
                        (x1, y2 + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            # Current letter
            color = (0, 255, 0) if smooth_conf > 70 else (0, 165, 255)
            cv2.putText(frame, f"{smooth_class}  {smooth_conf:.1f}%",
                        (x1, y1 - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)

            # Top 3
            top3_idx = np.argsort(prediction[0])[::-1][:3]
            for i, idx in enumerate(top3_idx):
                conf = prediction[0][idx] * 100
                cv2.putText(frame, f"{i+1}. {classes[idx]}: {conf:.1f}%",
                            (10, 160 + i * 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

    else:
        pred_history.clear()
        hold_start = {}
        cv2.putText(frame, "Show your hand!", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Sentence display on screen
    full_sentence = "".join(sentence)

    # Background box for sentence
    cv2.rectangle(frame, (0, 0), (w, 55), (30, 30, 30), -1)
    cv2.putText(frame, f"Sentence: {full_sentence}",
                (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

    # Controls info
    cv2.rectangle(frame, (0, h - 30), (w, h), (30, 30, 30), -1)
    cv2.putText(frame, "SPACE=space  DEL=delete  Q=quit",
                (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)

    cv2.imshow("ASL Sentence Builder", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        print("=" * 50)
        print(f"Final sentence: {full_sentence}")
        print("=" * 50)
        break

cap.release()
cv2.destroyAllWindows()
