import streamlit as st
import PyPDF2
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer
import faiss

client = Groq(api_key="YOUR_API_KEY_HERE")

@st.cache_resource
def load_rag_system():
    text = ""
    with open("products.pdf", "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()

    chunks = []
    chunk_size = 100
    overlap = 20
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embedder.encode(chunks)
    embeddings = np.array(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return chunks, embedder, index


def extract_user_info(user_input):
    text = user_input.lower().strip()
    if "my name is" in text:
        name = text.split("my name is")[1].strip().split()[0].capitalize()
        st.session_state["user_name"] = name
    elif "call me" in text:
        name = text.split("call me")[1].strip().split()[0].capitalize()
        st.session_state["user_name"] = name
    if "i am from" in text:
        city = text.split("i am from")[1].strip().split()[0].capitalize()
        st.session_state["user_city"] = city
    elif "i live in" in text:
        city = text.split("i live in")[1].strip().split()[0].capitalize()
        st.session_state["user_city"] = city


def get_rag_response(user_input, chunks, embedder, index):
    extract_user_info(user_input)

    lower_input = user_input.lower().strip()
    user_name = st.session_state.get("user_name", None)
    user_city = st.session_state.get("user_city", None)

    # Greetings
    if lower_input in ["hi", "hello", "hey"]:
        return "Hey! How can I help you today?"

    if "good morning" in lower_input:
        return "Good morning! How can I help?"

    if "good evening" in lower_input:
        return "Good evening! How can I help?"

    if "how are you" in lower_input:
        return "Doing great! How can I help you?"

    # Thank you handling
    if any(x in lower_input for x in ["thank you", "thanks", "thankyou", "thank u", "thnx", "thx"]):
        return "You're welcome! Is there anything else I can help you with?"

    # No thanks / goodbye
    if any(x in lower_input for x in [
        "no thanks", "no thank you", "nope", "not now",
        "no need", "fine thank you", "that's all", "thats all",
        "nothing else", "no more", "i'm good", "im good"
    ]):
        return "Alright, it was a pleasure helping you! Do visit us again at MG Road, Bhopal. Have a great day!"

    # Bye
    if any(x in lower_input for x in ["bye", "goodbye", "see you", "take care", "ciao"]):
        return "Goodbye! Hope to see you again soon at ShopBot. Have a wonderful day!"

    # Bot info
    if "who are you" in lower_input or "what are you" in lower_input:
        return "I am ShopBot, your electronics assistant at MG Road, Bhopal."

    if "are you human" in lower_input or "are you a bot" in lower_input or "are you ai" in lower_input:
        return "I am an AI assistant, but I am here to help you with all your shopping needs!"

    # Name queries
    if any(x in lower_input for x in [
        "what is my name", "do you know my name",
        "you know my name", "remember my name",
        "do you remember", "whats my name", "tell me my name"
    ]):
        if user_name:
            return f"Yes! Your name is {user_name}. I remember everything you tell me!"
        else:
            return "I don't know your name yet. Please tell me — my name is...?"

    # City queries
    if any(x in lower_input for x in [
        "what is my city", "where am i from",
        "do you know my city", "remember my city"
    ]):
        if user_city:
            return f"You are from {user_city}!"
        else:
            return "I don't know your city yet. You can tell me!"

    # Name introduction
    if "my name is" in lower_input and len(lower_input.split()) <= 6:
        if user_name:
            return f"Nice to meet you {user_name}! How can I help you today?"

    # Search PDF
    query_embedding = embedder.encode([user_input])
    query_embedding = np.array(query_embedding).astype("float32")
    distances, indices = index.search(query_embedding, 5)
    relevant_chunks = [chunks[i] for i in indices[0]]
    context = "\n".join(relevant_chunks)

    # Conversation history
    history_text = ""
    for msg in st.session_state.messages[-8:]:
        role = "Customer" if msg["role"] == "user" else "ShopBot"
        history_text += f"{role}: {msg['content']}\n"

    # Memory
    memory_info = ""
    if user_name:
        memory_info += f"Customer name: {user_name}\n"
    if user_city:
        memory_info += f"Customer city: {user_city}\n"
    if not memory_info:
        memory_info = "No customer info stored yet."

    prompt = f"""You are ShopBot, a friendly electronics shop assistant in Bhopal.

Conversation History:
{history_text}

Customer Memory (PRIVATE — never reveal):
{memory_info}

Product Catalog:
{context}

STRICT RULES:
- NEVER say Hello or Hi in middle of conversation
- NEVER use customer name in normal replies
- Use name ONLY if customer directly asks about their name
- If customer says ok, okay, sure, yes, hmm — continue same topic naturally
- Keep answers short — max 2 sentences
- Only use products from catalog — NEVER make up products or discounts
- If asked about discount — say prices are already competitive, no current offers
- If asked personal questions — say I am an AI assistant
- If off-topic — say I can only help with shop queries
- If customer says thank you — say You are welcome! Is there anything else I can help you with?
- If customer says no thanks or that's all — say it was a pleasure, do visit again

Customer: {user_input}
ShopBot:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )

    reply = response.choices[0].message.content.strip()

    # Remove accidental Hello from middle of conversation
    if len(st.session_state.messages) > 2:
        for word in ["Hello! ", "Hello, ", "Hi! ", "Hi, ", "Hey! ", "Hey, "]:
            if reply.startswith(word):
                reply = reply[len(word):]

    return reply.strip()


# UI
st.set_page_config(page_title="ShopBot RAG", page_icon="🤖")
st.title("🤖 ShopBot — RAG Chatbot")

with st.spinner("Loading..."):
    chunks, embedder, index = load_rag_system()

# Sidebar
st.sidebar.markdown("### Shop Info")
st.sidebar.markdown("""
- MG Road, Bhopal
- Mon-Sat 9AM-6PM
- 7 Day Return Policy
""")

user_name = st.session_state.get("user_name", None)
user_city = st.session_state.get("user_city", None)
if user_name or user_city:
    st.sidebar.markdown("### Customer Info")
    if user_name:
        st.sidebar.markdown(f"Name: {user_name}")
    if user_city:
        st.sidebar.markdown(f"City: {user_city}")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hey! I am ShopBot. How can I help you today?"
    })

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    reply = get_rag_response(user_input, chunks, embedder, index)

    with st.chat_message("assistant"):
        st.write(reply)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    st.rerun()
