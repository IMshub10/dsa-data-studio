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
from db import get_problems_count, get_problems_page

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "dsa_data.db")

PAGE_SIZE = 20

st.set_page_config(page_title="DSA Data Studio", layout="wide")

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

# --- Page title ---

st.title("🧑‍💻 DSA Data Studio")
st.markdown("Track your LeetCode problem solving progress and view LLM optimizations.")

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

    # Table
    display_cols = ["id", "name", "topic", "pattern", "time_to_optimal", "bugs", "aha_moment", "checklist_status"]
    
    # Increase font size for better readability
    if not problems_df.empty:
        styled_df = problems_df[display_cols].style.set_properties(**{'font-size': '16px'})
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.dataframe(problems_df[display_cols], use_container_width=True, height=400)

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
                sol_path = os.path.join(BASE_DIR, latest_sol["file_path"])
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
                    fb_path = os.path.join(BASE_DIR, feedback_df.iloc[0]["feedback_path"])
                    if os.path.exists(fb_path):
                        with open(fb_path, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if content.startswith("```markdown"):
                                content = content[11:]
                            if content.endswith("```"):
                                content = content[:-3]
                            st.markdown(content.strip())
                    else:
                        st.error("Feedback file not found.")
                else:
                    st.info("No LLM feedback generated yet for this solution. Run `dsa review`.")
        else:
            st.info("No solutions submitted yet for this problem.")
