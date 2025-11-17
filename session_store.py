import sqlite3
import os
import json

def ensure_data_dirs():
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("data", exist_ok=True)

class SessionStore:
    def __init__(self, db_path="data/sessions.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            pdf_id TEXT,
            history TEXT
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            pdf_id TEXT PRIMARY KEY,
            filename TEXT,
            path TEXT
        )""")
        conn.commit()
        conn.close()

    def create_session(self, pdf_id: str):
        import uuid
        session_id = str(uuid.uuid4())
        self._save_session(session_id, pdf_id, [])
        return session_id

    def _save_session(self, session_id, pdf_id, history):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO sessions (session_id, pdf_id, history) VALUES (?, ?, ?)",
                    (session_id, pdf_id, json.dumps(history)))
        conn.commit()
        conn.close()

    def get_history(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT history FROM sessions WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return json.loads(row[0])

    def append_history(self, session_id: str, entry: str):
        history = self.get_history(session_id) or []
        history.append(entry)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET history = ? WHERE session_id = ?", (json.dumps(history), session_id))
        conn.commit()
        conn.close()

    def add_pdf(self, pdf_id: str, filename: str, path: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO pdfs (pdf_id, filename, path) VALUES (?, ?, ?)", (pdf_id, filename, path))
        conn.commit()
        conn.close()

    def get_pdf(self, pdf_id: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT filename, path FROM pdfs WHERE pdf_id = ?", (pdf_id,))
        row = cur.fetchone()
        conn.close()
        return {"filename": row[0], "path": row[1]} if row else None
