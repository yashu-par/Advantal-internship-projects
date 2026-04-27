import streamlit as st
import joblib
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Load model
model = joblib.load('spam_model.pkl')
tfidf = joblib.load('tfidf_vectorizer.pkl')

nltk.download('stopwords', quiet=True)
ps = PorterStemmer()
stop_words = set(stopwords.words('english'))

# Clean function
def clean_text(text):
    text = text.lower()
    text = re.sub(r'\d+', 'NUM', text)
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    tokens = [ps.stem(w) for w in tokens if w not in stop_words]
    return ' '.join(tokens)

# Phishing keywords
phishing_keywords = ['click this link', 'verify immediately',
                     'account suspended', 'bank account',
                     'http://', 'login now']

# Page config
st.set_page_config(page_title="SMS Spam Detection", page_icon="✉️", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .title { font-size: 2rem; font-weight: bold; color: #2c3e50; }
    .subtitle { font-size: 1rem; color: #7f8c8d; margin-bottom: 20px; }
    .spam-box {
        background-color: #ffe0e0;
        border-left: 6px solid #e74c3c;
        padding: 15px;
        border-radius: 8px;
        font-size: 1.2rem;
        color: #c0392b;
        font-weight: bold;
    }
    .ham-box {
        background-color: #e0ffe0;
        border-left: 6px solid #27ae60;
        padding: 15px;
        border-radius: 8px;
        font-size: 1.2rem;
        color: #1e8449;
        font-weight: bold;
    }
    .footer {
        text-align: center;
        color: #aaa;
        margin-top: 40px;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="title">✉️ SMS Spam Detection</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Check whether a message is Spam or Not</div>', unsafe_allow_html=True)
st.markdown("---")

# Input
message = st.text_input("", placeholder="Enter your message here...")

# Button
if st.button("🔍 Check Spam"):
    if message.strip() == "":
        st.warning("Please enter a message!")
    else:
        message_lower = message.lower()
        phishing_found = any(k in message_lower for k in phishing_keywords)

        if phishing_found:
            st.markdown('<div class="spam-box">🚨 This is a SPAM message!</div>', unsafe_allow_html=True)
        else:
            clean = clean_text(message)
            vec = tfidf.transform([clean])
            pred = model.predict(vec)[0]
            prob = model.predict_proba(vec)[0][1]

            if pred == 1:
                st.markdown(f'<div class="spam-box">🚨 This is a SPAM message! (Confidence: {prob:.2%})</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ham-box">✅ This is NOT Spam! (Confidence: {1-prob:.2%})</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown('<div class="footer">Built with ❤️ using Machine Learning</div>', unsafe_allow_html=True)

#run
#cd "C:\Users\yasha\OneDrive\Desktop\SMS spam Detection\spam_detection"
#streamlit run app.py