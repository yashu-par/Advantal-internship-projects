# ====================================================
# app.py — Object Detection with YOLOv8x
# Run with: streamlit run app.py
# ====================================================

import streamlit as st
from PIL import Image
import io

from yolo_detector import detect_with_yolo


st.set_page_config(
    page_title="Object Detection — YOLOv8",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
.header-blue {
    background: linear-gradient(90deg, #1a3a6b, #2563eb);
    color: white; padding: 14px 24px; border-radius: 12px;
    font-size: 22px; font-weight: bold; margin-bottom: 10px;
}
.result-row {
    background: #1e293b; border-radius: 8px;
    padding: 6px 14px; margin: 4px 0;
    color: #e2e8f0; font-size: 15px;
}
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.title("🔍 Object Detection — YOLOv8")
st.markdown("Upload a real photo — YOLOv8 will detect all **main objects** in the image.")
st.markdown("---")

with st.expander("ℹ️ How it works"):
    st.markdown("""
    **YOLOv8x (Extra-Large Model)**
    - Detects **80 standard object classes** from COCO dataset
    - Runs **two detection passes** (image sizes 1280 + 960) for better accuracy
    - Removes tiny detections (keyboard keys, buttons, noise)
    - Removes sub-parts detected inside a larger object (e.g. keys inside laptop)
    - Only shows **main objects** with clear bounding boxes
    
    **What it can detect:** person, car, bicycle, laptop, phone, book, bottle,
    chair, table, watch, scissors, bag, dog, cat, cup, and 65 more...
    """)

# ---- Upload ----
st.subheader("📸 Upload an Image")
uploaded_file = st.file_uploader("Choose a real photo (JPG, JPEG, PNG)", type=["jpg","jpeg","png"])

if uploaded_file is not None:

    image = Image.open(io.BytesIO(uploaded_file.read()))
    if image.mode != "RGB":
        image = image.convert("RGB")

    st.markdown("---")
    st.subheader("🖼️ Uploaded Image")
    _, col_m, _ = st.columns([1, 2, 1])
    with col_m:
        st.image(image, caption="Original Image", use_container_width=True)

    st.markdown("---")

    if st.button("🚀 Detect Objects!", use_container_width=True):

        with st.spinner("YOLOv8 scanning image (2 passes)... ⏳"):
            detections, annotated_img = detect_with_yolo(image)

        # ---- Results ----
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown('<div class="header-blue">🔵 Detected Objects</div>', unsafe_allow_html=True)
            st.image(annotated_img, caption="YOLOv8 — Detected Objects", use_container_width=True)

        with col2:
            st.markdown("### 📋 Detection Results")
            if detections:
                st.success(f"✅ {len(detections)} main object(s) detected!")
                st.markdown("---")

                sorted_det = sorted(detections, key=lambda x: x["confidence"], reverse=True)
                for i, d in enumerate(sorted_det):
                    conf = int(d["confidence"])
                    # Color bar based on confidence
                    bar_color = "#22c55e" if conf >= 70 else "#f59e0b" if conf >= 40 else "#ef4444"
                    st.markdown(
                        f'<div class="result-row">'
                        f'<b>{i+1}. {d["object"].upper()}</b> — {d["confidence"]}%'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.progress(conf)

                # Summary stats
                st.markdown("---")
                st.markdown("### 📊 Summary")
                avg_conf = round(sum(d["confidence"] for d in detections) / len(detections), 1)
                best     = sorted_det[0]

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Objects", len(detections))
                m2.metric("Avg Confidence", f"{avg_conf}%")
                m3.metric("Top Detection", best["object"].upper())

            else:
                st.warning("⚠️ No objects detected. Try a clearer real photo.")
                st.info("💡 Tips: Use well-lit photos, avoid blur, make sure objects are clearly visible.")

else:
    st.info("👆 Upload a real photo above, then click 'Detect Objects!'")

st.markdown("---")
st.markdown("**Built with Streamlit · YOLOv8x · Ultralytics**")