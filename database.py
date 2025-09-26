import sqlite3
import json

DATABASE = "database.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT NULL,
            phone TEXT DEFAULT NULL,
            email TEXT DEFAULT NULL,
            education TEXT DEFAULT NULL,
            filename TEXT,
            filedata BLOB,
            skills TEXT DEFAULT NULL,
            exp_data TEXT DEFAULT NULL, -- store JSON string
            total_exp FLOAT DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_resume_to_db(name, phone, email, education, filename, filedata, skills, exp_data, total_exp):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    exp_json = json.dumps(exp_data) if exp_data else None

    cursor.execute("""
        INSERT INTO resumes (name, phone, email, education, filename, filedata, skills, exp_data, total_exp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, email, education, filename, filedata, skills, exp_json, total_exp))

    conn.commit()
    conn.close()


def fetch_all_resumes():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, email, education, filename, skills, exp_data FROM resumes")
    rows = cursor.fetchall()
    conn.close()
    result = [dict(row) for row in rows]
    return result

def get_resume_file(resume_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, filedata FROM resumes WHERE id=?", (resume_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_resume(resume_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resumes WHERE id=?", (resume_id,))
    conn.commit()
    conn.close()


def delete_all_records():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resumes")  # Deletes all rows
    conn.commit()
    conn.close()
    print("All records deleted successfully.")


def add_skill_score_column():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE resumes ADD COLUMN Total_Exp FLOAT DEFAULT 0")
        conn.commit()
        print("✅ Total_Exp column added.")
    except sqlite3.OperationalError:
        print("⚠️ skill_score column already exists.")
    finally:
        conn.close()



def show_table_schema():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(resumes)")
    schema = cursor.fetchall()
    conn.close()

    print("Table Schema for 'resumes':")
    for col in schema:
        print(col)

def drop_table(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
        print(f"✅ Table '{table_name}' dropped successfully.")
    except Exception as e:
        print("❌ Error:", e)
    finally:
        conn.close()

fetch_all_resumes()