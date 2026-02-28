import os
import shutil
import sqlite3
from datetime import datetime
import typer
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path, override=True)

from db import (
    init_db, create_problem, get_problem_by_name, add_solution, get_latest_solution, 
    add_feedback, update_problem_metadata, delete_problem_from_db, add_api_usage,
    insert_pattern, get_pattern_by_name, get_all_patterns, link_problem_to_pattern, get_problems_for_pattern,
    get_analytics_by_pattern
)
from llm.factory import get_llm_provider
from utils import sanitize_name

app = typer.Typer(help="DSA Data Studio CLI for managing LeetCode solutions and LLM feedback.")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROBLEMS_DIR = os.path.join(DATA_DIR, "problems")
PATTERNS_DIR = os.path.join(DATA_DIR, "patterns")

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
    # Store only the filename; the app will construct the path dynamically based on current problem name
    solution_id = add_solution(problem["id"], dest_filename, language)
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
        
    raw_path = latest_sol["file_path"]
    if "/" in raw_path:
        sol_path = os.path.join(BASE_DIR, raw_path)
    else:
        sol_path = os.path.join(problem_dir, "solutions", raw_path)
    with open(sol_path, "r", encoding="utf-8") as f:
        solution_code = f.read()
        
    typer.echo("Requesting review from LLM...")
    try:
        provider = get_llm_provider()
        feedback, in_tokens, out_tokens = provider.generate_review(problem_statement, solution_code, latest_sol["language"])
        
        # Calculate estimated cost based on common model pricing (Per 1M tokens)
        model_name = getattr(provider, "model_name", "unknown")
        provider_name = provider.__class__.__name__
        cost = 0.0
        
        if "gpt-4o-mini" in model_name:
            cost = (in_tokens / 1_000_000) * 0.150 + (out_tokens / 1_000_000) * 0.600
        elif "gpt-4o" in model_name:
            cost = (in_tokens / 1_000_000) * 2.50 + (out_tokens / 1_000_000) * 10.00
        elif "o1-mini" in model_name:
            cost = (in_tokens / 1_000_000) * 3.00 + (out_tokens / 1_000_000) * 12.00
        elif "o3-mini" in model_name:
            cost = (in_tokens / 1_000_000) * 1.10 + (out_tokens / 1_000_000) * 4.40
        elif "sonnet" in model_name:
            cost = (in_tokens / 1_000_000) * 3.00 + (out_tokens / 1_000_000) * 15.00
        elif "haiku" in model_name:
            cost = (in_tokens / 1_000_000) * 0.80 + (out_tokens / 1_000_000) * 4.00
        elif "opus" in model_name:
            cost = (in_tokens / 1_000_000) * 15.00 + (out_tokens / 1_000_000) * 75.00
        else:
            cost = 0.0 # Default fallback
            
        add_api_usage(problem["id"], provider_name, model_name, in_tokens, out_tokens, cost)
            
    except Exception as e:
        typer.echo(f"Failed to get review: {e}")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fb_filename = f"{timestamp}_review.md"
    fb_path = os.path.join(problem_dir, "feedback", fb_filename)
    
    with open(fb_path, "w", encoding="utf-8") as f:
        f.write(feedback)
        
    # Store only the filename; path is constructed dynamically
    add_feedback(latest_sol["id"], fb_filename)
    
    typer.echo(f"Review successfully generated and saved to {fb_path}")
    typer.echo(f"  Tokens usage: {in_tokens} input, {out_tokens} output")
    typer.echo(f"  Estimated cost: ${cost:.5f}")

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
    
    # Prompt for linking to a global DSA pattern (numbered selection)
    all_pats = get_all_patterns()
    if all_pats:
        typer.echo("\nAvailable patterns:")
        for i, p in enumerate(all_pats, 1):
            typer.echo(f"  {i}. {p['name']}")
        typer.echo("  0. Skip")
        selection = typer.prompt("Select patterns (comma-separated numbers)", default="0")
        if selection.strip() != "0":
            for num_str in selection.split(","):
                num_str = num_str.strip()
                if num_str.isdigit() and 1 <= int(num_str) <= len(all_pats):
                    pat = all_pats[int(num_str) - 1]
                    link_problem_to_pattern(problem["id"], pat["id"])
                    typer.echo(f"✅ Linked to {pat['name']}.")
                elif num_str != "0":
                    typer.echo(f"⚠️  Invalid selection: {num_str}")

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

@app.command()
def pattern(
    name: str,
    add: bool = typer.Option(False, "--add", "-a"),
    link: str = typer.Option(None, "--link", "-l"),
    add_doc: str = typer.Option(None, "--add-doc", "-d", help="Create a markdown document for this pattern")
):
    """View, add, or link a DSA pattern."""
    safe_name = name.strip()
    pattern_slug = sanitize_name(safe_name)
    pattern_dir = os.path.join(PATTERNS_DIR, pattern_slug)
    
    if add:
        notes = typer.prompt("When to use (notes)", default="", show_default=False)
        
        try:
            pattern_id = insert_pattern(safe_name, notes)
            os.makedirs(pattern_dir, exist_ok=True)
            typer.echo(f"✅ Added pattern '{safe_name}' (ID: {pattern_id})")
            typer.echo(f"📁 Folder: {pattern_dir}")
            typer.echo(f"   Add documents with: ./dsa pattern \"{safe_name}\" --add-doc \"<name>\"")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                typer.echo(f"❌ Pattern '{safe_name}' already exists.")
            else:
                typer.echo(f"❌ Error adding pattern: {e}")
        return

    if add_doc:
        pat = get_pattern_by_name(safe_name)
        if not pat:
            typer.echo(f"❌ Pattern '{safe_name}' not found. Add it first using --add.")
            return
        
        doc_slug = sanitize_name(add_doc)
        doc_path = os.path.join(pattern_dir, f"{doc_slug}.md")
        os.makedirs(pattern_dir, exist_ok=True)
        
        if os.path.exists(doc_path):
            typer.echo(f"❌ Document '{doc_slug}.md' already exists.")
            return
        
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(f"# {add_doc}\n\n")
            f.write(f"[Describe when to use this variant]\n\n")
            f.write(f"## Template\n\n")
            f.write(f"```java\n// paste your code here\n```\n")
        
        typer.echo(f"✅ Created document: {doc_path}")
        typer.echo(f"   Edit this file to add your notes and code template.")
        return

    if link:
        safe_prob_name = sanitize_name(link)
        problem = get_problem_by_name(safe_prob_name)
        if not problem:
            typer.echo(f"❌ Problem '{safe_prob_name}' not found. Run 'dsa new' first.")
            return
            
        pat = get_pattern_by_name(safe_name)
        if not pat:
            typer.echo(f"❌ Pattern '{safe_name}' not found. Add it first using --add.")
            return
            
        link_problem_to_pattern(problem["id"], pat["id"])
        typer.echo(f"✅ Linked problem '{safe_prob_name}' to pattern '{safe_name}'.")
        return

    # View mode
    pat = get_pattern_by_name(safe_name)
    if not pat:
        typer.echo(f"❌ Pattern '{safe_name}' not found. Add it first using --add.")
        return
        
    typer.echo(f"\nPattern: {pat['name']}")
    typer.echo("──────────────────────────────")
    typer.echo("When to use:")
    if pat["notes"]:
        for line in pat["notes"].split('\n'):
            typer.echo(f"  - {line}")
    else:
        typer.echo("  (No notes)")

    typer.echo("\nDocuments:")
    if os.path.isdir(pattern_dir):
        docs = sorted([f for f in os.listdir(pattern_dir) if f.endswith(".md")])
        if docs:
            for d in docs:
                typer.echo(f"  → {d}")
        else:
            typer.echo("  (No documents yet — use --add-doc to create one)")
    else:
        typer.echo("  (No documents yet — use --add-doc to create one)")
        
    typer.echo("\nLinked Problems:")
    problems = get_problems_for_pattern(pat["id"])
    if problems:
        for p in problems:
            typer.echo(f"  → {p['name']}")
    else:
        typer.echo("  (No linked problems yet)")

@app.command()
def patterns():
    """List all patterns and their linked problem counts (Total & Solved)."""
    pattern_data = get_analytics_by_pattern()
    if not pattern_data:
        typer.echo("No patterns found. Add one with: dsa pattern <name> --add")
        return
        
    typer.echo("┌──────────────────────────────┬────────────────┬────────────────┐")
    typer.echo("│ Pattern                      │ Total Problems │ Solved         │")
    typer.echo("├──────────────────────────────┼────────────────┼────────────────┤")
    for p in pattern_data:
        name_pad = p["pattern_name"][:28].ljust(28)
        total_pad = str(p["total_problems"]).ljust(14)
        solved_pad = str(p["solved_problems"]).ljust(14)
        typer.echo(f"│ {name_pad} │ {total_pad} │ {solved_pad} │")
    typer.echo("└──────────────────────────────┴────────────────┴────────────────┘")

if __name__ == "__main__":
    app()
