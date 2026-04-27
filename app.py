import streamlit as st
from groq import Groq
import pandas as pd
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def load_products():
    try:
        with open("products.txt", "r") as f:
            return f.read()
    except:
        return "Product catalog not available."

@st.cache_resource
def load_model():
    df = pd.read_csv("intents_large.csv")
    X = df["text"]
    y = df["intent"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    models = {
        "Naive Bayes": Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2))), ('model', MultinomialNB(alpha=0.1))]),
        "Logistic Regression": Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2))), ('model', LogisticRegression(max_iter=500, C=10))]),
        "Random Forest": Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2))), ('model', RandomForestClassifier(n_estimators=200))]),
        "LinearSVC": Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2))), ('model', LinearSVC(C=10, max_iter=2000))]),
    }
    results = {}
    for name, m in models.items():
        m.fit(X_train, y_train)
        results[name] = accuracy_score(y_test, m.predict(X_test))
    best_name = max(results, key=results.get)
    return models[best_name], best_name

def extract_user_info(user_input):
    text = user_input.lower().strip()
    if "my name is" in text:
        after = text.split("my name is")[1].strip()
        name = after.split()[0].capitalize()
        st.session_state["user_name"] = name
    elif "mera naam" in text:
        parts = text.split("mera naam")
        if len(parts) > 1:
            name = parts[1].strip().split()[0].capitalize()
            st.session_state["user_name"] = name
    elif "call me" in text:
        after = text.split("call me")[1].strip()
        if after:
            name = after.split()[0].capitalize()
            st.session_state["user_name"] = name
    if "i am from" in text:
        after = text.split("i am from")[1].strip()
        city = after.split()[0].capitalize()
        st.session_state["user_city"] = city
    elif "i live in" in text:
        after = text.split("i live in")[1].strip()
        city = after.split()[0].capitalize()
        st.session_state["user_city"] = city

from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("api_key"))
products_catalog = load_products()

def get_response(user_input, best_model):
    intent = best_model.predict([user_input.lower()])[0]
    extract_user_info(user_input)

    user_name = st.session_state.get("user_name", None)
    user_city = st.session_state.get("user_city", None)

    memory = ""
    if user_name:
        memory += f"Customer name: {user_name}\n"
    if user_city:
        memory += f"Customer city: {user_city}\n"
    if not memory:
        memory = "No info known yet."

    product_keywords = ["product", "products", "laptop", "phone", "smartphone",
                        "camera", "watch", "smartwatch", "gaming", "tv", "audio",
                        "earphone", "headphone", "accessories", "iphone", "samsung",
                        "price", "available", "show", "list", "catalog",
                        "what do you have", "kya kya", "items", "sell", "do you have"]

    is_product_query = any(word in user_input.lower() for word in product_keywords)

    if is_product_query:
        product_section = f"ONLY use these exact products, do NOT make up any:\n{products_catalog}"
    else:
        product_section = ""

    order_keywords = ["i want to buy", "i'll take it", "i want it", "place order",
                      "buy this", "order karna", "le leta", "confirm", "yes i want",
                      "book it", "i want to order", "purchase"]

    is_order = any(word in user_input.lower() for word in order_keywords)

    name_str = user_name if user_name else "there"

    prompt = f"""You are ShopBot, a warm friendly assistant for an electronics shop in Bhopal.

Customer Memory:
{memory}

Shop Details:
- Returns within 7 days, refund in 3-5 days
- Open Monday to Saturday, 9 AM to 6 PM
- Located at MG Road, Bhopal

{product_section}

STRICT RULES:
- Reply in ONE short friendly sentence only
- NEVER say welcome back or hello again in middle of conversation
- NEVER make up products — only use products listed above
- NEVER start reply with bullet points or dashes
- Use customer name naturally if you know it
- If customer tells name: "Nice to meet you [name], how can I help?"
- If asked about product category: confirm yes and ask which one. Example: "Yes, we have smartphones — iPhone 15, Samsung S24, OnePlus 12 — which one catches your eye?"
- If asked specific product price: tell exact price from the list
- If customer wants to buy or place order: "Your order has been confirmed {name_str}! It will be delivered soon."
- If customer says yes to buying: confirm order immediately
- If asked personal questions: answer briefly as AI
- If asked how are you: "Doing great, how can I help?"
- If off-topic: "I can only help with shop queries!"

Customer said: "{user_input}"

Reply in one friendly sentence:"""

    response = client.chat.completions.create(
       model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80
    )
    return response.choices[0].message.content.strip(), intent

st.set_page_config(page_title="ShopBot", page_icon="🤖", layout="centered")

st.markdown("""
    <h1 style='text-align: center; color: #4A90E2;'>🤖 ShopBot</h1>
    <p style='text-align: center; color: gray;'>Your friendly customer support assistant</p>
    <hr>
""", unsafe_allow_html=True)

best_model, best_name = load_model()

st.sidebar.success(f"✅ Model: {best_name}")
user_name = st.session_state.get("user_name", None)
user_city = st.session_state.get("user_city", None)

if user_name or user_city:
    st.sidebar.markdown("### 👤 Customer Info")
    if user_name:
        st.sidebar.markdown(f"**Name:** {user_name}")
    if user_city:
        st.sidebar.markdown(f"**City:** {user_city}")

st.sidebar.markdown("### 🛍️ Shop Info")
st.sidebar.markdown("""
- 🕐 Mon-Sat, 9AM - 6PM
- 📍 MG Road, Bhopal
- 🔄 Returns within 7 days
""")

st.sidebar.markdown("### 📦 Our Products")
st.sidebar.text(products_catalog)

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hey! 👋 I'm ShopBot. How can I help you today?"
    })

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "intent" in msg:
            st.caption(f"`{msg['intent']}`")

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("typing..."):
        reply, intent = get_response(user_input, best_model)

    with st.chat_message("assistant"):
        st.write(reply)
        st.caption(f"`{intent}`")

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "intent": intent
    })

    # mistral or llama

    #streamlit run app.py