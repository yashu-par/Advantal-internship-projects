# ====================================================
# yolo_detector.py — Universal detector for ANY image
# No hardcoded per-class thresholds
# Works on any random real photo
# ====================================================

from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import os


BACKGROUND = {
    "dining table", "desk", "floor", "wall", "ceiling",
    "couch", "sofa", "bed", "bench", "background"
}


def _iou(b1, b2):
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1: return 0.0
    inter = (x2-x1)*(y2-y1)
    a1 = (b1[2]-b1[0])*(b1[3]-b1[1])
    a2 = (b2[2]-b2[0])*(b2[3]-b2[1])
    return inter/(a1+a2-inter+1e-6)


def detect_with_yolo(image: Image.Image):
    """
    Universal detection — works on ANY real photo.

    Strategy:
    - Run YOLO at conf=0.15 (low) to catch everything
    - Remove same-label duplicates
    - Remove background/surface classes IF other objects found
    - NO per-class hardcoded thresholds — model decides
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))
    model = None
    for name in ["yolov8x.pt","yolov8l.pt","yolov8m.pt","yolov8s.pt"]:
        p = os.path.join(base_dir, name)
        if os.path.exists(p):
            model = YOLO(p)
            break
    if model is None:
        model = YOLO("yolov8m.pt")

    W, H = image.size

    # Single clean pass — YOLO's own NMS handles most duplicates
    # conf=0.15: low enough to catch small/partial objects
    # iou=0.5: standard overlap threshold
    results = model(
        image,
        conf=0.15,
        iou=0.50,
        imgsz=1280,
        augment=True,       # Test-Time Augmentation = better accuracy
        agnostic_nms=True,  # cross-class NMS — removes overlapping boxes
        verbose=False
    )

    raw = []
    for box in results[0].boxes:
        lbl  = model.names[int(box.cls[0])]
        conf = float(box.conf[0])
        x1,y1,x2,y2 = [int(v) for v in box.xyxy[0]]
        area = (x2-x1)*(y2-y1)
        # Skip truly microscopic boxes (< 0.3% of image)
        if area < 0.003 * W * H:
            continue
        raw.append({"label":lbl, "conf":conf, "box":(x1,y1,x2,y2)})

    # Sort by confidence
    raw.sort(key=lambda x: x["conf"], reverse=True)

    # Remove same-label duplicates that YOLO missed
    # (can happen across two augment passes)
    deduped = []
    for cand in raw:
        dup = False
        for kept in deduped:
            if cand["label"] == kept["label"] and _iou(cand["box"], kept["box"]) > 0.45:
                dup = True
                break
        if not dup:
            deduped.append(cand)

    # Suppress background classes if real objects exist
    non_bg = [d for d in deduped if d["label"].lower() not in BACKGROUND]
    bg     = [d for d in deduped if d["label"].lower() in BACKGROUND]
    final  = non_bg if non_bg else bg

    detections = [
        {"object": d["label"], "confidence": round(d["conf"]*100, 2), "box": d["box"]}
        for d in final
    ]

    # Draw
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except Exception:
            font = ImageFont.load_default()

    COLORS = [
        "#FF4444","#44BB44","#4488FF","#FF8800","#AA44FF",
        "#00BBBB","#FF44AA","#886600","#0044FF","#FF0088",
        "#00CC66","#CC6600","#FF6600","#0099CC","#99CC00"
    ]

    for i, d in enumerate(final):
        x1,y1,x2,y2 = d["box"]
        color = COLORS[i % len(COLORS)]
        text  = f"{d['label']} {d['conf']:.2f}"
        draw.rectangle([x1,y1,x2,y2], outline=color, width=3)
        try:
            bb = draw.textbbox((0,0), text, font=font)
            tw,th = bb[2]-bb[0], bb[3]-bb[1]
        except Exception:
            tw,th = len(text)*9, 18
        pad = 4
        ly = y1-th-pad*2
        if ly < 0: ly = y1+2
        draw.rectangle([x1,ly,x1+tw+pad*2,ly+th+pad*2], fill=color)
        draw.text((x1+pad,ly+pad), text, fill="white", font=font)

    return detections, annotated