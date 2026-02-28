# DSA Data Studio

DSA Data Studio is a local CLI tool and web dashboard designed to help you track your LeetCode problem-solving progress. It allows you to save incremental solutions, log performance metadata in a SQLite database, and get automated L4/L5 standard code reviews and optimal solutions from your LLM of choice. 

The application features an adaptive dashboard UI including **Current Focus tracking**, API cost metrics, historical submission viewing, structured **Problem Queues**, and a dedicated DSA Patterns library.


## How does the UI look
<img width="2558" height="1357" alt="image" src="https://github.com/user-attachments/assets/c6e4c9ef-f981-4e36-a57b-3cab44007e88" />
<img width="2481" height="1283" alt="image" src="https://github.com/user-attachments/assets/c346fad5-5574-48dc-bd24-63adbde8f5bd" />


---

## Quick Start

1. **Activate the Environment**
   Open your terminal in the project root and activate the Python virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. **Set your API Key**
   Copy `.env.example` to `.env` and fill in your credentials. The tool supports multiple LLM providers — set `LLM_PROVIDER` to switch between them:
   ```env
   # Choose: openai | anthropic
   LLM_PROVIDER=openai

   # OpenAI
   OPENAI_API_KEY=your-api-key-here
   OPENAI_MODEL=gpt-4o-mini
   # Set to false for reasoning models (o1, o3, codex) that don't support temperature
   OPENAI_SUPPORTS_TEMPERATURE=true

   # Anthropic (optional)
   # ANTHROPIC_API_KEY=your-api-key-here
   # ANTHROPIC_MODEL=claude-3-5-sonnet-latest
   ```

3. **Sync your Personal Data (Optional)**
   Your personal problems and database are stored in `/data`, which is ignored by Git. You can track your progress privately by turning the data folder into its own repository:
   ```bash
   cd data
   git init
   git add .
   git commit -m "initial problem tracking backup"
   # Link to a private repository on GitHub
   ```

4. **Open the Web Dashboard**
   To view your progress logs, API metrics, and LLM feedback side-by-side, start the Streamlit server:
   ```bash
   streamlit run web/app.py --server.port 8501
   ```

   *(Optional)* To access the dashboard at `http://dsa.datastudio.com:8501` instead of `localhost:8501`:
   1. Add `127.0.0.1 dsa.datastudio.com` to your `/etc/hosts` file (macOS/Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows).
   2. Edit your `.streamlit/config.toml` (create it if it doesn't exist) to allow CORS:
      ```toml
      [server]
      enableCORS = false
      ```

5. **Set your Current Focus Pattern!**
   - Open the **Dashboard**.
   - Navigate to the **🧩 Patterns** Tab.
   - Expand any pattern bucket you want to practice and click the `🎯 Set as Focus` button.
   - Head back to the **🏠 Dashboard** Tab to track your progress and avoid stale study habits!

---

## 🛠️ CLI Commands

You can run these commands from anywhere inside the project directory using the provided `./dsa` executable script.

### 1. Initialize DB (Run Once)
Initializes the SQLite database and creates the necessary directories. *(This is usually done for you upon first setup).*
```bash
./dsa init
```

### 2. Create a New Problem
Creates a new directory for the problem, stubs out a `problem.md` file for you to paste the description into, and creates a record in the database.
```bash
./dsa new "Problem Name" --link "https://leetcode.com/problems/..."
```

### 3. Submit a Solution
Copies your local Java/Python solution into the problem's tracking folder, timestamps it, and logs it to the database.
```bash
./dsa submit "Problem Name" path/to/your/Solution.java
```

### 4. Get LLM Feedback
Reads your latest submitted solution and the problem description, sends it to your configured LLM provider, and saves the generated Markdown feedback (Time/Space complexity, bugs, optimal approach).
```bash
./dsa review "Problem Name"
```

### 5. Log Metadata
Opens an interactive prompt to retroactively log metadata for the problem (Topic, Pattern, Time to Optimal, Bugs, Aha! moments). This data populates the Streamlit dashboard.
```bash
./dsa log "Problem Name"
```

### 6. Delete a Problem
Completely removes the problem directory from your disk and safely deletes all associated records (solutions, feedbacks) from the database.
```bash
./dsa delete "Problem Name"

# Skip the confirmation prompt
./dsa delete "Problem Name" --force
```

### 7. Manage Patterns
View, add, or link reusable DSA patterns to your problems to build a repository of code templates and recognition notes.
```bash
# Add a new pattern interactively
./dsa pattern "KMP" --add

# View a pattern's details and linked problems
./dsa pattern "KMP"

# Link an existing problem to a pattern
./dsa pattern "KMP" --link "Find Index of First Occurrence"

# List all patterns with their Total and Solved problem counts
./dsa patterns
```

---

## Project Worktree

```text
dsa-data-studio/
├── dsa                        # The main executable bash script for the CLI
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (see .env.example)
│
├── data/                      # 🛑 IGNORED BY GIT: Your private data
│   ├── dsa_data.db            # SQLite Database storing all your progress metadata
│   └── problems/              # Where all your generated problem files live
│       └── problem-name/
│           ├── problem.md         # The problem statement
│           ├── solutions/         # Timestamped copies of your submitted code
│           │   ├── 20260221_120000_solution.java
│           │   └── 20260221_123000_solution.java
│           └── feedback/          # Markdown files generated by LLM reviews
│               └── 20260221_123005_review.md
│
├── scripts/                   # Core backend logic
│   ├── cli.py                 # Typer configuration and CLI routing
│   ├── db.py                  # SQLite schema definitions and query wrappers
│   ├── utils.py               # Shared utility functions (e.g. sanitize_name)
│   ├── seed_curated_list.py   # Populates the DB with the Master DP Bucket list
│   └── llm/                   # Provider-agnostic LLM integration
│       ├── base.py            # Abstract LLMProvider interface
│       ├── factory.py         # Reads LLM_PROVIDER env var and returns the right provider
│       ├── openai_provider.py # OpenAI implementation
│       └── anthropic_provider.py # Anthropic implementation
│
└── web/                       # The local web application
    └── app.py                 # Streamlit dashboard script
```
