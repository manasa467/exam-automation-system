import sqlite3
import json
import hashlib
import secrets

ADMIN_USERNAME = "Manasa"
ADMIN_PASSWORD = "Manasa@1208"

DB_NAME = "academy.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER,
                    subject_name TEXT NOT NULL,
                    course_code TEXT NOT NULL UNIQUE,
                    semester TEXT NOT NULL,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS syllabus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    module_number INTEGER,
                    content TEXT,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS course_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    co_number TEXT,
                    description TEXT,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reference_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    reference_text TEXT,
                    reference_pdf_path TEXT,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
                )''')

    # Migration guard for existing DBs
    try:
        c.execute("ALTER TABLE reference_materials ADD COLUMN reference_pdf_path TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Migration guard for unique constraint on course_code (for existing databases)
    try:
        c.execute("CREATE UNIQUE INDEX idx_subjects_course_code ON subjects(course_code)")
    except sqlite3.OperationalError:
        pass

    # Sessions table for secure token-based auth
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    teacher_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS question_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    pattern_type TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id)
                )''')

    # Migration guards: add password columns if they don't exist yet
    for col in ['password_hash', 'password_salt']:
        try:
            c.execute(f"ALTER TABLE teachers ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

    # Ensure admin account always exists with the correct password
    _ensure_admin()

# --- Password Helpers ---

def _hash_password(password: str, salt: str = None):
    """Returns (hash_hex, salt_hex) using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 260000)
    return key.hex(), salt

def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 260000)
    return key.hex() == stored_hash

def _ensure_admin():
    """Create or update the Manasa admin account with the hardcoded password."""
    conn = get_connection()
    c = conn.cursor()
    pw_hash, pw_salt = _hash_password(ADMIN_PASSWORD)
    c.execute("SELECT id FROM teachers WHERE LOWER(name) = LOWER(?)", (ADMIN_USERNAME,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE teachers SET password_hash = ?, password_salt = ? WHERE id = ?",
                  (pw_hash, pw_salt, row[0]))
    else:
        c.execute("INSERT INTO teachers (name, password_hash, password_salt) VALUES (?, ?, ?)",
                  (ADMIN_USERNAME, pw_hash, pw_salt))
    conn.commit()
    conn.close()

# --- Teachers ---

def get_or_create_teacher(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM teachers WHERE name = ?", (name,))
    teacher = c.fetchone()
    if not teacher:
        c.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
        conn.commit()
        teacher = (c.lastrowid, name)
    conn.close()
    return teacher

def register_teacher(name: str, password: str):
    """Register a new teacher with a hashed password. Returns (id, name) or raises ValueError."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM teachers WHERE LOWER(name) = LOWER(?)", (name,))
    if c.fetchone():
        conn.close()
        raise ValueError(f"Username '{name}' is already taken.")
    pw_hash, pw_salt = _hash_password(password)
    c.execute("INSERT INTO teachers (name, password_hash, password_salt) VALUES (?, ?, ?)",
              (name, pw_hash, pw_salt))
    conn.commit()
    teacher_id = c.lastrowid
    conn.close()
    return (teacher_id, name)

def verify_login(name: str, password: str):
    """Verify credentials. Returns (id, name) tuple if valid, else None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, password_hash, password_salt FROM teachers WHERE LOWER(name) = LOWER(?)", (name,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    t_id, t_name, pw_hash, pw_salt = row
    if not pw_hash or not pw_salt:
        return None
    if _verify_password(password, pw_hash, pw_salt):
        return (t_id, t_name)
    return None

# --- Sessions ---

def create_session(teacher_id: int) -> str:
    """Create a secure opaque session token and store it in the DB."""
    token = secrets.token_urlsafe(32)
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, teacher_id) VALUES (?, ?)", (token, teacher_id))
    conn.commit()
    conn.close()
    return token

def get_session(token: str):
    """Look up a session token. Returns (teacher_id, name) or None."""
    if not token:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT t.id, t.name FROM sessions s
                 JOIN teachers t ON s.teacher_id = t.id
                 WHERE s.token = ?''', (token,))
    row = c.fetchone()
    conn.close()
    return row

def delete_session(token: str):
    """Remove a session token on logout."""
    if not token:
        return
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def get_all_users_for_admin():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM teachers WHERE name != 'Manasa' COLLATE NOCASE")
    users = c.fetchall()
    conn.close()
    return users

def delete_teacher(teacher_id):
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Get all subjects for this teacher
    c.execute("SELECT id FROM subjects WHERE teacher_id = ?", (teacher_id,))
    subject_ids = [row[0] for row in c.fetchall()]
    
    # 2. Delete all related data for each subject manually
    for sid in subject_ids:
        c.execute("DELETE FROM syllabus WHERE subject_id = ?", (sid,))
        c.execute("DELETE FROM course_outcomes WHERE subject_id = ?", (sid,))
        c.execute("DELETE FROM reference_materials WHERE subject_id = ?", (sid,))
        c.execute("DELETE FROM question_papers WHERE subject_id = ?", (sid,))
        
    # 3. Delete the subjects
    c.execute("DELETE FROM subjects WHERE teacher_id = ?", (teacher_id,))
    
    # 4. Delete the teacher
    c.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    
    conn.commit()
    conn.close()

# --- Subjects ---

def add_subject(teacher_id, name, code, semester):
    conn = get_connection()
    c = conn.cursor()
    
    # Check if course code already exists
    c.execute("SELECT id FROM subjects WHERE course_code = ?", (code,))
    existing = c.fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Course code '{code}' already exists. Please use a unique course code.")
    
    c.execute("INSERT INTO subjects (teacher_id, subject_name, course_code, semester) VALUES (?, ?, ?, ?)",
              (teacher_id, name, code, semester))
    conn.commit()
    subject_id = c.lastrowid
    conn.close()
    return subject_id

def get_subjects(teacher_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM subjects WHERE teacher_id = ?", (teacher_id,))
    subjects = c.fetchall()
    conn.close()
    return subjects

def get_all_subjects_for_admin():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT s.*, t.name as teacher_name 
                 FROM subjects s 
                 LEFT JOIN teachers t ON s.teacher_id = t.id''')
    subjects = c.fetchall()
    conn.close()
    return subjects

def delete_subject(subject_id):
    conn = get_connection()
    c = conn.cursor()
    # Explicitly cascade deletes manually in case PRAGMA foreign_keys is OFF
    c.execute("DELETE FROM syllabus WHERE subject_id = ?", (subject_id,))
    c.execute("DELETE FROM course_outcomes WHERE subject_id = ?", (subject_id,))
    c.execute("DELETE FROM reference_materials WHERE subject_id = ?", (subject_id,))
    c.execute("DELETE FROM question_papers WHERE subject_id = ?", (subject_id,))
    
    c.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()

# --- Syllabus ---

def add_syllabus(subject_id, module_number, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM syllabus WHERE subject_id = ?", (subject_id,))
    if c.fetchone()[0] >= 5:
        conn.close()
        raise ValueError("Only 5 modules are allowed per subject.")
    c.execute("INSERT INTO syllabus (subject_id, module_number, content) VALUES (?, ?, ?)",
              (subject_id, module_number, content))
    conn.commit()
    conn.close()

def get_syllabus(subject_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM syllabus WHERE subject_id = ? ORDER BY module_number", (subject_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def check_syllabus_exists(subject_id, module_number):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM syllabus WHERE subject_id = ? AND module_number = ?", (subject_id, module_number))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def update_syllabus(id, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE syllabus SET content = ? WHERE id = ?", (content, id))
    conn.commit()
    conn.close()

def delete_syllabus(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM syllabus WHERE id = ?", (id,))
    conn.commit()
    conn.close()

# --- Course Outcomes ---

def add_co(subject_id, co_number, description):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM course_outcomes WHERE subject_id = ?", (subject_id,))
    if c.fetchone()[0] >= 5:
        conn.close()
        raise ValueError("Only 5 Course Outcomes are allowed per subject.")
    c.execute("INSERT INTO course_outcomes (subject_id, co_number, description) VALUES (?, ?, ?)",
              (subject_id, co_number, description))
    conn.commit()
    conn.close()

def get_cos(subject_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM course_outcomes WHERE subject_id = ? ORDER BY co_number", (subject_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def check_co_exists(subject_id, co_number):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM course_outcomes WHERE subject_id = ? AND co_number = ?", (subject_id, co_number))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def update_co(id, description):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE course_outcomes SET description = ? WHERE id = ?", (description, id))
    conn.commit()
    conn.close()

def delete_co(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM course_outcomes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

# --- Reference Materials ---

def add_reference(subject_id, text, pdf_path=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM reference_materials WHERE subject_id = ?", (subject_id,))
    if c.fetchone()[0] >= 5:
        conn.close()
        raise ValueError("Only 5 references are allowed per subject.")
    c.execute("INSERT INTO reference_materials (subject_id, reference_text, reference_pdf_path) VALUES (?, ?, ?)",
              (subject_id, text, pdf_path))
    conn.commit()
    conn.close()

def get_references(subject_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reference_materials WHERE subject_id = ?", (subject_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_reference_by_id(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reference_materials WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()
    return row

def update_reference(id, text, pdf_path=None):
    conn = get_connection()
    c = conn.cursor()
    if pdf_path:
        c.execute("UPDATE reference_materials SET reference_text = ?, reference_pdf_path = ? WHERE id = ?",
                  (text, pdf_path, id))
    else:
        c.execute("UPDATE reference_materials SET reference_text = ? WHERE id = ?", (text, id))
    conn.commit()
    conn.close()

def delete_reference(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM reference_materials WHERE id = ?", (id,))
    conn.commit()
    conn.close()

# --- Question Papers ---

def save_question_paper(subject_id, pattern_type, content_json):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO question_papers (subject_id, pattern_type, content) VALUES (?, ?, ?)",
              (subject_id, pattern_type, json.dumps(content_json)))
    conn.commit()
    conn.close()