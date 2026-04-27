from flask import Flask, render_template, request, jsonify, session, redirect
from groq import Groq
import json
import sqlite3
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = "hospital_secret_key_2024"

import os
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# ── Database ───────────────────────────────────────
def init_db():
    conn = sqlite3.connect("hospital.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT,
            name          TEXT,
            age           TEXT,
            gender        TEXT,
            symptoms      TEXT,
            doctor_id     INTEGER,
            doctor_name   TEXT,
            doctor_room   TEXT,
            priority      TEXT,
            appointment   TEXT,
            precautions   TEXT,
            visited_at    TEXT
        )
    """)
    # Add username and precautions columns if they don't exist (for existing DBs)
    try:
        c.execute("ALTER TABLE patients ADD COLUMN username TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists
    try:
        c.execute("ALTER TABLE patients ADD COLUMN precautions TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT,
            username   TEXT UNIQUE,
            password   TEXT,
            role       TEXT DEFAULT 'staff',
            created_at TEXT
        )
    """)
    admin_pass = hashlib.md5("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (name,username,password,role,created_at) VALUES (?,?,?,?,?)",
              ("Admin","admin",admin_pass,"admin",datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

init_db()

DOCTORS = [
    {
        "id": 1,"name": "Dr. Rajesh Sharma","specialty": "Cardiologist",
        "room": "Room 101","available": True,"initials": "RS","color": "#ef4444","count": 8,
        "slots": ["Monday 10:00 AM","Monday 2:00 PM","Wednesday 11:00 AM","Friday 3:00 PM"],
        "treats": ["chest pain","heart","BP","blood pressure","palpitation","breathing difficulty"]
    },
    {
        "id": 2,"name": "Dr. Priya Verma","specialty": "Neurologist",
        "room": "Room 205","available": True,"initials": "PV","color": "#8b5cf6","count": 5,
        "slots": ["Tuesday 9:00 AM","Tuesday 3:00 PM","Thursday 10:00 AM","Saturday 11:00 AM"],
        "treats": ["headache","migraine","dizziness","seizure","memory loss","numbness"]
    },
    {
        "id": 3,"name": "Dr. Anil Gupta","specialty": "Gastroenterologist",
        "room": "Room 312","available": True,"initials": "AG","color": "#f59e0b","count": 6,
        "slots": ["Monday 9:00 AM","Wednesday 2:00 PM","Thursday 4:00 PM","Friday 10:00 AM"],
        "treats": ["stomach pain","vomiting","acidity","diarrhea","liver","digestion"]
    },
    {
        "id": 4,"name": "Dr. Sunita Patel","specialty": "Pulmonologist",
        "room": "Room 418","available": True,"initials": "SP","color": "#06b6d4","count": 10,
        "slots": ["Monday 11:00 AM","Tuesday 2:00 PM","Thursday 9:00 AM","Saturday 10:00 AM"],
        "treats": ["cough","fever","breathing","asthma","cold","TB","lung"]
    },
    {
        "id": 5,"name": "Dr. Mohan Singh","specialty": "Orthopedic Surgeon",
        "room": "Room 520","available": False,"initials": "MS","color": "#10b981","count": 4,
        "slots": [],
        "treats": ["bone","joint","back pain","knee","fracture","sprain","muscle"]
    },
    {
        "id": 6,"name": "Dr. Kavita Joshi","specialty": "General Physician",
        "room": "Room 102","available": True,"initials": "KJ","color": "#3b82f6","count": 12,
        "slots": ["Monday 8:00 AM","Tuesday 10:00 AM","Wednesday 3:00 PM","Friday 9:00 AM","Saturday 2:00 PM"],
        "treats": ["general","fever","weakness","diabetes","thyroid","routine","checkup"]
    }
]

def is_logged_in():
    return session.get('logged_in', False)

@app.route("/login")
def login_page():
    if is_logged_in(): return redirect('/')
    return render_template("login.html")

@app.route("/")
def index():
    if not is_logged_in(): return redirect('/login')
    if session.get('role','staff') == 'admin':
        return redirect('/dashboard')
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if not is_logged_in(): return redirect('/login')
    role = session.get('role', 'staff')
    if role == 'admin':
        return render_template("dashboard.html")
    else:
        return render_template("user_dashboard.html")

@app.route("/patients")
def patients_page():
    if not is_logged_in(): return redirect('/login')
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM patients ORDER BY id DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return render_template("patients.html", patients=rows)

@app.route("/api/login", methods=["POST"])
def api_login():
    data     = request.get_json()
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    hashed   = hashlib.md5(password.encode()).hexdigest()
    conn = sqlite3.connect("hospital.db")
    c    = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed))
    user = c.fetchone()
    conn.close()
    if user:
        session['logged_in'] = True
        session['username']  = username
        session['name']      = user[1]
        session['role']      = user[4] if len(user) > 4 else 'staff'
        return jsonify({"success": True, "name": user[1], "role": session['role']})
    return jsonify({"success": False, "message": "Invalid username or password"})

@app.route("/api/signup", methods=["POST"])
def api_signup():
    data     = request.get_json()
    name     = data.get("name","").strip()
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    if not name or not username or not password:
        return jsonify({"success": False, "message": "All fields required"})
    hashed = hashlib.md5(password.encode()).hexdigest()
    try:
        conn = sqlite3.connect("hospital.db")
        c    = conn.cursor()
        c.execute("INSERT INTO users (name,username,password,role,created_at) VALUES (?,?,?,?,?)",
                  (name, username, hashed, 'staff', datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/session", methods=["GET"])
def get_session():
    if is_logged_in():
        return jsonify({
            "logged_in": True,
            "name": session.get('name',''),
            "username": session.get('username',''),
            "role": session.get('role','staff')
        })
    return jsonify({"logged_in": False})

@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    return jsonify({"success": True, "doctors": DOCTORS})

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data            = request.get_json()
        patient_message = data.get("message","")
        patient_name    = data.get("name","")
        patient_age     = data.get("age","")
        patient_gender  = data.get("gender","")
        history         = data.get("history",[])
        doctor_context  = data.get("doctorContext","")
        chat_stage      = data.get("stage","symptoms")
        symptom_turns   = data.get("symptomTurns", 0)

        # FIX: Force English responses always
        system_content = f"""You are Aria, a warm, caring and smart AI medical receptionist at City Hospital.

IMPORTANT: You MUST always respond in ENGLISH ONLY. Never reply in Hindi, Hinglish, or any other language. Always use English regardless of what language the patient uses.

Patient: {patient_name}, Age: {patient_age}, Gender: {patient_gender}
Stage: {chat_stage}
Symptom conversation turns so far: {symptom_turns}
{doctor_context}

YOUR BEHAVIOR BY STAGE:

STAGE 'symptoms' (turns 1):
- Listen carefully to what patient said
- Show empathy first ("I'm sorry to hear that...")
- Ask ONE good follow-up question to understand better
- Example: "How long have you been experiencing this?" or "Is the pain constant or does it come and go?"
- Do NOT suggest any doctor yet

STAGE 'symptoms' (turns 2+):
- You have enough info now
- Say "I have all the information I need. Let me find the best doctor for you right now!"
- Do NOT suggest doctor name yourself

STAGE 'slots':
- Slot buttons are shown on screen
- If patient asks about slots or time — tell them to click one of the slot buttons shown below
- If patient asks about precautions, symptoms, medicines — answer from your medical knowledge helpfully
- Give real precautions based on their symptoms (e.g. for headache: rest in dark room, drink water, avoid screen time)
- Be conversational and helpful

STAGE 'post':
- Answer any questions naturally
- Give medical precautions/advice based on symptoms from your knowledge
- Be warm and caring

STRICT RULES:
1. NEVER suggest any doctor name yourself — system assigns doctor
2. NEVER confirm appointment — slot buttons do that
3. Always respond directly to what patient just said
4. Keep replies 2-4 lines
5. If emergency symptoms — say EMERGENCY clearly
6. ALWAYS respond in ENGLISH ONLY — this is mandatory"""

        clean_history = [m for m in history if m.get("role") in ("user","assistant")]
        messages = [{"role":"system","content":system_content}]
        messages += clean_history
        messages += [{"role":"user","content":patient_message}]

        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=400, temperature=0.75
        )
        return jsonify({"success":True,"reply":response.choices[0].message.content})

    except Exception as e:
        print(f"[CHAT ERROR] {e}")
        return jsonify({"success":False,"reply":f"Server error: {str(e)}"}), 500

@app.route("/api/assign", methods=["POST"])
def assign_doctor():
    try:
        data           = request.get_json()
        symptoms       = data.get("symptoms","")
        patient_name   = data.get("name","Patient")
        patient_age    = data.get("age","")
        patient_gender = data.get("gender","")
        is_emergency   = data.get("emergency",False)

        doctors_json = json.dumps([
            {"id":d["id"],"name":d["name"],"specialty":d["specialty"],
             "available":d["available"],"treats":d["treats"]}
            for d in DOCTORS
        ], ensure_ascii=False)

        prompt = f"""Patient: {patient_name}, Age: {patient_age}, Gender: {patient_gender}
Symptoms: {symptoms}, Emergency: {is_emergency}
Doctors: {doctors_json}
Pick BEST available doctor. Return ONLY valid JSON no markdown:
{{"doctor_id":<number>,"reason":"<1-2 lines>","priority":"<High or Medium or Normal>","instructions":"<what to bring and precautions>"}}"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role":"system","content":"Medical triage expert. Return only valid JSON. No markdown."},
                {"role":"user","content":prompt}
            ],
            max_tokens=300, temperature=0.2
        )

        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        raw = raw.strip()

        result   = json.loads(raw)
        assigned = next((d for d in DOCTORS if d["id"] == result["doctor_id"]), None)

        if assigned and not assigned["available"]:
            assigned = next((d for d in DOCTORS if d["available"] and d["id"]==6), assigned)
            result["reason"] += " (Referred to General Physician)"

        if assigned:
            conn = sqlite3.connect("hospital.db")
            c    = conn.cursor()
            session_username = session.get('username', '')

            # Reuse existing pending patient record for this logged-in user,
            # preventing duplicate entries for the same appointment flow.
            if session_username:
                c.execute("SELECT id, appointment FROM patients WHERE LOWER(username)=LOWER(?) ORDER BY id DESC LIMIT 1", (session_username,))
            else:
                c.execute("SELECT id, appointment FROM patients WHERE LOWER(name)=LOWER(?) ORDER BY id DESC LIMIT 1", (patient_name,))
            existing = c.fetchone()

            if existing and existing[1] in (None, "", "null", "undefined"):
                c.execute("""
                    UPDATE patients SET username=?, age=?, gender=?, symptoms=?, doctor_id=?, doctor_name=?, doctor_room=?, priority=?, precautions=?, visited_at=?
                    WHERE id=?
                """, (
                    session_username,
                    patient_age, patient_gender, symptoms,
                    assigned["id"], assigned["name"], assigned["room"],
                    result.get("priority","Normal"),
                    result.get("instructions",""),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    existing[0]
                ))
                saved_row = existing[0]
            else:
                c.execute("""
                    INSERT INTO patients
                    (username,name,age,gender,symptoms,doctor_id,doctor_name,doctor_room,priority,precautions,visited_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                      session_username, patient_name, patient_age, patient_gender, symptoms,
                      assigned["id"], assigned["name"], assigned["room"],
                      result.get("priority","Normal"),
                      result.get("instructions",""),
                      datetime.now().strftime("%Y-%m-%d %H:%M")))
                saved_row = c.lastrowid

            conn.commit()
            conn.close()
            print(f"[DB SAVED] {patient_name} ({patient_gender}) → {assigned['name']} (row {saved_row})")

        return jsonify({
            "success":True,"doctor":assigned,
            "reason":result.get("reason",""),
            "priority":result.get("priority","Normal"),
            "instructions":result.get("instructions","Please proceed to the doctor's room.")
        })

    except Exception as e:
        print(f"[ASSIGN ERROR] {e}")
        return jsonify({"success":False,"error":str(e)}), 500

@app.route("/api/book", methods=["POST"])
def book_appointment():
    try:
        data             = request.get_json()
        patient_name     = data.get("name","")
        appointment_time = data.get("appointment_time","")
        precautions      = data.get("precautions","")

        conn = sqlite3.connect("hospital.db")
        c    = conn.cursor()
        session_username = session.get('username', '')
        if session_username:
            c.execute("""
                UPDATE patients SET appointment=?, precautions=COALESCE(precautions||' '||?, precautions, ?)
                WHERE id=(SELECT id FROM patients WHERE LOWER(username)=LOWER(?) ORDER BY id DESC LIMIT 1)
            """, (appointment_time, precautions, precautions, session_username))
        else:
            c.execute("""
                UPDATE patients SET appointment=?, precautions=COALESCE(precautions||' '||?, precautions, ?)
                WHERE id=(SELECT id FROM patients WHERE name=? ORDER BY id DESC LIMIT 1)
            """, (appointment_time, precautions, precautions, patient_name))
        conn.commit()
        conn.close()
        print(f"[APPOINTMENT] {patient_name} → {appointment_time}")
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@app.route("/api/patients", methods=["GET"])
def get_patients():
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM patients ORDER BY id DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"success":True,"patients":rows})

@app.route("/api/my-appointments", methods=["GET"])
def my_appointments():
    session_username = session.get('username', '')
    name = request.args.get("name","")
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if session_username:
        c.execute("SELECT * FROM patients WHERE LOWER(username)=LOWER(?) OR LOWER(name)=LOWER(?) ORDER BY id DESC", (session_username, session_username))
    else:
        c.execute("SELECT * FROM patients WHERE LOWER(name)=LOWER(?) ORDER BY id DESC", (name,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    # Remove exact duplicate entries so the user dashboard does not show repeated records
    seen = set()
    deduped = []
    for row in rows:
        key = (
            row.get('name','').strip().lower(),
            row.get('doctor_id'),
            row.get('doctor_name','').strip().lower(),
            row.get('appointment','').strip().lower(),
            row.get('visited_at','').strip().lower(),
            row.get('symptoms','').strip().lower()
        )
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    return jsonify({"success":True,"appointments":deduped})

if __name__ == "__main__":
    print("="*45)
    print("  City Hospital AI running...")
    print("  Login     : http://localhost:5000/login")
    print("  Counter   : http://localhost:5000")
    print("  Dashboard : http://localhost:5000/dashboard")
    print("="*45)
    app.run(debug=True, port=5000)