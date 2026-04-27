import streamlit as st
import pickle
import json
import numpy as np
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords', quiet=True)

# ── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="Fake News Detector",
    page_icon="🔍",
    layout="centered"
)

# ── Load Models — version=2 se cache force reload hoga ───
@st.cache_resource(hash_funcs={"builtins.int": lambda x: x})
def load_models(version=2):
    import tensorflow as tf
    tf.keras.backend.clear_session()

    # LSTM + Tokenizer
    lstm = tf.keras.models.load_model('models/lstm_model.h5')
    with open('models/lstm_tokenizer.pkl', 'rb') as f:
        tokenizer = pickle.load(f)

    # MAX_LEN config
    with open('models/config.json', 'r') as f:
        config = json.load(f)
    max_len = config['MAX_LEN']

    # Random Forest + Vectorizer
    with open('models/rf_model.pkl', 'rb') as f:
        rf_model = pickle.load(f)
    with open('models/tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    print(f"✅ Models loaded! MAX_LEN={max_len}")
    return lstm, tokenizer, max_len, rf_model, vectorizer

# ── Predict Functions ─────────────────────────────────────
def predict_lstm(text, model, tokenizer, max_len):
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    # Raw text use karo
    seq   = tokenizer.texts_to_sequences([text])
    pad   = pad_sequences(seq, maxlen=max_len,
                          padding='post', truncating='post')
    prob  = model.predict(pad, verbose=0)[0][0]
    label = 'REAL' if prob > 0.5 else 'FAKE'
    conf  = float(prob) if label == 'REAL' else float(1 - prob)
    return label, conf

def predict_rf(text, model, vectorizer):
    import re
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    stop_words = set(stopwords.words('english'))
    tokens = [w for w in text.split() if w not in stop_words]
    clean = ' '.join(tokens)
    vec   = vectorizer.transform([clean])
    label = model.predict(vec)[0]
    prob  = max(model.predict_proba(vec)[0])
    return label, float(prob)

# ── UI ────────────────────────────────────────────────────
st.title("🔍 Fake News Detector")
st.caption("LSTM Deep Learning + Random Forest ML Model")
st.markdown("---")

# Model Selection
model_choice = st.radio(
    "Select Model:",
    ["🧠 LSTM (Deep Learning)", "🌲 Random Forest (ML)"],
    horizontal=True
)

# News Input
st.markdown("### 📰 Enter News Article")

# Dataset se sample articles
sample_options = {
    "Select a sample...": "",
    "✅ REAL News 1": "WASHINGTON (Reuters) - U.S. President Donald Trump removed his chief strategist Steve Bannon from the National Security Council on Wednesday, reversing his controversial decision early this year to give Bannon a regular seat at NSC meetings.",
    "✅ REAL News 2": "Reuters - Puerto Rico Governor Ricardo Rossello said on Wednesday he expected the federal government to waive the Jones Act, which would lift restrictions on ships that can provide aid to the island after Hurricane Maria.",
    "❌ FAKE News 1": "21st Century Wire says Ben Stein reputable professor from Pepperdine University also of some Hollywood fame appearing in TV shows and films such as Ferris Buellers Day Off made some provocative statements about vaccines.",
    "❌ FAKE News 2": "On Monday Donald Trump once again embarrassed himself and his country by accidentally revealing the source of the extremely classified information he leaked to Russia earlier this month while Republican politicians called a recess.",
}

sample_choice = st.selectbox("Try a sample:", list(sample_options.keys()))
default_text  = sample_options[sample_choice]

news_text = st.text_area(
    "Paste your news article here:",
    value=default_text,
    height=200,
    placeholder="Enter news article here..."
)

word_count = len(news_text.split()) if news_text.strip() else 0
st.caption(f"Word count: {word_count}")

# Predict Button
if st.button("🔍 Check News", use_container_width=True):
    if not news_text.strip():
        st.error("⚠️ Please enter a news article!")
    elif word_count < 10:
        st.warning("⚠️ Please enter at least 10 words!")
    else:
        with st.spinner("Analyzing..."):
            # Load models
            lstm, tokenizer, max_len, rf_model, vectorizer = load_models(version=2)

            # Predict
            if "LSTM" in model_choice:
                label, confidence = predict_lstm(
                    news_text, lstm, tokenizer, max_len)
                model_used = "LSTM"
            else:
                label, confidence = predict_rf(
                    news_text, rf_model, vectorizer)
                model_used = "Random Forest"

        st.markdown("---")

        # Result
        if label == 'REAL':
            st.success("## ✅ REAL NEWS")
        else:
            st.error("## ❌ FAKE NEWS")

        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Result",     label)
        col2.metric("Confidence", f"{confidence*100:.1f}%")
        col3.metric("Model",      model_used)

        # Confidence bar
        st.markdown(f"**Confidence: {confidence*100:.1f}%**")
        st.progress(confidence)

        # Tips
        if label == 'FAKE':
            st.warning("""
            **⚠️ Tips to verify:**
            - Check trusted sources (BBC, Reuters)
            - Search on fact-checking sites
            - Look for author credentials
            """)

st.markdown("---")
st.caption("Based on: Fake News Detection using LSTM | ICDSAC 2023 | VIT Pune")