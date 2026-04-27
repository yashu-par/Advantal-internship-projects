import os
import re
import json
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from sentence_transformers import CrossEncoder

CHROMA_DIR = "./chroma_db"
COLLECTIONS_FILE = "./chroma_db/collections.json"

_retrievers = {}
_chain = None
_llm = None

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ── COLLECTIONS LOAD ─────────────────────────────────
def get_all_collections():
    """
    collections.json se saari PDF collections lo.
    Har PDF ki alag collection hoti hai.
    """
    if not os.path.exists(COLLECTIONS_FILE):
        return []
    with open(COLLECTIONS_FILE, "r") as f:
        return json.load(f)

def get_retrievers():
    """
    Saari PDF collections ke retrievers banao.
    Ek baar bante hain, baar baar nahi.
    """
    global _retrievers
    if _retrievers:
        return _retrievers

    collections = get_all_collections()
    if not collections:
        print("No collections found!")
        return {}

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    for item in collections:
        collection_name = item["collection"]
        pdf_name = item["pdf"]
        try:
            vectorstore = Chroma(
                persist_directory=CHROMA_DIR,
                embedding_function=embeddings,
                collection_name=collection_name
            )
            # Har collection ka alag retriever
            _retrievers[pdf_name] = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 10}
            )
            print(f"Retriever loaded for: {pdf_name}")
        except Exception as e:
            print(f"Error loading {pdf_name}: {e}")

    return _retrievers

# ── MEMORY EXTRACTOR ─────────────────────────────────
def extract_memory(message):
    memory = {}
    msg = message.lower().strip()

    skip_patterns = [
        "what is your name", "what's your name",
        "who are you", "his name is", "her name is",
        "do you know", "what is my name", "what's my name",
        "tell me", "do you remember",
    ]
    for skip in skip_patterns:
        if skip in msg:
            return {}

    name_patterns = [
        r"my name is (\w+)",
        r"name is (\w+)",
        r"call me (\w+)",
        r"^i am (\w+)$",
        r"^i'm (\w+)$",
        r"mera naam (\w+) hai",
        r"mera naam (\w+)$",
        r"main (\w+) hoon",
    ]
    skip_words = [
        "a", "an", "the", "here", "there", "just", "not",
        "ok", "is", "are", "was", "been", "happy", "sad",
        "good", "fine", "great", "medico", "you", "your",
        "me", "my",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, msg)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in skip_words:
                memory["name"] = name
            break

    city_patterns = [
        r"i(?:'m| am) from (\w+)",
        r"i live in (\w+)",
        r"mera sheher (\w+) hai",
        r"mera sheher (\w+)$",
        r"main (\w+) se hoon",
    ]
    for pattern in city_patterns:
        match = re.search(pattern, msg)
        if match:
            city = match.group(1).capitalize()
            if city.lower() not in ["a", "an", "the"]:
                memory["city"] = city
            break

    age_patterns = [
        r"i am (\d+) years", r"i'm (\d+) years",
        r"meri age (\d+)", r"(\d+) saal ka", r"(\d+) saal ki",
    ]
    for pattern in age_patterns:
        match = re.search(pattern, msg)
        if match:
            memory["age"] = match.group(1)
            break

    return memory

# ── MEMORY QUESTION CHECK ────────────────────────────
def is_asking_about_memory(message):
    msg = message.lower().strip()
    memory_questions = [
        "what is my name", "what's my name",
        "do you remember my name", "do you know my name",
        "mera naam kya hai", "mera naam batao",
        "do you remember me", "what do you know about me",
        "who am i", "where am i from", "my city",
        "my age", "meri age", "do you remember",
        "kya yaad hai", "tumhe yaad hai", "yaad hai mera",
        "remember my name", "know my name",
    ]
    return any(kw in msg for kw in memory_questions)

# ── CASUAL CHECK ─────────────────────────────────────
def is_casual(message):
    msg = message.lower().strip()

    not_casual_patterns = [
        "my name is", "name is", "mera naam",
        "call me", "i am from", "i live in",
        "i'm from", "se hoon", "meri age",
    ]
    for pattern in not_casual_patterns:
        if pattern in msg:
            return False

    if is_asking_about_memory(message):
        return False

    casual_keywords = [
        "hello", "hi", "hey", "namaste",
        "how are you", "what's your name", "who are you",
        "your name", "good morning", "good evening",
        "good night", "thank", "thanks", "bye", "goodbye",
        "what can you do", "kaise ho", "aap kaun",
        "tumhara naam",
    ]
    for kw in casual_keywords:
        if kw in msg:
            return True

    if len(msg.split()) <= 3 and "?" not in msg:
        return True

    return False

# ── CASUAL RESPONSE ──────────────────────────────────
def get_casual_response(message, memory, llm):
    msg = message.lower().strip()
    if "your name" in msg or "who are you" in msg or "aap kaun" in msg:
        return "I'm Medico, your medical PDF assistant! 😊 How can I help you today?"

    prompt = f"""You are Medico, a warm and friendly medical PDF assistant.
Rules:
- Keep responses short and warm (1-2 sentences only)
- Do NOT use or mention the user's name unless they ask
- Respond in same language as user (Hindi or English)

User said: {message}
Respond naturally:"""

    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else str(response)

# ── PERSONAL INFO RESPONSE ───────────────────────────
def get_personal_info_response(message, memory):
    msg = message.lower().strip()
    if any(p in msg for p in ["my name is", "name is", "call me", "mera naam", "main", "naam"]):
        name = memory.get("name", "")
        if name:
            return f"Got it! I'll remember that your name is {name}. 😊 Nice to meet you, {name}!"
        return "Nice! I'll remember that. 😊"
    if any(p in msg for p in ["i am from", "i live in", "i'm from", "se hoon", "sheher"]):
        city = memory.get("city", "")
        if city:
            return f"Great! I'll remember that you're from {city}. 😊"
        return "Got it! I'll remember that. 😊"
    if any(p in msg for p in ["age", "saal"]):
        age = memory.get("age", "")
        if age:
            return f"Noted! You are {age} years old. 😊"
    return "Got it! I'll remember that. 😊"

# ── RERANKER ─────────────────────────────────────────
def rerank_docs(query, docs, top_k=4):
    if not docs:
        return docs
    pairs = [[query, doc.page_content] for doc in docs]
    scores = reranker.predict(pairs)
    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    top_docs = [doc for score, doc in scored_docs[:top_k]]
    print(f"Reranker: {len(docs)} → top {len(top_docs)} selected")
    for i, (score, doc) in enumerate(scored_docs[:top_k]):
        src = doc.metadata.get("source_pdf", "?")
        doc_type = doc.metadata.get("type", "text")
        print(f"  Rank {i+1}: score={score:.3f} | {src} | type={doc_type} | {doc.page_content[:50]}...")
    return top_docs

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# ── PDF RELEVANCE CHECK ──────────────────────────────
def is_pdf_relevant(query, docs, threshold=2.0):
    if not docs:
        return False
    pairs = [[query, doc.page_content] for doc in docs[:3]]
    scores = reranker.predict(pairs)
    best_score = max(scores)
    print(f"PDF relevance best score: {best_score:.3f}")
    return best_score >= threshold

# ── LLM ──────────────────────────────────────────────
def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.3-70b-versatile",
            temperature=0.3
        )
    return _llm

# ── SEARCH ALL COLLECTIONS ───────────────────────────
def search_all_pdfs(query):
    """
    Saari PDF collections mein search karo.
    Saare results ek saath laao phir rerank karo.
    """
    retrievers = get_retrievers()
    if not retrievers:
        return []

    all_docs = []
    for pdf_name, retriever in retrievers.items():
        try:
            docs = retriever.invoke(query)
            all_docs.extend(docs)
            print(f"  {pdf_name}: {len(docs)} docs found")
        except Exception as e:
            print(f"  Error searching {pdf_name}: {e}")

    print(f"Total docs from all PDFs: {len(all_docs)}")
    return all_docs

# ── MAIN CHAIN ───────────────────────────────────────
def get_chain():
    global _chain
    if _chain is not None:
        return _chain

    llm = get_llm()

    # Prompt 1: PDF mein answer mila
    pdf_prompt = PromptTemplate(
        template="""You are Medico, a helpful medical assistant.
Answer the question using ONLY the context below from the PDF.
Be clear, detailed and helpful.
If the context has table data, use it to answer accurately.
Do NOT mention the user's name repeatedly.

Context from PDF:
{context}

Question: {question}

Answer:""",
        input_variables=["context", "question"]
    )

    # Prompt 2: PDF mein answer nahi mila — general knowledge
    general_prompt = PromptTemplate(
        template="""You are Medico, a knowledgeable and helpful assistant.
The uploaded PDF does not contain sufficient information about this topic.
Use your own knowledge to answer the question clearly and helpfully.

At the end of your answer, add this note on a new line:
"📚 Note: This answer is based on my general knowledge, not from the uploaded PDF."

Question: {question}

Answer:""",
        input_variables=["question"]
    )

    pdf_chain = (
        {
            "context": RunnableLambda(lambda q: format_docs(
                rerank_docs(q, search_all_pdfs(q), top_k=4)
            )),
            "question": RunnablePassthrough()
        }
        | pdf_prompt
        | llm
        | StrOutputParser()
    )

    general_chain = (
        {"question": RunnablePassthrough()}
        | general_prompt
        | llm
        | StrOutputParser()
    )

    _chain = {
        "pdf": pdf_chain,
        "general": general_chain
    }

    return _chain