AskBetterAgent

Judge the quality of any question and hand back a cleaner, answer-ready version—plus the minimal follow-ups needed to proceed.

AskBetterAgent:

Classifies the question (domain + type).

Scores it (clarity, specificity, answerability, safety; 0–10).

Lists missing_info, assumptions, and followups (bounded lengths).

Generates two rewrites (minimal edit + ideal; each ≤ 280 chars).

Calls a pii_scan tool to flag email, phone, card-ish (and can add vague, unsafe).

Enforces a strict JSON shape via a Pydantic schema (QuestionReview) for predictable, machine-readable output.

Contents

Architecture

Requirements

Setup (uv)

Configuration

Run: Command Line

Run: Streamlit UI

Examples

Development Notes

Architecture

Agents SDK: Agent + Runner to execute the agent.

Tooling: @function_tool -> pii_scan(text: str) -> list[str].

Schema: Pydantic models (QuestionReview, ClassificationModel, ScoresModel, RewritesModel) to guarantee shape, ranges, and length caps.

Models: Defaults to gpt-4o-mini.

Requirements

Python 3.10+

uv
 (fast Python package/dependency manager)

A valid OpenAI API key

Setup (uv)

From the repo root:

# (1) Create a virtual environment (managed by uv)
uv venv
source .venv/bin/activate  # on macOS/Linux
# .venv\Scripts\activate   # on Windows PowerShell

# (2) Install runtime deps
uv add openai python-dotenv pydantic streamlit

# (3) Install the Agents SDK (the one you’re using in code)
uv add agents


Tip: commit a .gitignore (don’t commit .env or .streamlit/secrets.toml).

Configuration
Option A — .env (CLI & local dev)

Create a .env in the repo root:

OPENAI_API_KEY=sk-...


The app loads it via python-dotenv.

Option B — Streamlit secrets (for the UI)

Create .streamlit/secrets.toml:

OPENAI_API_KEY = "sk-..."


Don’t commit this. Instead commit a sample:

.streamlit/secrets.example.toml

OPENAI_API_KEY = "your-key-here"

Run: Command Line

The CLI path runs the agent against the user’s question and prints strict JSON.

# Activate venv first if not already
source .venv/bin/activate

# Run with uv
uv run python askbetter.py "Fix this SQL?"
# or if your entry file is named differently, update the path accordingly


If you omit the question, the script will prompt:

Enter your question:

Run: Streamlit UI

The UI lets you type a question, run the agent, and see pretty results (scores, flags, rewrites).

# Activate venv first if not already
source .venv/bin/activate

# Ensure .streamlit/secrets.toml exists with OPENAI_API_KEY
uv run streamlit run streamlit_app.py


Enter a question (e.g., “Can you email me at jane.doe@acme.com
 to fix my Postgres query?”).

Click Review.

You’ll see:

classification (domain/type)

scores (0–10)

lists: missing_info / assumptions / followups

flags (tool-derived + extra)

rewrites (minimal, ideal)

Copy buttons are provided for the ideal rewrite (if you added them).

Examples
Example input
Fix this SQL?

Example (truncated) output
{
  "original_question": "Fix this SQL?",
  "classification": { "domain": "coding", "type": "debug" },
  "scores": { "clarity": 3, "specificity": 2, "answerability": 4, "safety": 8 },
  "missing_info": ["The actual SQL", "DB engine", "Error message", "Expected output"],
  "assumptions": ["User has basic SQL context"],
  "followups": ["Can you paste the SQL?", "Which database?", "What error do you see?"],
  "rewrites": {
    "minimal": "Can you help me fix this SQL query?",
    "ideal": "I’m using Postgres. Here’s my SQL and the error. How can I fix it to return X?"
  },
  "flags": []
}


PII example:

"Can you email me at jane.doe@acme.com to fix my Postgres query?"


→ flags will include ["email"].

Development Notes

Schema guarantees

Scores are int with 0 ≤ x ≤ 10.

Rewrites each have max_length=280.

Lists are capped in code or post-processed (add validators as needed).

Tool usage

Instructions require: pii_scan(text=original_question).

You can belt-and-suspenders by recomputing flags locally and merging.

Determinism

Later, add temperature=0.2 (and seed if supported) to reduce drift.

Secrets

Never commit .env or .streamlit/secrets.toml.

Use .streamlit/secrets.example.toml for teammates.

Using uv daily

uv add <package>            # add deps
uv run python <file>.py     # run scripts with deps resolved
uv run streamlit run streamlit_app.py
