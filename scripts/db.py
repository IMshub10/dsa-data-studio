import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "dsa_data.db")

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

    # Create patterns table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create problem_patterns table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problem_patterns (
        problem_id INTEGER NOT NULL,
        pattern_id INTEGER NOT NULL,
        PRIMARY KEY (problem_id, pattern_id),
        FOREIGN KEY (problem_id) REFERENCES problems (id) ON DELETE CASCADE,
        FOREIGN KEY (pattern_id) REFERENCES patterns (id) ON DELETE CASCADE
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

    # Add focus tracking columns to existing patterns table gracefully
    pattern_columns = [
        "is_focus INTEGER DEFAULT 0",
        "focus_started_at TIMESTAMP"
    ]
    for col in pattern_columns:
        try:
            cursor.execute(f"ALTER TABLE patterns ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass # Column already exists

    # Phase 1: Add Spaced Repetition (SRS) columns to problems table
    problem_columns = [
        "difficulty INTEGER",
        "review_stage INTEGER DEFAULT 0",
        "next_review_date TIMESTAMP"
    ]
    for col in problem_columns:
        try:
            cursor.execute(f"ALTER TABLE problems ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
            
    # Phase 2: Add timing column to solutions table
    try:
        cursor.execute("ALTER TABLE solutions ADD COLUMN time_spent_seconds INTEGER")
    except sqlite3.OperationalError:
        pass

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
        "name", "link", "difficulty", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "checklist_status",
        "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability"
    ]
    updates = []
    values = []

    integer_fields = ["difficulty"]
    
    for key, val in metadata.items():
        if key in valid_fields:
            # Handle float/NaN or None
            if val is None or (isinstance(val, float) and val != val):  # val != val is a safe NaN check
                clean_val = None if key in integer_fields else ""
            elif key in integer_fields:
                try:
                    clean_val = int(val)
                except (ValueError, TypeError):
                    clean_val = None
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
        # Delete child patterns links
        cursor.execute("DELETE FROM problem_patterns WHERE problem_id = ?", (problem_id,))
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

def insert_pattern(name: str, notes: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO patterns (name, notes) VALUES (?, ?)",
            (name, notes)
        )
        return cursor.lastrowid

def get_pattern_by_name(name: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patterns WHERE name = ?", (name,))
        row = cursor.fetchone()
    return dict(row) if row else None

def get_all_patterns() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patterns ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]

def link_problem_to_pattern(problem_id: int, pattern_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO problem_patterns (problem_id, pattern_id) VALUES (?, ?)",
            (problem_id, pattern_id)
        )

def get_problems_for_pattern(pattern_id: int) -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.* FROM problems p
            JOIN problem_patterns pp ON p.id = pp.problem_id
            WHERE pp.pattern_id = ?
            ORDER BY p.name ASC
        ''', (pattern_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_patterns_for_problem(problem_id: int) -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pt.* FROM patterns pt
            JOIN problem_patterns pp ON pt.id = pp.pattern_id
            WHERE pp.problem_id = ?
            ORDER BY pt.name ASC
        ''', (problem_id,))
        return [dict(row) for row in cursor.fetchall()]

# --- Dashboard & Analytics Helpers ---

def get_solved_problems_count() -> int:
    """Returns the count of unique problems that have at least one solution."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT problem_id) FROM solutions")
        return cursor.fetchone()[0]

def get_todo_problems(limit: int = 10) -> list:
    """Returns problems that have NO entries in the solutions table."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.* FROM problems p
            LEFT JOIN solutions s ON p.id = s.problem_id
            WHERE s.id IS NULL
            ORDER BY p.created_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_analytics_by_pattern() -> list:
    """Returns solve counts and total problem counts per pattern."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # This query gets pattern names, total problems linked, and how many of those are solved
        cursor.execute('''
            SELECT 
                pt.name as pattern_name,
                COUNT(DISTINCT pp.problem_id) as total_problems,
                COUNT(DISTINCT s.problem_id) as solved_problems
            FROM patterns pt
            LEFT JOIN problem_patterns pp ON pt.id = pp.pattern_id
            LEFT JOIN solutions s ON pp.problem_id = s.problem_id
            GROUP BY pt.id, pt.name
            ORDER BY pt.name ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_stale_patterns(days_threshold: int = 5) -> list:
    """
    Returns patterns where either no problems have been solved,
    or the most recent solution is older than `days_threshold` days.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT 
                pt.name as pattern_name,
                MAX(s.submitted_at) as last_solved_date
            FROM patterns pt
            LEFT JOIN problem_patterns pp ON pt.id = pp.pattern_id
            LEFT JOIN solutions s ON pp.problem_id = s.problem_id
            GROUP BY pt.id, pt.name
            HAVING last_solved_date IS NULL OR last_solved_date < datetime('now', '-{days_threshold} days')
            ORDER BY last_solved_date ASC NULLS FIRST
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_pattern_id_by_name(name: str) -> int:
    """Helper to get a pattern ID by name, useful for seeding scripts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patterns WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row[0] if row else None

def set_focus_pattern(pattern_id: int):
    """Sets a specific pattern as the current focus, unsetting all others."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Reset all
        cursor.execute("UPDATE patterns SET is_focus = 0, focus_started_at = NULL")
        # Set new focus
        cursor.execute(
            "UPDATE patterns SET is_focus = 1, focus_started_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pattern_id,)
        )

def get_focus_pattern() -> dict:
    """Returns the currently focused pattern with its start date and completion metrics."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # We join to get total problems and total solved
        cursor.execute('''
            SELECT 
                pt.id,
                pt.name as pattern_name,
                pt.focus_started_at,
                COUNT(DISTINCT pp.problem_id) as total_problems,
                COUNT(DISTINCT s.problem_id) as solved_problems
            FROM patterns pt
            LEFT JOIN problem_patterns pp ON pt.id = pp.pattern_id
            LEFT JOIN solutions s ON pp.problem_id = s.problem_id
            WHERE pt.is_focus = 1
            GROUP BY pt.id, pt.name, pt.focus_started_at
            LIMIT 1
        ''')
        row = cursor.fetchone()
    return dict(row) if row else None

# --- Spaced Repetition (SRS) Helpers ---

def update_srs_status(problem_id: int, difficulty: int):
    """
    Updates the Spaced Repetition schedule for a problem based on user-rated difficulty.
    Difficulty scale: 1 (Easy) to 5 (Hard).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch current review stage
        cursor.execute("SELECT review_stage FROM problems WHERE id = ?", (problem_id,))
        row = cursor.fetchone()
        
        # If problem doesn't exist, exit safely
        if not row:
            return
            
        current_stage = row[0] if row[0] is not None else 0
        
        # 2. Algorithm Logic
        if difficulty >= 4:
            # Got it wrong or found it very hard -> Reset the interval
            new_stage = 0
            days_to_add = 1
        elif difficulty == 3:
            # Medium -> Keep the same stage but push it out slightly
            new_stage = current_stage
            days_to_add = 3 if current_stage == 0 else (current_stage * 2)
        else:
            # Easy/Perfect -> Advance stage, exponential interval
            new_stage = current_stage + 1
            # Base logic: stage 1=3d, stage 2=7d, stage 3=14d, stage 4=30d
            intervals = [3, 7, 14, 30, 60, 120]
            stage_idx = min(new_stage, len(intervals) - 1)
            days_to_add = intervals[stage_idx]
            
        # 3. Apply Update
        cursor.execute('''
            UPDATE problems 
            SET difficulty = ?,
                review_stage = ?,
                next_review_date = datetime('now', '+' || ? || ' days')
            WHERE id = ?
        ''', (difficulty, new_stage, days_to_add, problem_id))

def get_srs_queue(limit: int = 5) -> list:
    """Returns problems that are past their scheduled `next_review_date`."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM problems
            WHERE next_review_date IS NOT NULL 
              AND next_review_date <= datetime('now')
            ORDER BY next_review_date ASC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_mock_interview_problems() -> list:
    """
    Selects 2 random unsolved problems that belong to DISTINCT patterns.
    This simulates a real interview where the user cannot guess the required approach.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            WITH Unsolved AS (
                SELECT p.*, pp.pattern_id
                FROM problems p
                LEFT JOIN solutions s ON p.id = s.problem_id
                LEFT JOIN problem_patterns pp ON p.id = pp.problem_id
                WHERE s.id IS NULL
            ),
            Randomized AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY pattern_id ORDER BY RANDOM()) as rn
                FROM Unsolved
            )
            SELECT id, name, topic, time_to_optimal, bugs, aha_moment, checklist_status, created_at, difficulty, review_stage, next_review_date
            FROM Randomized
            WHERE rn = 1
            ORDER BY RANDOM()
            LIMIT 2
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_daily_activity() -> list:
    """Returns a daily aggregation of solutions submitted over the last 365 days."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                date(submitted_at) as activity_date,
                COUNT(id) as count
            FROM solutions
            WHERE submitted_at >= datetime('now', '-365 days')
            GROUP BY date(submitted_at)
            ORDER BY activity_date ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_cheat_sheet_data() -> list:
    """Returns problems that have 'Aha!' moments or recorded bugs, grouped by their primary pattern."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.name as problem_name,
                p.bugs,
                p.aha_moment,
                pt.name as pattern_name
            FROM problems p
            LEFT JOIN problem_patterns pp ON p.id = pp.problem_id
            LEFT JOIN patterns pt ON pp.pattern_id = pt.id
            WHERE (p.bugs IS NOT NULL AND p.bugs != '') 
               OR (p.aha_moment IS NOT NULL AND p.aha_moment != '')
            ORDER BY pt.name ASC, p.name ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
