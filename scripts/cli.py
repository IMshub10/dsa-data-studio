import os
import shutil
import sqlite3
from datetime import datetime
import typer
from db import init_db, create_problem, get_problem_by_name, add_solution, get_latest_solution, add_feedback, update_problem_metadata, delete_problem_from_db
from llm.factory import get_llm_provider
from utils import sanitize_name

app = typer.Typer(help="DSA Data Studio CLI for managing LeetCode solutions and LLM feedback.")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROBLEMS_DIR = os.path.join(BASE_DIR, "problems")

@app.command()
def init():
    """Initialize the local DB."""
    init_db()
    os.makedirs(PROBLEMS_DIR, exist_ok=True)
    typer.echo("Database and directories initialized.")

@app.command()
def new(name: str, link: str = ""):
    """Create a new problem folder and DB entry."""
    safe_name = sanitize_name(name)
    problem_dir = os.path.join(PROBLEMS_DIR, safe_name)
    
    if os.path.exists(problem_dir):
        typer.echo(f"Problem folder {safe_name} already exists.")
        return
        
    os.makedirs(os.path.join(problem_dir, "solutions"))
    os.makedirs(os.path.join(problem_dir, "feedback"))
    
    prob_file = os.path.join(problem_dir, "problem.md")
    with open(prob_file, "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\nLink: {link}\n\n[Paste your problem description here]\n")
        
    problem_id = create_problem(safe_name, link)
    typer.echo(f"Created problem {safe_name} with DB ID: {problem_id}")
    typer.echo(f"Please fill in the problem description at: {prob_file}")

@app.command()
def submit(problem_name: str, solution_file: str):
    """Submit a solution file for a problem. Copies it and logs to DB."""
    safe_name = sanitize_name(problem_name)
    problem = get_problem_by_name(safe_name)
    
    if not problem:
        typer.echo(f"Problem {safe_name} not found in DB. Run 'dsa new' first.")
        return
        
    problem_dir = os.path.join(PROBLEMS_DIR, safe_name)
    if not os.path.exists(problem_dir):
        typer.echo(f"Directory {problem_dir} not found.")
        return
        
    if not os.path.isfile(solution_file):
        typer.echo(f"Solution file {solution_file} not found.")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(solution_file)[1]
    language = "python" if ext == ".py" else ("java" if ext == ".java" else "text")
    
    dest_filename = f"{timestamp}_solution{ext}"
    dest_path = os.path.join(problem_dir, "solutions", dest_filename)
    
    shutil.copy2(solution_file, dest_path)
    # Store relative path for portability
    rel_path = os.path.join("problems", safe_name, "solutions", dest_filename)
    
    solution_id = add_solution(problem["id"], rel_path, language)
    typer.echo(f"Successfully submitted solution: {dest_path}")
    typer.echo(f"Logged to DB with Solution ID: {solution_id}")

@app.command()
def review(problem_name: str):
    """Generate LLM review for the latest solution of a problem."""
    safe_name = sanitize_name(problem_name)
    problem = get_problem_by_name(safe_name)
    if not problem:
        typer.echo("Problem not found.")
        return

    latest_sol = get_latest_solution(problem["id"])
    if not latest_sol:
        typer.echo("No solutions found for this problem.")
        return
        
    problem_dir = os.path.join(PROBLEMS_DIR, safe_name)
    prob_file = os.path.join(problem_dir, "problem.md")
    
    if not os.path.exists(prob_file):
        typer.echo("Problem description file missing.")
        return
        
    with open(prob_file, "r", encoding="utf-8") as f:
        problem_statement = f.read()
        
    sol_path = os.path.join(BASE_DIR, latest_sol["file_path"])
    with open(sol_path, "r", encoding="utf-8") as f:
        solution_code = f.read()
        
    typer.echo("Requesting review from LLM...")
    try:
        provider = get_llm_provider()
        feedback = provider.generate_review(problem_statement, solution_code, latest_sol["language"])
    except Exception as e:
        typer.echo(f"Failed to get review: {e}")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fb_filename = f"{timestamp}_review.md"
    fb_path = os.path.join(problem_dir, "feedback", fb_filename)
    
    with open(fb_path, "w", encoding="utf-8") as f:
        f.write(feedback)
        
    rel_fb_path = os.path.join("problems", safe_name, "feedback", fb_filename)
    add_feedback(latest_sol["id"], rel_fb_path)
    
    typer.echo(f"Review successfully generated and saved to {fb_path}")

@app.command()
def log(problem_name: str):
    """Interactively log metadata for a problem."""
    safe_name = sanitize_name(problem_name)
    problem = get_problem_by_name(safe_name)
    if not problem:
        typer.echo("Problem not found.")
        return
        
    typer.echo(f"Logging metadata for {problem_name}:")
    topic = typer.prompt("Topic (e.g. Arrays, DP, Strings)", default="", show_default=False)
    pattern = typer.prompt("Pattern (e.g. Two Pointers, Sliding Window)", default="", show_default=False)
    time_to_optimal = typer.prompt("Time to Optimal Logic (e.g. 15m, 1h)", default="", show_default=False)
    bugs = typer.prompt("Bugs encountered", default="", show_default=False)
    aha_moment = typer.prompt("Aha! moment", default="", show_default=False)
    checklist_status = typer.prompt("Checklist Status (Todo, In Progress, Done)", default="Done")
    
    metadata = {
        "topic": topic,
        "pattern": pattern,
        "time_to_optimal": time_to_optimal,
        "bugs": bugs,
        "aha_moment": aha_moment,
        "checklist_status": checklist_status
    }
    
    update_problem_metadata(problem["id"], metadata)
    typer.echo("Metadata updated successfully.")

@app.command()
def delete(problem_name: str, force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation")):
    """Delete a problem and all associated files/solutions from disk and the database."""
    safe_name = sanitize_name(problem_name)
    problem = get_problem_by_name(safe_name)
    
    if not problem:
        typer.echo(f"Problem '{problem_name}' not found in the database.")
        return

    if not force:
        confirm = typer.confirm(f"Are you sure you want to completely delete '{problem_name}'? This cannot be undone.")
        if not confirm:
            typer.echo("Deletion cancelled.")
            return

    # Delete from database (cascades not automatically set up in python sqlite by default unless PRAGMA is on, 
    # so we'll delete explicitly in the db script to be safe)
    typer.echo(f"Deleting DB records for '{safe_name}'...")
    delete_problem_from_db(problem["id"])
    
    # Delete from file system
    problem_dir = os.path.join(PROBLEMS_DIR, safe_name)
    if os.path.exists(problem_dir):
        typer.echo(f"Removing directory: {problem_dir}")
        shutil.rmtree(problem_dir)
    else:
        typer.echo(f"Directory {problem_dir} not found. Skipping file deletion.")
        
    typer.echo(f"Successfully deleted problem '{problem_name}'.")

if __name__ == "__main__":
    app()
