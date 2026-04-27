import time
import os
import json
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template
from database import (
    init_db, create_session, save_message, save_log,
    get_sessions, get_messages, get_stats,
    save_memory, get_memory
)
from rag_chain import (
    get_chain, get_casual_response, is_casual,
    extract_memory, get_llm, rerank_docs,
    is_pdf_relevant, get_personal_info_response,
    is_asking_about_memory, search_all_pdfs
)

init_db()
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/new-session", methods=["POST"])
def new_session():
    sid = create_session()
    return jsonify({"session_id": sid})

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        user_query = data.get("message", "").strip()

        if not user_query:
            return jsonify({"error": "Empty message"}), 400

        save_message(session_id, "user", user_query)

        # 🔥 STEP 1: Load OLD memory first
        memory = get_memory(session_id)

        # 🔥 STEP 2: Extract NEW memory
        new_memory = extract_memory(user_query)

        # 🔥 STEP 3: Save NEW memory
        for key, value in new_memory.items():
            save_memory(session_id, key, value)

        # 🔥 STEP 4: Reload UPDATED memory
        memory = get_memory(session_id)

        print("DEBUG MEMORY:", memory)

        start = time.time()
        pages = []
        sources = []

        # =========================================================
        # 🔥 FINAL DECISION FLOW (FIXED)
        # =========================================================

        # ✅ PRIORITY 1: MEMORY QUESTIONS
        if is_asking_about_memory(user_query):
            known = []

            if memory.get("name"):
                known.append(f"your name is {memory['name']}")
            if memory.get("city"):
                known.append(f"you are from {memory['city']}")
            if memory.get("age"):
                known.append(f"you are {memory['age']} years old")

            if known:
                answer = f"Yes, I remember! I know that {', and '.join(known)} 😊"
            else:
                answer = "I don't think you've told me anything yet! What should I call you? 😊"

        # ✅ PRIORITY 2: NEW MEMORY SAVE RESPONSE
        elif new_memory:
            answer = get_personal_info_response(user_query, memory)

        # ✅ PRIORITY 3: CASUAL CHAT
        elif is_casual(user_query):
            llm = get_llm()
            answer = get_casual_response(user_query, memory, llm)

        # ✅ PRIORITY 4: RAG SYSTEM
        else:
            all_docs = search_all_pdfs(user_query)
            chains = get_chain()

            pdf_relevant = is_pdf_relevant(user_query, all_docs)

            if pdf_relevant:
                reranked_docs = rerank_docs(user_query, all_docs, top_k=4)

                pages = [doc.metadata.get("page", 0) + 1 for doc in reranked_docs]
                sources = list(set([
                    doc.metadata.get("source_pdf", "Unknown PDF")
                    for doc in reranked_docs
                ]))

                answer = chains["pdf"].invoke(user_query)
                print(f"Answer from PDF — sources: {sources}")

            else:
                answer = chains["general"].invoke(user_query)
                print("Answer from general knowledge")

        # =========================================================

        elapsed = round(time.time() - start, 2)

        save_message(session_id, "assistant", answer)
        save_log(session_id, user_query, answer, pages, elapsed)

        return jsonify({
            "answer": answer,
            "sources": pages,
            "source_pdfs": sources,
            "time": elapsed,
            "memory": memory
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "answer": f"Error: {str(e)}",
            "sources": [],
            "source_pdfs": [],
            "time": 0
        })

@app.route("/api/sessions")
def sessions():
    rows = get_sessions()
    return jsonify({
        "sessions": [{"id": r[0], "name": r[1], "date": r[2]} for r in rows]
    })

@app.route("/api/history/<int:session_id>")
def history(session_id):
    msgs = get_messages(session_id)
    return jsonify({
        "messages": [{"role": r[0], "content": r[1]} for r in msgs]
    })

@app.route("/api/stats")
def stats():
    s, q, avg = get_stats()
    return jsonify({"sessions": s, "queries": q, "avg_time": avg})

@app.route("/api/pdfs")
def list_pdfs():
    collections_file = "./chroma_db/collections.json"
    if os.path.exists(collections_file):
        with open(collections_file, "r") as f:
            collections = json.load(f)
        return jsonify({"pdfs": [c["pdf"] for c in collections]})
    return jsonify({"pdfs": []})

@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")

@app.route("/api/analytics")
def analytics_data():
    from database import get_conn
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT s.id, s.name, COUNT(q.id) as total
        FROM sessions s
        LEFT JOIN query_logs q ON s.id = q.session_id
        GROUP BY s.id
    """)
    session_queries = c.fetchall()

    c.execute("SELECT created_at, response_time FROM query_logs ORDER BY id")
    response_times = c.fetchall()

    c.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
    role_counts = c.fetchall()

    c.execute("""
        SELECT strftime('%H', created_at) as hour, COUNT(*) as count
        FROM query_logs GROUP BY hour ORDER BY hour
    """)
    hourly = c.fetchall()

    conn.close()

    return jsonify({
        "session_queries": [{"session": f"Session {r[0]}", "queries": r[2]} for r in session_queries],
        "response_times": [{"time": r[0], "seconds": r[1]} for r in response_times],
        "role_counts": [{"role": r[0], "count": r[1]} for r in role_counts],
        "hourly": [{"hour": r[0] + ":00", "count": r[1]} for r in hourly]
    })

if __name__ == "__main__":
    app.run(debug=True)