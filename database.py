import sqlite3
from datetime import datetime

DB_PATH = "medico.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT 'New Chat',
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            user_query TEXT,
            bot_answer TEXT,
            source_pages TEXT,
            response_time REAL,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # Memory table — user ki personal info yaad rakhne ke liye
    # jaise naam, city, problem — yeh session ke saath save hoga
    c.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            key TEXT,        -- jaise 'name', 'city', 'problem'
            value TEXT,      -- jaise 'Yasha', 'Bhopal', 'knee pain'
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready!")

def create_session():
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO sessions (name, created_at) VALUES (?, ?)", ("New Chat", now))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def save_message(session_id, role, content):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now)
    )
    conn.commit()
    conn.close()

def save_log(session_id, query, answer, pages, elapsed):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO query_logs
           (session_id, user_query, bot_answer, source_pages, response_time, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, query, answer, ", ".join(map(str, pages)), elapsed, now)
    )
    conn.commit()
    conn.close()

def save_memory(session_id, key, value):
    # memory save karo ya update karo
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # pehle check karo agar pehle se hai toh update karo
    c.execute(
        "SELECT id FROM memory WHERE session_id=? AND key=?",
        (session_id, key)
    )
    existing = c.fetchone()
    if existing:
        c.execute(
            "UPDATE memory SET value=? WHERE session_id=? AND key=?",
            (value, session_id, key)
        )
    else:
        c.execute(
            "INSERT INTO memory (session_id, key, value, created_at) VALUES (?, ?, ?, ?)",
            (session_id, key, value, now)
        )
    conn.commit()
    conn.close()

def get_memory(session_id):
    # is session ki saari memory lo — dictionary mein return karo
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT key, value FROM memory WHERE session_id=?",
        (session_id,)
    )
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_sessions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM sessions ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_messages(session_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY id",
        (session_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sessions")
    s = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM query_logs")
    q = c.fetchone()[0]
    c.execute("SELECT AVG(response_time) FROM query_logs")
    avg = c.fetchone()[0] or 0
    conn.close()
    return s, q, round(avg, 2)