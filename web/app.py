import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
import math
from datetime import datetime

# Ensure scripts/ is on the path so shared utilities can be imported
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from utils import sanitize_name
from db import (
    get_problems_count, get_problems_page, update_problem_metadata,
    get_all_patterns, get_problems_for_pattern, get_patterns_for_problem,
    link_problem_to_pattern, get_solved_problems_count, get_todo_problems,
    get_analytics_by_pattern, get_stale_patterns, get_focus_pattern, set_focus_pattern,
    get_srs_queue, get_daily_activity, get_mock_interview_problems, get_cheat_sheet_data
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "dsa_data.db")
PATTERNS_DIR = os.path.join(DATA_DIR, "patterns")

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
        background: rgba(128, 128, 128, 0.15) !important;
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

    /* LLM Feedback Box */
    .llm-feedback-box {
        background: rgba(128, 128, 128, 0.1) !important;
        border: 1px solid rgba(150, 150, 150, 0.2) !important;
        border-radius: 12px;
        padding: 20px;
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.02);
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

# --- Tab Navigation ---
tab_main, tab_problems, tab_patterns, tab_metrics, tab_mock, tab_cheatsheet = st.tabs([
    "🏠 Dashboard", 
    "📚 Problems", 
    "🧩 Patterns", 
    "📈 Metrics",
    "🥊 Mock Interview",
    "💡 Cheat Sheet"
])

with tab_main:
    st.header("🏠 Main Dashboard")
    
    # --- Top Row Metrics ---
    total_probs = get_problems_count()
    total_solved = get_solved_problems_count()
    total_todos = total_probs - total_solved
    completion_rate = (total_solved / total_probs * 100) if total_probs > 0 else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Solved", f"{total_solved} / {total_probs}")
    m2.metric("Pending Todos", str(total_todos))
    m3.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    st.divider()
    
    # --- Current Focus Widget ---
    focus_pat = get_focus_pattern()
    if focus_pat:
        # Calculate days active
        started_at = datetime.strptime(focus_pat["focus_started_at"], "%Y-%m-%d %H:%M:%S")
        days_active = (datetime.now() - started_at).days
        
        # Determine warning class
        if days_active > 7:
            status_color = "#FF4B4B" # Red
            status_text = f"Stale Focus! Active for {days_active} days. Time to switch?"
        elif days_active > 4:
            status_color = "#FFA500" # Orange
            status_text = f"Active for {days_active} days. Keep going!"
        else:
            status_color = "#00FF00" # Green
            status_text = f"Fresh Focus! Active for {days_active} days."
            
        st.markdown(f"""
        <div style="background: rgba(138, 43, 226, 0.1); border: 1px solid rgba(138, 43, 226, 0.4); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: gray;">🎯 Current Focus Pattern</p>
            <h2 style="margin: 5px 0;">{focus_pat['pattern_name']}</h2>
            <p style="margin: 0; font-size: 18px; font-weight: bold; color: {status_color};">{status_text}</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: gray;">Progress: {focus_pat['solved_problems']} / {focus_pat['total_problems']} solved</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("🎯 You have no active focus pattern! Go to the **Patterns** tab to set one.")

    col_left, col_right = st.columns([2, 1], gap="large")
    
    with col_left:
        # --- Analytics Section ---
        st.subheader("📊 Pattern Progress")
        pattern_data = get_analytics_by_pattern()
        if pattern_data:
            df_patterns = pd.DataFrame(pattern_data)
            # Create a stacked bar chart showing solved vs un-solved per pattern
            df_patterns["unsolved"] = df_patterns["total_problems"] - df_patterns["solved_problems"]
            # Filter to patterns that actually have problems linked
            df_active = df_patterns[df_patterns["total_problems"] > 0].copy()
            
            if not df_active.empty:
                # We rename for the chart legend
                df_active = df_active.rename(columns={"solved_problems": "Solved", "unsolved": "Unsolved"})
                
                # Melt the dataframe for Altair stacked bar chart
                df_melted = df_active.melt(
                    id_vars=["pattern_name"], 
                    value_vars=["Solved", "Unsolved"],
                    var_name="Status", 
                    value_name="Count"
                )
                
                import altair as alt
                chart = alt.Chart(df_melted).mark_bar().encode(
                    x=alt.X('pattern_name:N', title="", axis=alt.Axis(labelAngle=-45, labelLimit=200)),
                    y=alt.Y('Count:Q', title="Problems"),
                    color=alt.Color('Status:N', 
                                    scale=alt.Scale(domain=['Solved', 'Unsolved'], 
                                                    range=['#00E5FF', '#333333'])),
                    tooltip=['pattern_name', 'Status', 'Count']
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No problems linked to patterns yet.")
        else:
            st.info("No pattern data available.")
            
        st.divider()
        
        # --- Todo Data Table ---
        st.subheader("📝 Problem Queue")
        todo_list = get_todo_problems(limit=100)  # load up to 100
        if todo_list:
            df_todo = pd.DataFrame(todo_list)
            # Annotate with patterns
            df_todo["pattern"] = df_todo["id"].apply(
                lambda pid: ", ".join(p["name"] for p in get_patterns_for_problem(int(pid)))
            )
            # Show a simplified subset
            display_cols = ["name", "topic", "pattern", "created_at"]
            st.dataframe(
                df_todo[display_cols],
                use_container_width=True,
                height=300,
                hide_index=True
            )
        else:
            st.success("Your Queue is empty! Great job!")

    with col_right:
        # --- SRS Review Queue ---
        srs_list = get_srs_queue(limit=5)
        if srs_list:
            st.subheader("🧠 SRS Review Due")
            for prob in srs_list:
                with st.container(border=True):
                    due_date = datetime.strptime(prob['next_review_date'], "%Y-%m-%d %H:%M:%S")
                    days_past = (datetime.now() - due_date).days
                    st.markdown(f"**{prob['name']}**")
                    time_label = "Today" if days_past <= 0 else f"{days_past} days overdue"
                    st.caption(f"Stage {prob['review_stage']} | ⚠️ {time_label}")
            st.divider()

        # --- Up Next ---
        st.subheader("🎯 Up Next")
        todo_list_short = get_todo_problems(limit=3)
        if todo_list_short:
            for prob in todo_list_short:
                with st.container(border=True):
                    st.markdown(f"**{prob['name']}**")
                    pat_links = get_patterns_for_problem(int(prob['id']))
                    pat_str = ", ".join(p["name"] for p in pat_links) if pat_links else "No Pattern"
                    topic_str = prob.get("topic") or "No Topic"
                    st.caption(f"🧩 {pat_str} | 🏷️ {topic_str}")
        else:
            st.info("Queue empty! Add more problems to solve.")
            
        st.divider()
        
        # --- Pattern Alert View ---
        st.subheader("🚨 Review Alerts")
        st.markdown("<p style='font-size: 14px; color: gray;'>Patterns not practiced recently (> 5 days).</p>", unsafe_allow_html=True)
        stale_patterns = get_stale_patterns(days_threshold=5)
        
        if stale_patterns:
            for pat in stale_patterns:
                date_str = pat['last_solved_date']
                if date_str:
                    # Format standard DB timestamp "YYYY-MM-DD HH:MM:SS" to "YYYY-MM-DD"
                    short_date = date_str.split(" ")[0]
                    alert_text = f"Last solved: {short_date}"
                    color = "orange"
                else:
                    alert_text = "Never solved"
                    color = "red"
                    
                st.markdown(f"**{pat['pattern_name']}**")
                st.markdown(f":{color}[_{alert_text}_]")
        else:
            st.success("All patterns are fresh! You've practiced everything recently.")


with tab_problems:
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

        # Overwrite pattern column with FK-linked pattern names
        problems_df["pattern"] = problems_df["id"].apply(
            lambda pid: ", ".join(p["name"] for p in get_patterns_for_problem(int(pid)))
        )

        # Editable table
        display_cols = ["id", "name", "link", "difficulty", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability", "checklist_status"]
        editable_cols = ["name", "link", "difficulty", "topic", "time_to_optimal", "bugs", "aha_moment", "time_complexity", "space_complexity", "l4_code_quality", "l4_edge_cases", "l4_scalability", "checklist_status"]

        # Keep a snapshot of the original data for diffing
        original_df = problems_df[display_cols].copy()

        column_config = {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "pattern": st.column_config.TextColumn("Patterns (linked)", disabled=True),
            "link": st.column_config.TextColumn("Link"),
            "difficulty": st.column_config.SelectboxColumn("Diff (1-5)", options=[1, 2, 3, 4, 5]),
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

            # Parse existing comma-separated topics
            current_topics = [t.strip() for t in str(prof_row.get("topic") or "").split(",") if t.strip()]

            # Load pattern links from FK join table
            all_db_patterns = get_all_patterns()
            all_pattern_names = [p["name"] for p in all_db_patterns]
            linked_patterns = get_patterns_for_problem(int(prob_id))
            current_pattern_names = [p["name"] for p in linked_patterns]

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
                    options=sorted(set(all_pattern_names)),
                    default=current_pattern_names,
                    key=f"patterns_{prob_id}"
                )

            # Check if tags changed
            new_topic_str = ", ".join(selected_topics)
            old_topic_str = ", ".join(current_topics)
            patterns_changed = set(selected_patterns) != set(current_pattern_names)

            if new_topic_str != old_topic_str or patterns_changed:
                tag_btn1, tag_btn2, _ = st.columns([1, 1, 10], gap="small")
                with tag_btn1:
                    if st.button("Save Tags", type="primary", key=f"save_tags_{prob_id}"):
                        # Save topic text
                        update_problem_metadata(int(prob_id), {
                            "topic": new_topic_str,
                            "pattern": ", ".join(selected_patterns)
                        })
                        # Sync FK links: delete removed, add new
                        conn = get_connection()
                        conn.execute("DELETE FROM problem_patterns WHERE problem_id = ?", (int(prob_id),))
                        conn.commit()
                        conn.close()
                        for pat_name in selected_patterns:
                            pat = next((p for p in all_db_patterns if p["name"] == pat_name), None)
                            if pat:
                                link_problem_to_pattern(int(prob_id), pat["id"])
                        st.success("Tags saved!")
                        st.rerun()
                with tag_btn2:
                    if st.button("Discard", key=f"discard_tags_{prob_id}"):
                        if f"topics_{prob_id}" in st.session_state:
                            del st.session_state[f"topics_{prob_id}"]
                        if f"patterns_{prob_id}" in st.session_state:
                            del st.session_state[f"patterns_{prob_id}"]
                        st.rerun()

            prob_file_path = os.path.join(DATA_DIR, "problems", sanitize_name(prof_row["name"]), "problem.md")
            if os.path.exists(prob_file_path):
                with st.expander("📝 Problem Statement", expanded=False):
                    with open(prob_file_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())

            solutions_df = load_solutions(prob_id)
            if not solutions_df.empty:
                st.markdown("### Solutions")

                # Create formatting for the dropdown options
                solution_options = []
                for _, row in solutions_df.iterrows():
                    fname = row['file_path'].split('/')[-1]
                    solution_options.append(f"{row['submitted_at']} - {fname} ({row['language']})")

                selected_option = st.selectbox(
                    "Select Submission:", 
                    options=solution_options,
                    index=0, 
                    key=f"sol_select_{prob_id}"
                )

                selected_idx = solution_options.index(selected_option)
                selected_sol = solutions_df.iloc[selected_idx]
                sol_id = selected_sol["id"]

                col1, col2 = st.columns(2)

                with col1:
                    header_str = f"**Viewing:** {selected_sol['file_path'].split('/')[-1]}"
                    if 'time_spent_seconds' in selected_sol and pd.notna(selected_sol['time_spent_seconds']):
                        ts = int(selected_sol['time_spent_seconds'])
                        header_str += f" &nbsp;|&nbsp; ⏱️ **Time:** {ts//60}m {ts%60}s"
                    st.markdown(header_str)

                    # Dynamically construct path using the current problem name slug
                    current_slug = sanitize_name(prof_row["name"])

                    # Backwards compatible: if the DB still has old absolute paths, just use them.
                    # If it's just a filename (the new way), prepend the directories.
                    if "/" in selected_sol["file_path"]:
                        sol_path = os.path.join(BASE_DIR, selected_sol["file_path"])
                    else:
                        sol_path = os.path.join(DATA_DIR, "problems", current_slug, "solutions", selected_sol["file_path"])

                    if os.path.exists(sol_path):
                        with open(sol_path, "r", encoding="utf-8") as f:
                            code = f.read()
                        st.code(code, language=selected_sol["language"])
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
                            fb_path = os.path.join(DATA_DIR, "problems", current_slug, "feedback", fb_raw_path)

                        if os.path.exists(fb_path):
                            with open(fb_path, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                                if content.startswith("```markdown"):
                                    content = content[11:]
                                if content.endswith("```"):
                                    content = content[:-3]
                            # Wrap the feedback inside a stylized div
                            st.markdown(f'<div class="llm-feedback-box">{content.strip()}</div>', unsafe_allow_html=True)

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

with tab_patterns:
    st.subheader("🧩 DSA Patterns")
    st.markdown('<p class="subtitle">Reusable code templates and recognition notes.</p>', unsafe_allow_html=True)
    
    search_query = st.text_input("🔍 Search Patterns", "")
    
    patterns_list = get_all_patterns()
    if not patterns_list:
        st.info("No patterns found. Add one with: `dsa pattern <name> --add`")
    else:
        for pat in patterns_list:
            if search_query and search_query.lower() not in pat["name"].lower() and (pat["notes"] and search_query.lower() not in pat["notes"].lower()):
                continue
            
            linked_probs = get_problems_for_pattern(pat["id"])
            prob_names = [p["name"] for p in linked_probs]
            
            with st.expander(f"{pat['name']} ({len(prob_names)} probs)"):
                col_btn, col_rest = st.columns([1, 4])
                with col_btn:
                    if st.button("🎯 Set as Focus", key=f"focus_{pat['id']}"):
                        set_focus_pattern(pat['id'])
                        st.success(f"Focus set to {pat['name']}!")
                        st.rerun()
                
                st.markdown("#### When to use")
                if pat["notes"]:
                    st.markdown(pat["notes"])
                else:
                    st.caption("No notes")
                
                # Render markdown documents from disk
                pattern_slug = sanitize_name(pat["name"])
                pattern_doc_dir = os.path.join(PATTERNS_DIR, pattern_slug)
                if os.path.isdir(pattern_doc_dir):
                    docs = sorted([f for f in os.listdir(pattern_doc_dir) if f.endswith(".md")])
                    if docs:
                        st.markdown("#### Documents")
                        for doc_name in docs:
                            doc_path = os.path.join(pattern_doc_dir, doc_name)
                            with open(doc_path, "r", encoding="utf-8") as f:
                                doc_content = f.read()
                            with st.expander(f"📄 {doc_name}"):
                                st.markdown(doc_content)
                
                if linked_probs:
                    st.markdown("**Linked Problems:**")
                    df_linked = pd.DataFrame(linked_probs)
                    display_cols = ["name", "topic", "time_to_optimal", "created_at"]
                    # Only keep columns that exist in the dataframe to prevent errors
                    display_cols = [c for c in display_cols if c in df_linked.columns]
                    st.dataframe(
                        df_linked[display_cols],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.markdown("**Linked Problems:** None")

with tab_metrics:
    # --- Analytics Header ---
    st.header("📈 Analytics")
    total_cost, _ = load_analytics()

    st.metric(label="Total LLM Review Cost (All Time)", value=f"${total_cost:.4f}")
    
    st.divider()
    st.subheader("🟩 Daily Activity Heatmap")
    
    activity_data = get_daily_activity()
    
    # Generate continuous last 365 days backbone
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.Timedelta(days=364)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    df_all = pd.DataFrame({'activity_date': all_dates})
    
    if activity_data:
        df_activity = pd.DataFrame(activity_data)
        df_activity['activity_date'] = pd.to_datetime(df_activity['activity_date'])
        df_merged = pd.merge(df_all, df_activity, on='activity_date', how='left').fillna({'count': 0})
    else:
        df_merged = df_all.copy()
        df_merged['count'] = 0.0

    # Calculate continuous week columns for GitHub style grid
    start_of_week = start_date - pd.Timedelta(days=start_date.dayofweek)
    df_merged['week_col'] = ((df_merged['activity_date'] - start_of_week).dt.days // 7)
    df_merged['day'] = df_merged['activity_date'].dt.day_name()
    
    # Sort days correctly (Mon-Sun)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    import altair as alt
    heatmap = alt.Chart(df_merged).mark_rect(cornerRadius=2).encode(
        x=alt.X('week_col:O', title='', axis=alt.Axis(labels=False, ticks=False), scale=alt.Scale(paddingInner=0.15)),
        y=alt.Y('day:O', title='', sort=day_order, axis=alt.Axis(domain=False, ticks=False), scale=alt.Scale(paddingInner=0.15)),
        color=alt.condition(
            alt.datum.count == 0,
            alt.value('rgba(128, 128, 128, 0.1)'), # Empty day color (adapts to light/dark themes via transparency)
            alt.Color('count:Q', 
                      title='Problems Solved',
                      scale=alt.Scale(scheme='greens', domain=[1, max(5, df_merged['count'].max())]))
        ),
        tooltip=[
            alt.Tooltip('activity_date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('count:Q', title='Solved')
        ]
    ).properties(
        width='container',
        height=180
    ).configure_view(
        strokeWidth=0
    )
    
    st.altair_chart(heatmap, use_container_width=True)

with tab_mock:
    st.header("🥊 Mock Interview")
    st.markdown("Test your skills by solving 2 hidden random problems in 45 minutes. *No pattern tags allowed!*")
    
    if "mock_problems" not in st.session_state:
        st.session_state.mock_problems = []
    if "mock_start_time" not in st.session_state:
        st.session_state.mock_start_time = None
        
    col_btn, col_timer, _ = st.columns([1, 1, 3])
    with col_btn:
        if st.button("🔄 Generate Interview", type="primary"):
            st.session_state.mock_problems = get_mock_interview_problems()
            st.session_state.mock_start_time = datetime.now()
            st.rerun()
            
    with col_timer:
        if st.session_state.mock_start_time:
            # 45 minutes = 2700 seconds
            elapsed = (datetime.now() - st.session_state.mock_start_time).total_seconds()
            remaining = max(0, 2700 - elapsed)
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            if remaining > 0:
                st.markdown(f"### ⏳ {mins:02d}:{secs:02d}")
            else:
                st.markdown("### 🚨 **TIME UP!**")
            
    if st.session_state.mock_problems:
        st.divider()
        col1, col2 = st.columns(2)
        
        for i, prob in enumerate(st.session_state.mock_problems):
            target_col = col1 if i == 0 else col2
            with target_col:
                with st.container(border=True):
                    # Mask everything, just show name and link
                    st.markdown(f"### Q{i+1}: {prob['name']}")
                    
                    # Display the problem.md statement if it exists
                    from utils import sanitize_name
                    prob_slug = sanitize_name(prob['name'])
                    prob_file_path = os.path.join(DATA_DIR, "problems", prob_slug, "problem.md")
                    
                    if os.path.exists(prob_file_path):
                        with st.expander("📝 Show Problem Statement"):
                            with open(prob_file_path, "r", encoding="utf-8") as f:
                                st.markdown(f.read())
                    else:
                        st.info("No local markdown provided. Click the link above.")
    else:
        st.info("Click the button above to start your mock interview.")

with tab_cheatsheet:
    st.header("💡 The 'Aha!' Cheat Sheet")
    st.markdown("Your personalized 5-minute pre-interview warm-up page. Only showing problems where you explicitly logged 'Aha! Moments' or 'Bugs'.")
    
    cheat_data = get_cheat_sheet_data()
    if cheat_data:
        # Group by pattern
        grouped_data = {}
        for row in cheat_data:
            pat_name = row['pattern_name'] or "Uncategorized"
            if pat_name not in grouped_data:
                grouped_data[pat_name] = []
            grouped_data[pat_name].append(row)
            
        # Render
        for pat_name, probs in grouped_data.items():
            st.subheader(f"🧩 {pat_name}")
            for p in probs:
                with st.expander(f"**{p['problem_name']}**", expanded=True):
                    if p['aha_moment']:
                        st.markdown(f"💡 **Aha! Moment:** {p['aha_moment']}")
                    if p['bugs']:
                        st.markdown(f"🐛 **Bugs:** {p['bugs']}")
            st.divider()
    else:
        st.info("No 'Aha!' moments or bugs logged yet! Run `dsa log` on your problems to populate this list.")
