import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
import math

# Ensure scripts/ is on the path so shared utilities can be imported
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from utils import sanitize_name
from db import get_problems_count, get_problems_page, update_problem_metadata

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "dsa_data.db")

PAGE_SIZE = 20

# Predefined DSA categories
DSA_TOPICS = [
    "Arrays", "Strings", "Linked List", "Stack", "Queue", "Hash Table",
    "Trees", "Binary Search", "Graphs", "Dynamic Programming", "Greedy",
    "Backtracking", "Bit Manipulation", "Math", "Sorting", "Heap",
    "Trie", "Union Find", "Sliding Window", "Recursion", "Matrix",
    "Intervals", "Design", "Simulation",
]

DSA_PATTERNS = [
    "Two Pointers", "Sliding Window", "Fast & Slow Pointers",
    "Merge Intervals", "Cyclic Sort", "In-place Reversal",
    "BFS", "DFS", "Binary Search", "Top K Elements",
    "K-way Merge", "Knapsack", "Topological Sort",
    "Monotonic Stack", "Kadane's Algorithm", "Prefix Sum",
    "Divide and Conquer", "Bit Masking", "Floyd's Cycle",
    "Reservoir Sampling", "Bucket Sort",
]

st.set_page_config(page_title="DSA Data Studio", layout="wide")

# --- Custom Styling ---

st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    /* Global styling */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: 0.2px;
    }

    /* Headings & Gradient text */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -1px !important;
        background: -webkit-linear-gradient(45deg, #00E5FF, #8A2BE2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px !important;
    }
    h2, h3, h4 {
        font-weight: 600 !important;
        color: var(--text-color) !important;
    }

    /* Subtitle text */
    .subtitle {
        font-size: 18px;
        margin-top: -5px;
        margin-bottom: 30px;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 300;
    }

    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        color: var(--primary-color) !important;
        font-weight: 700 !important;
        font-size: 2.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-color) !important;
        opacity: 0.7;
        font-size: 1rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Glassmorphism Data Editor container */
    [data-testid="stDataEditor"] {
        border-radius: 12px;
        border: 1px solid var(--secondary-background-color) !important;
        background: transparent !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
    }

    /* Tags styling */
    span[data-baseweb="tag"] {
        background: transparent !important;
        color: var(--text-color) !important;
        border: 1px solid rgba(150, 150, 150, 0.4) !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 4px 12px !important;
    }
    span[data-baseweb="tag"] span[role="presentation"] {
        color: var(--text-color) !important;
        opacity: 0.7;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        border: 1px solid rgba(150, 150, 150, 0.4) !important;
        background-color: transparent !important;
        color: var(--text-color) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        border-color: var(--primary-color) !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00E5FF, #8A2BE2) !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
        transform: translateY(-2px) !important;
    }

    /* Expanders (accordion) */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 16px !important;
        background: transparent !important;
        border-radius: 8px !important;
        transition: background 0.2s ease;
    }
    .streamlit-expanderHeader:hover {
        background: var(--secondary-background-color) !important;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--secondary-background-color) !important;
        border-radius: 8px !important;
        background: transparent !important;
    }

    /* Dividers */
    hr { 
        border-color: var(--secondary-background-color) !important; 
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
    }
    
    /* Chart Area */
    [data-testid="stChart"] {
        background: transparent !important;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid var(--secondary-background-color);
    }
</style>
""", unsafe_allow_html=True)

# --- Helper DB functions for detail view ---

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_solutions(problem_id):
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM solutions WHERE problem_id = ? ORDER BY submitted_at DESC",
            conn, params=(int(problem_id),)
        )

def load_feedback(solution_id):
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM feedback WHERE solution_id = ? ORDER BY created_at DESC",
            conn, params=(int(solution_id),)
        )

def load_api_usage(problem_id):
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM api_usage_logs WHERE problem_id = ? ORDER BY created_at DESC",
            conn, params=(int(problem_id),)
        )

def load_analytics():
    """Returns a tuple of (total_cost, df_daily_problems) for the dashboard header."""
    with get_connection() as conn:
        # Total Cost
        cost_df = pd.read_sql_query("SELECT SUM(estimated_cost_usd) as total FROM api_usage_logs", conn)
        total_cost = cost_df.iloc[0]["total"] if not pd.isna(cost_df.iloc[0]["total"]) else 0.0
        
        # Problems Solved per Day (Last 14 days)
        daily_df = pd.read_sql_query("""
            SELECT date(created_at) as solved_date, COUNT(*) as count 
            FROM problems 
            WHERE created_at >= date('now', '-14 days')
            GROUP BY date(created_at)
            ORDER BY solved_date ASC
        """, conn)
        
        # Ensure 'solved_date' is a proper datetime or str that Streamlit charts can use as index
        if not daily_df.empty:
            daily_df["solved_date"] = pd.to_datetime(daily_df["solved_date"])
            daily_df.set_index("solved_date", inplace=True)
            
        return total_cost, daily_df

# --- Page title ---

st.title("DSA Data Studio")
st.markdown('<p class="subtitle">Track your LeetCode problem solving progress and view LLM optimizations.</p>', unsafe_allow_html=True)

# --- Problem Log with pagination ---

st.header("📚 Problem Log")

total = get_problems_count()

if total == 0:
    st.info("No problems recorded yet. Use `dsa new <problem_name>` to get started.")
else:
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    # Initialise page in session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # Clamp in case rows were deleted
    st.session_state.current_page = min(st.session_state.current_page, total_pages)

    page_rows = get_problems_page(st.session_state.current_page, PAGE_SIZE)
    problems_df = pd.DataFrame(page_rows)

    # Editable table
    display_cols = ["id", "name", "link", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability", "checklist_status"]
    editable_cols = ["name", "link", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability", "checklist_status"]

    # Keep a snapshot of the original data for diffing
    original_df = problems_df[display_cols].copy()

    column_config = {
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "link": st.column_config.TextColumn("Link"),
        "time_complexity": st.column_config.TextColumn("Time Complex"),
        "space_complexity": st.column_config.TextColumn("Space Complex"),
        "l4_code_quality": st.column_config.SelectboxColumn("Code Quality", options=["", "Needs Work", "Good", "Strong"]),
        "l4_edge_cases": st.column_config.SelectboxColumn("Edge Cases", options=["", "Missed", "Handled", "Documented"]),
        "l4_scalability": st.column_config.SelectboxColumn("Scalability", options=["", "Missed", "Discussed", "Strong Context"]),
    }

    edited_df = st.data_editor(
        problems_df[display_cols],
        column_config=column_config,
        use_container_width=True,
        height=400,
        num_rows="fixed",
        key="problem_editor"
    )

    # Detect changes
    changed_mask = (edited_df[editable_cols].fillna("") != original_df[editable_cols].fillna("")).any(axis=1)
    changed_rows = edited_df[changed_mask]

    if not changed_rows.empty:
        st.warning(f"You have unsaved changes in **{len(changed_rows)} row(s)**.")

        with st.expander("Preview changes", expanded=True):
            for _, row in changed_rows.iterrows():
                orig = original_df[original_df["id"] == row["id"]].iloc[0]
                st.markdown(f"**{row['name']}**")
                for col in editable_cols:
                    old_val = str(orig[col]) if pd.notna(orig[col]) else ""
                    new_val = str(row[col]) if pd.notna(row[col]) else ""
                    if old_val != new_val:
                        st.markdown(f"- `{col}`: ~~{old_val or '(empty)'}~~ → **{new_val or '(empty)'}**")

        btn_col1, btn_col2, _ = st.columns([1, 1, 10], gap="small")
        with btn_col1:
            if st.button("Save Changes", type="primary"):
                for _, row in changed_rows.iterrows():
                    orig_row = original_df[original_df["id"] == row["id"]].iloc[0]
                    metadata = {col: row[col] for col in editable_cols}
                    
                    # If name was changed, rename the local directory
                    # The DB only stores bare filenames for solutions/feedback now, so we don't need to bulk update child paths!
                    if row["name"] != orig_row["name"]:
                        old_slug = sanitize_name(orig_row["name"])
                        new_slug = sanitize_name(row["name"])
                        old_path = os.path.join(BASE_DIR, "problems", old_slug)
                        new_path = os.path.join(BASE_DIR, "problems", new_slug)
                        if os.path.exists(old_path) and not os.path.exists(new_path):
                            os.rename(old_path, new_path)
                            
                    print(f"DEBUG SAVING ID {row['id']}: {metadata}")
                    update_problem_metadata(int(row["id"]), metadata)
                st.success(f"Saved {len(changed_rows)} row(s) to database!")
                if "problem_editor" in st.session_state:
                    del st.session_state["problem_editor"]
                st.rerun()
        with btn_col2:
            if st.button("Discard"):
                if "problem_editor" in st.session_state:
                    del st.session_state["problem_editor"]
                st.rerun()

    # Pagination controls
    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Prev", disabled=(st.session_state.current_page <= 1)):
            st.session_state.current_page -= 1
            st.rerun()
    with col_info:
        start = (st.session_state.current_page - 1) * PAGE_SIZE + 1
        end = min(st.session_state.current_page * PAGE_SIZE, total)
        st.markdown(
            f"<div style='text-align:center; padding-top:6px;'>Page <b>{st.session_state.current_page}</b> of <b>{total_pages}</b> &nbsp;·&nbsp; showing {start}–{end} of {total}</div>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.button("Next →", disabled=(st.session_state.current_page >= total_pages)):
            st.session_state.current_page += 1
            st.rerun()

    st.divider()

    # --- Detail View ---
    st.header("🔍 Detail View")

    problem_names = problems_df["name"].tolist()
    selected_name = st.selectbox(
        "Select a problem from this page to view details:",
        options=[None] + problem_names,
        format_func=lambda x: "— select a problem —" if x is None else x
    )

    if selected_name:
        prof_row = problems_df[problems_df["name"] == selected_name].iloc[0]
        prob_id = prof_row["id"]

        st.subheader(f"{prof_row['name']}")
        if prof_row["link"]:
            st.markdown(f"**Link:** [Problem URL]({prof_row['link']})")

        # --- Topic & Pattern multi-select tagging ---
        st.markdown("#### Tags")
        tag_col1, tag_col2 = st.columns(2)

        # Parse existing comma-separated values into lists
        current_topics = [t.strip() for t in str(prof_row.get("topic") or "").split(",") if t.strip()]
        current_patterns = [p.strip() for p in str(prof_row.get("pattern") or "").split(",") if p.strip()]

        with tag_col1:
            selected_topics = st.multiselect(
                "Topics",
                options=sorted(set(DSA_TOPICS + current_topics)),
                default=current_topics,
                key=f"topics_{prob_id}"
            )
        with tag_col2:
            selected_patterns = st.multiselect(
                "Patterns",
                options=sorted(set(DSA_PATTERNS + current_patterns)),
                default=current_patterns,
                key=f"patterns_{prob_id}"
            )

        # Check if tags changed
        new_topic_str = ", ".join(selected_topics)
        new_pattern_str = ", ".join(selected_patterns)
        old_topic_str = ", ".join(current_topics)
        old_pattern_str = ", ".join(current_patterns)

        if new_topic_str != old_topic_str or new_pattern_str != old_pattern_str:
            tag_btn1, tag_btn2, _ = st.columns([1, 1, 10], gap="small")
            with tag_btn1:
                if st.button("Save Tags", type="primary", key=f"save_tags_{prob_id}"):
                    update_problem_metadata(int(prob_id), {
                        "topic": new_topic_str,
                        "pattern": new_pattern_str
                    })
                    st.success("Tags saved!")
                    st.rerun()
            with tag_btn2:
                if st.button("Discard", key=f"discard_tags_{prob_id}"):
                    if f"topics_{prob_id}" in st.session_state:
                        del st.session_state[f"topics_{prob_id}"]
                    if f"patterns_{prob_id}" in st.session_state:
                        del st.session_state[f"patterns_{prob_id}"]
                    st.rerun()

        prob_file_path = os.path.join(BASE_DIR, "problems", sanitize_name(prof_row["name"]), "problem.md")
        if os.path.exists(prob_file_path):
            with st.expander("📝 Problem Statement", expanded=False):
                with open(prob_file_path, "r", encoding="utf-8") as f:
                    st.markdown(f.read())

        solutions_df = load_solutions(prob_id)
        if not solutions_df.empty:
            st.markdown("### Solutions")

            latest_sol = solutions_df.iloc[0]
            sol_id = latest_sol["id"]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Latest Submission:** {latest_sol['submitted_at']} ({latest_sol['language']})")
                
                # Dynamically construct path using the current problem name slug
                current_slug = sanitize_name(prof_row["name"])
                
                # Backwards compatible: if the DB still has old absolute paths, just use them.
                # If it's just a filename (the new way), prepend the directories.
                if "/" in latest_sol["file_path"]:
                    sol_path = os.path.join(BASE_DIR, latest_sol["file_path"])
                else:
                    sol_path = os.path.join(BASE_DIR, "problems", current_slug, "solutions", latest_sol["file_path"])
                    
                if os.path.exists(sol_path):
                    with open(sol_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    st.code(code, language=latest_sol["language"])
                else:
                    st.error(f"File not found: {sol_path}")

            with col2:
                st.markdown("**LLM Feedback**")
                feedback_df = load_feedback(sol_id)
                if not feedback_df.empty:
                    fb_raw_path = feedback_df.iloc[0]["feedback_path"]
                    if "/" in fb_raw_path:
                        fb_path = os.path.join(BASE_DIR, fb_raw_path)
                    else:
                        fb_path = os.path.join(BASE_DIR, "problems", current_slug, "feedback", fb_raw_path)
                        
                    if os.path.exists(fb_path):
                        with open(fb_path, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if content.startswith("```markdown"):
                                content = content[11:]
                            if content.endswith("```"):
                                content = content[:-3]
                            st.markdown(content.strip())
                            
                        # Show API Usage if available
                        usage_df = load_api_usage(prob_id)
                        if not usage_df.empty:
                            latest_usage = usage_df.iloc[0]
                            st.caption(f"🤖 **Model:** `{latest_usage['model_name']}`  |  "
                                       f"🪙 **Tokens:** {latest_usage['input_tokens']:,} in, {latest_usage['output_tokens']:,} out  |  "
                                       f"💳 **Cost:** ${latest_usage['estimated_cost_usd']:.5f}")
                    else:
                        st.error("Feedback file not found.")
                else:
                    st.info("No LLM feedback generated yet for this solution. Run `dsa review`.")
        else:
            st.info("No solutions submitted yet for this problem.")

st.divider()

# --- Analytics Header ---
st.header("📈 Analytics")
total_cost, daily_df = load_analytics()

col1, col2 = st.columns([1, 4])
with col1:
    st.metric(label="Total LLM Review Cost (All Time)", value=f"${total_cost:.4f}")
    
with col2:
    if not daily_df.empty:
        st.line_chart(daily_df, y="count", height=150, x_label="Date", y_label="Problems Solved")
    else:
        st.info("Solve a problem to see your activity chart!")
