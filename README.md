# AskBetterAgent

Judge the quality of any question and hand back a cleaner, answer-ready version—plus the minimal follow-ups needed to proceed.

AskBetterAgent:

* **Classifies** the question (domain + type).
* **Scores** it (clarity, specificity, answerability, safety; 0–10).
* Lists **missing_info**, **assumptions**, and **followups** (bounded lengths).
* Generates two **rewrites** (minimal edit + ideal; each ≤ 280 chars).
* Calls a `pii_scan` tool to flag `email`, `phone`, `card-ish` (and can add `vague`, `unsafe`).
* Enforces a strict JSON shape via a Pydantic schema (`QuestionReview`) for predictable, machine-readable output.

---

## Contents

* [Architecture](#architecture)
* [Requirements](#requirements)
* [Setup (uv)](#setup-uv)
* [Configuration](#configuration)
* [Run: Command Line](#run-command-line)
* [Run: Streamlit UI](#run-streamlit-ui)
* [Examples](#examples)
* [Development Notes](#development-notes)

---

## Architecture

* **Agents SDK**: `Agent` + `Runner` to execute the agent
* **Tooling**: `@function_tool` → `pii_scan(text: str) -> list[str]`
* **Schema**: Pydantic models (`QuestionReview`, `ClassificationModel`, `ScoresModel`, `RewritesModel`)
* **Model**: defaults to `gpt-4o-mini`

---

## Requirements

* Python 3.10+
* [uv](https://docs.astral.sh/uv/) (fast Python package/dependency manager)
* A valid OpenAI API key

---

## Setup (uv)

```bash
# 1) Create a virtual environment (managed by uv)
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell

# 2) Install runtime deps
uv add openai python-dotenv pydantic streamlit

# 3) Install the Agents SDK used in code
uv add agents
```

> Tip: commit a `.gitignore` (don’t commit `.env` or `.streamlit/secrets.toml`).

---

## Configuration

### Option A — `.env` (CLI & local dev)

Create a `.env` in the repo root:

```env
OPENAI_API_KEY=sk-...
```

Loaded automatically by `python-dotenv`.

### Option B — Streamlit secrets (for the UI)

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
```

**Do not commit secrets.** Instead commit a template:

```toml
# .streamlit/secrets.example.toml
OPENAI_API_KEY = "your-key-here"
```

---

## Run: Command Line

Runs the agent against your question and prints strict JSON.

```bash
# Activate venv first if not already
source .venv/bin/activate

# Run with uv (adjust filename if different)
uv run python askbetter.py "Fix this SQL?"
```

If you omit the question, the script will prompt:

```
Enter your question:
```

---

## Run: Streamlit UI

A small UI to type a question and see results (scores, flags, rewrites).

```bash
# Activate venv first if not already
source .venv/bin/activate

# Ensure .streamlit/secrets.toml exists with OPENAI_API_KEY
uv run streamlit run streamlit_app.py
```

* Enter a question (e.g., “Can you email me at [jane.doe@acme.com](mailto:jane.doe@acme.com) to fix my Postgres query?”).
* Click **Review** to see:

  * **classification** (domain/type)
  * **scores** (0–10)
  * **lists**: missing_info / assumptions / followups
  * **flags** (tool-derived + extra)
  * **rewrites** (minimal, ideal)

---

## Examples

**Input**

```
Fix this SQL?
```

**(Truncated) Output**

```json
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
```

PII example input:

```
Can you email me at jane.doe@acme.com to fix my Postgres query?
```

→ `flags` will include `["email"]`.

---

## Development Notes

* **Schema guarantees**

  * Scores are `int` with `0 ≤ x ≤ 10`.
  * Rewrites each have `max_length=280`.
  * Lists can be capped with validators (`≤6` for `missing_info/assumptions`, `≤5` for `followups`).

* **Tool usage**

  * Instructions require: `pii_scan(text=original_question)` and copy results into `flags`.
  * (Optional) Recompute flags locally and merge for belt-and-suspenders.

* **Determinism**

  * Add `temperature=0.2` (and `seed` if supported) in your run config to reduce drift.

* **Secrets hygiene**

  * Never commit `.env` or `.streamlit/secrets.toml`.
  * Commit `.streamlit/secrets.example.toml` for teammates.

* **Using uv daily**

  ```bash
  uv add <package>             # add deps
  uv run python <file>.py      # run scripts
  uv run streamlit run streamlit_app.py
  ```

---

### .gitignore (suggested)

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
build/
dist/

# Envs
.env
.venv/
venv/

# Streamlit
.streamlit/

# OS/IDE
.DS_Store
.vscode/
.idea/
```
