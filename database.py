import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hospital.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Patients table
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            age         INTEGER,
            gender      TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Appointments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      INTEGER NOT NULL,
            patient_name    TEXT,
            patient_age     INTEGER,
            patient_gender  TEXT,
            doctor_id       INTEGER NOT NULL,
            doctor_name     TEXT,
            doctor_specialty TEXT,
            doctor_room     TEXT,
            symptoms        TEXT,
            appointment_time TEXT,
            priority        TEXT DEFAULT 'Normal',
            status          TEXT DEFAULT 'Confirmed',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Chat history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id   INTEGER NOT NULL,
            role         TEXT NOT NULL,
            message      TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized — hospital.db ready")


def save_patient(name, age, gender):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO patients (name, age, gender) VALUES (?, ?, ?)",
        (name, age, gender)
    )
    patient_id = c.lastrowid
    conn.commit()
    conn.close()
    return patient_id


def save_appointment(patient_id, patient_name, patient_age, patient_gender,
                     doctor, symptoms, appointment_time, priority):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO appointments
        (patient_id, patient_name, patient_age, patient_gender,
         doctor_id, doctor_name, doctor_specialty, doctor_room,
         symptoms, appointment_time, priority, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed')
    """, (
        patient_id, patient_name, patient_age, patient_gender,
        doctor["id"], doctor["name"], doctor["specialty"], doctor["room"],
        symptoms, appointment_time, priority
    ))
    appt_id = c.lastrowid
    conn.commit()
    conn.close()
    return appt_id


def save_chat(patient_id, role, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (patient_id, role, message) VALUES (?, ?, ?)",
        (patient_id, role, message)
    )
    conn.commit()
    conn.close()


def get_all_appointments():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM appointments ORDER BY created_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_patient_appointments(patient_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM appointments WHERE patient_name LIKE ? ORDER BY created_at DESC",
        (f"%{patient_name}%",)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()