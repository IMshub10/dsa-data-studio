import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dsa_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create problems table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        link TEXT,
        topic TEXT,
        pattern TEXT,
        time_to_optimal TEXT,
        bugs TEXT,
        aha_moment TEXT,
        checklist_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create solutions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS solutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        language TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (problem_id) REFERENCES problems (id) ON DELETE CASCADE
    )
    ''')

    # Create feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        solution_id INTEGER NOT NULL,
        feedback_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (solution_id) REFERENCES solutions (id) ON DELETE CASCADE
    )
    ''')

    # Create API usage logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        model_name TEXT NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        estimated_cost_usd REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (problem_id) REFERENCES problems (id) ON DELETE CASCADE
    )
    ''')

    # Add L4 tracking columns to existing problems table gracefully
    new_columns = [
        "time_complexity TEXT",
        "space_complexity TEXT",
        "l4_code_quality TEXT",
        "l4_edge_cases TEXT",
        "l4_scalability TEXT"
    ]
    for col in new_columns:
        try:
            cursor.execute(f"ALTER TABLE problems ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass # Column already exists

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def create_problem(name: str, link: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO problems (name, link) VALUES (?, ?)", (name, link))
        problem_id = cursor.lastrowid
    return problem_id

def get_problems_count() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM problems")
        return cursor.fetchone()[0]

def get_problems_page(page: int, page_size: int) -> list:
    offset = (page - 1) * page_size
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM problems ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_problem_by_name(name: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM problems WHERE name = ?", (name,))
        row = cursor.fetchone()
    return dict(row) if row else None

def add_solution(problem_id: int, file_path: str, language: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO solutions (problem_id, file_path, language) VALUES (?, ?, ?)",
            (problem_id, file_path, language)
        )
        solution_id = cursor.lastrowid
    return solution_id

def get_latest_solution(problem_id: int) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM solutions WHERE problem_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (problem_id,)
        )
        row = cursor.fetchone()
    return dict(row) if row else None

def add_feedback(solution_id: int, feedback_path: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (solution_id, feedback_path) VALUES (?, ?)",
            (solution_id, feedback_path)
        )

def update_problem_metadata(problem_id: int, metadata: dict):
    # Only update provided valid fields
    valid_fields = [
        "name", "link", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "checklist_status",
        "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability"
    ]
    updates = []
    values = []

    for key, val in metadata.items():
        if key in valid_fields:
            # Handle float/NaN or None
            if val is None or (isinstance(val, float) and val != val):  # val != val is a safe NaN check
                clean_val = ""
            else:
                clean_val = str(val).strip()
                
            updates.append(f"{key} = ?")
            values.append(clean_val)

    if not updates:
        return

    values.append(problem_id)
    query = f"UPDATE problems SET {', '.join(updates)} WHERE id = ?"

    with get_connection() as conn:
        conn.cursor().execute(query, tuple(values))

def delete_problem_from_db(problem_id: int):
    """Deletes a problem and its cascading dependencies explicitly for safety."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Delete child feedback (via solution IDs)
        cursor.execute("DELETE FROM feedback WHERE solution_id IN (SELECT id FROM solutions WHERE problem_id = ?)", (problem_id,))
        # Delete child solutions
        cursor.execute("DELETE FROM solutions WHERE problem_id = ?", (problem_id,))
        # Delete parent problem
        cursor.execute("DELETE FROM problems WHERE id = ?", (problem_id,))

def add_api_usage(problem_id: int, provider: str, model_name: str, input_tokens: int, output_tokens: int, estimated_cost_usd: float) -> int:
    """Logs an API call and its cost for a specific problem."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_usage_logs (problem_id, provider, model_name, input_tokens, output_tokens, estimated_cost_usd)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (problem_id, provider, model_name, input_tokens, output_tokens, estimated_cost_usd))
        return cursor.lastrowid


if __name__ == "__main__":
    init_db()
