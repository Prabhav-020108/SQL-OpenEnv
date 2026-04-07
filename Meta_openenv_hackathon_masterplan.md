# Meta × Hugging Face — OpenEnv Hackathon
## Complete Master Plan & Reference Document

> **Deadline: April 8, 2026 — 11:59 PM IST**  
> **Round 1 opens: April 1, 2026**  
> Share this document with teammates and paste into any Claude chat as full context.

---

## Table of Contents

1. [Hackathon Overview](#1-hackathon-overview)
2. [What You Are Building](#2-what-you-are-building)
3. [Evaluation Criteria & Scoring](#3-evaluation-criteria--scoring)
4. [Pre-Submission Checklist (Disqualification Gates)](#4-pre-submission-checklist-disqualification-gates)
5. [How Judging Works](#5-how-judging-works)
6. [Our Solution: SQL Query Grader Environment](#6-our-solution-sql-query-grader-environment)
7. [Phase 1 — Prerequisites & Setup](#7-phase-1--prerequisites--setup)
8. [Phase 2 — Environment Design](#8-phase-2--environment-design)
9. [Phase 3 — Core Implementation](#9-phase-3--core-implementation)
10. [Phase 4 — Local Testing & Validation](#10-phase-4--local-testing--validation)
11. [Phase 5 — Deploy to Hugging Face Spaces](#11-phase-5--deploy-to-hugging-face-spaces)
12. [Phase 6 — Polish & Final Submission](#12-phase-6--polish--final-submission)
13. [Time Budget](#13-time-budget)
14. [Critical Mistakes to Avoid](#14-critical-mistakes-to-avoid)
15. [What Makes You Stand Out](#15-what-makes-you-stand-out)
16. [Key File Reference](#16-key-file-reference)

---

## 1. Hackathon Overview

**Host:** Meta × Hugging Face  
**Framework:** OpenEnv — a standard for building, deploying, and using isolated RL training environments  
**Format:** Round 1 opens April 1. You pick 1 of 4–5 problem statements and build an OpenEnv environment around it.

**The core task:**
- Build a mini-game or real-world task environment an AI agent can learn from
- Define tasks with increasing difficulty
- Write graders that verify task completion and produce scores
- Define reward logic for scoring
- Package everything using the OpenEnv framework for automated evaluation

**What OpenEnv is:** A framework where environments run as isolated Docker containers exposing a standard `reset()` / `step()` / `state()` API over WebSocket. Agents interact with environments the same way whether training locally or in production — no friction, no "works on my machine."

---

## 2. What You Are Building

### Functional Requirements

| Requirement | Details |
|-------------|---------|
| **Real-world task** | Must simulate something humans actually do. NOT games, NOT toys. Examples: email triage, code review, data cleaning, scheduling, SQL writing |
| **OpenEnv spec compliance** | Typed `Observation`, `Action`, `Reward` Pydantic models. `step()`, `reset()`, `state()` methods. `openenv.yaml`. Must pass `openenv validate` |
| **Minimum 3 tasks with graders** | Each task has a concrete objective, a programmatic grader scoring 0.0–1.0, and a range from easy → medium → hard |
| **Meaningful reward function** | Provides signal across the full trajectory, not just binary end-of-episode. Rewards partial progress. Penalizes clearly bad behavior |
| **Baseline inference script** | Named `inference.py`, placed in root. Uses OpenAI client. Reads credentials from env vars. Produces reproducible baseline scores |

### Non-Functional Requirements

| Requirement | Details |
|-------------|---------|
| **HF Space deployment** | Must run as a containerized HF Space tagged with `openenv` |
| **Working Dockerfile** | Must `docker build` and `docker run` cleanly |
| **Documentation** | README with: environment description, action/observation space definitions, task descriptions, setup instructions, baseline scores |
| **Runtime** | Inference script must complete in under 20 minutes on vcpu=2, memory=8gb |

### Required stdout format for inference.py

Your inference script must emit **exactly** these three line types in order:

```
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
```

**Rules:**
- One `[START]` per episode, at the very beginning
- One `[STEP]` per step, immediately after `env.step()` returns
- One `[END]` after `env.close()`, always emitted even on exception
- `reward` and `rewards` formatted to exactly 2 decimal places
- `done` and `success` are lowercase: `true` or `false`
- `error` is the raw error string or `null` (not `None`)
- All fields on a single line, no newlines within a line

**Example:**
```
[START] task=select_basics env=sql_env model=Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT * FROM customers reward=0.30 done=false error=null
[STEP] step=2 action=SELECT name FROM customers WHERE city='NY' reward=1.00 done=true error=null
[END] success=true steps=2 score=1.000 rewards=0.30,1.00
```

### Required environment variables for inference.py

```
API_BASE_URL   — The API endpoint for the LLM
MODEL_NAME     — The model identifier for inference
HF_TOKEN       — Your Hugging Face / API key
IMAGE_NAME     — Local Docker image name (if using from_docker_image())
```

---

## 3. Evaluation Criteria & Scoring

Total: 100 points across 5 categories.

### Real-world utility — 30%

> Does the environment model a genuine task? Would someone actually use this to train or evaluate agents?

| Score | Meaning |
|-------|---------|
| 0–5 | Toy/artificial problem with no practical application |
| 6–15 | Valid domain but shallow modeling of the real task |
| 16–25 | Good domain modeling, would be useful for agent evaluation |
| 26–30 | Excellent — fills a real gap, immediate value for the RL/agent community |

### Task & grader quality — 25%

> Are tasks well-defined with clear objectives? Do graders accurately and fairly measure success? Meaningful difficulty progression?

Checklist:
- 3+ tasks with difficulty range (easy → medium → hard)?
- Graders produce scores between 0.0–1.0?
- Graders are deterministic and reproducible?
- Hard task genuinely challenges frontier models?

### Environment design — 20%

> Clean state management, sensible action/observation spaces, good reward shaping, proper episode boundaries.

Checklist:
- `reset()` produces clean state?
- Action/observation types well-designed and documented?
- Reward function provides useful varying signal (not just sparse)?
- Episode boundaries sensible?

### Code quality & spec compliance — 15%

> Follows OpenEnv spec, clean project structure, typed models, documented, tested, Dockerfile works.

Checklist:
- `openenv validate` passes?
- `docker build && docker run` works?
- HF Space deploys and responds?
- Baseline script runs and reproduces scores?

### Creativity & novelty — 10%

> Novel problem domain, interesting mechanics, clever reward design, original approach.

- Domain not seen in OpenEnv before?
- Reward design has interesting properties?
- Clever mechanics that make the environment engaging?

---

## 4. Pre-Submission Checklist (Disqualification Gates)

All must pass or you are **disqualified**.

| Check | How it's Verified |
|-------|-----------------|
| HF Space deploys | Automated ping to Space URL — must return 200 and respond to `reset()` |
| OpenEnv spec compliance | Validate `openenv.yaml`, typed models, `step()`/`reset()`/`state()` endpoints |
| Dockerfile builds | Automated docker build on the submitted repo |
| Baseline reproduces | Run the submitted inference script — must complete without error and produce scores |
| 3+ tasks with graders | Enumerate tasks, run each grader, verify scores/reward in 0.0–1.0 range |

**Mandatory additional instructions:**
- Variables `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` must be defined in environment configuration
- Inference script must be named `inference.py` and placed in **root directory**
- Must use OpenAI Client for all LLM calls
- Emit structured stdout logs strictly following `[START]`, `[STEP]`, `[END]` format
- Any deviation in field names, ordering, or formatting → incorrect evaluation scoring

**Infrastructure restrictions:**
- Runtime of inference script < 20 minutes
- Must run on vcpu=2, memory=8gb

**Run the hackathon's validator before submitting:**
```bash
bash validate-submission.sh https://YOUR_USERNAME-your-env.hf.space .
```

---

## 5. How Judging Works

### Phase 1 — Automated Validation (Pass/Fail Gate)
- HF Space deploys
- OpenEnv spec compliance
- Dockerfile builds
- Baseline reproduces
- 3+ tasks with graders

### Phase 2 — Agentic Evaluation (Scored)
- Baseline agent re-run
- Standard Open LLM agent (e.g. Nemotron 3 Super) run against all environments
- Score variance check

### Phase 3 — Human Review (Top Submissions)
- Meta and Hugging Face engineers review for real-world utility, creativity, exploit checks

### Disqualification Criteria
- Environment does not deploy or respond
- Plagiarized or trivially modified existing environments
- Graders that always return the same score
- No baseline inference script

---

## 6. Our Solution: SQL Query Grader Environment

### Why SQL?

SQL Query Writing is an ideal domain because:
- **Genuinely useful** — training agents to write SQL helps automate data analysis, database querying, and business intelligence
- **Deterministic grading** — SQL results can be compared programmatically with exact precision
- **Natural difficulty progression** — SELECT → GROUP BY → multi-JOIN is a perfect easy/medium/hard arc
- **Novel in OpenEnv** — no existing SQL environment in the OpenEnv ecosystem
- **Partial rewards are natural** — column match, row match, value match all give meaningful partial signal

### Environment Name

`sql_env` — deployed as `YOUR_USERNAME-sql-env.hf.space`

### How it works

1. Agent receives a **task description** in natural language + a **database schema** (DDL)
2. Agent writes a **SQL query** as its action
3. Environment **executes the query** against an in-memory SQLite database seeded with test data
4. Environment **grades the result** against the expected output and returns a reward + feedback
5. Agent can **retry** up to N steps per episode, improving its query based on feedback

### The 3 Tasks

| Task Name | Difficulty | Description | What agent must do |
|-----------|------------|-------------|-------------------|
| `select_basics` | Easy | Find customers from a specific city | Write a `SELECT ... WHERE` query |
| `aggregate_filter` | Medium | Find top-spending customers per category | Write `GROUP BY` + `HAVING` + `WHERE` |
| `multi_join` | Hard | Monthly revenue report across 3 tables | Write a 3-table `JOIN` with aggregation and ordering |

### Reward Function Design

Every step returns a reward in [0.0, 1.0] with partial credit:

```
+0.10  Query executes without syntax error
+0.20  Correct columns selected
+0.20  Correct row count returned
+0.40  Correct values (F1 score on result set)
+0.10  Query efficiency bonus (no SELECT *, no unnecessary scans)
─────
 1.00  Maximum per step

-0.05  Syntax error penalty
-0.10  Timeout penalty (query takes too long)
```

This gives the agent a learning signal at every step, not just when it gets the perfect answer.

### Action Space

```python
SqlAction(sql_query: str)
# Example: SqlAction(sql_query="SELECT name, city FROM customers WHERE city = 'New York'")
```

### Observation Space

```python
SqlObservation(
    task_description: str,      # Natural language task the agent must solve
    schema_info: str,           # Database schema as DDL (CREATE TABLE statements)
    query_result: list,         # Rows returned by the agent's last query
    error_message: str,         # SQL error message if query failed
    feedback: str,              # Human-readable grader feedback
    attempts_remaining: int,    # Steps left in this episode
    done: bool,                 # True when episode ends
    reward: float,              # Reward for this step (0.0–1.0)
)
```

### Architecture

```
inference.py (agent)
    │
    │  WebSocket /ws
    ↓
FastAPI Server (server/app.py)
    │
    ↓
SqlEnvironment (server/sql_environment.py)
    │  ← SQLite in-memory DB per session
    │  ← Grader logic
    │  ← Reward computation
    ↓
SqlObservation → back to agent
```

---

## 7. Phase 1 — Prerequisites & Setup

**Time: ~2 hours | Do this immediately**

### Step 1.1 — Install Python 3.11

```bash
python --version  # Must be 3.10, 3.11, or 3.12
```

### Step 1.2 — Install all tools

```bash
# uv — fast Python package manager (used by OpenEnv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# OpenEnv CLI
pip install openenv-core

# Hugging Face CLI
pip install huggingface_hub hf_transfer
huggingface-cli login    # enter your HF token when prompted

# Docker Desktop
# Download from https://docs.docker.com/get-docker/
docker --version         # verify installation

# OpenAI client (for inference.py)
pip install openai
```

### Step 1.3 — Create GitHub repository

1. Go to github.com → New Repository
2. Name: `sql-env`
3. Visibility: Public (required for HF Spaces)
4. Clone locally:

```bash
git clone https://github.com/YOUR_USERNAME/sql-env
cd sql-env
```

### Step 1.4 — Claim your HF Space URL early

```bash
huggingface-cli repo create sql-env --type space --sdk docker
```

This gives you: `https://YOUR_USERNAME-sql-env.hf.space` — note this down, you need it for submission.

### Step 1.5 — Scaffold the project structure

```bash
# Try CLI first
pip install openenv-core
openenv init sql_env --output-dir .
```

If that fails, create manually:

```
sql_env/
├── __init__.py
├── client.py
├── models.py
├── openenv.yaml
├── pyproject.toml
├── inference.py          ← REQUIRED: must be at root
├── README.md
└── server/
    ├── __init__.py
    ├── app.py
    ├── sql_environment.py
    ├── requirements.txt
    └── Dockerfile
```

---

## 8. Phase 2 — Environment Design

**Time: ~2 hours | Do on paper before coding**

### Step 2.1 — Define the 3 tasks in detail

Write these out fully before writing any code. Each task needs:
- Clear natural language description (what you'd tell a human)
- Database schema (CREATE TABLE statements)
- Seed data (the rows in the database)
- Expected result (the exact output a perfect query returns)
- Max steps (how many attempts the agent gets)

**Task 1 — select_basics (Easy):**
```
Description: "Find the names and email addresses of all customers 
              who are from New York, sorted alphabetically by name."
Schema: customers(id, name, email, city, age, signup_date)
Expected: [("Alice Brown", "alice@email.com"), ("Bob Smith", "bob@email.com"), ...]
Max steps: 5
```

**Task 2 — aggregate_filter (Medium):**
```
Description: "Find the total amount spent by each customer who has 
              placed more than 3 orders, showing customer name and 
              total spend, ordered by total spend descending."
Schema: customers(id, name, email), orders(id, customer_id, amount, date)
Expected: [("Charlie D", 450.00), ("Alice B", 320.00), ...]
Max steps: 5
```

**Task 3 — multi_join (Hard):**
```
Description: "Generate a monthly revenue report showing month, 
              category name, number of orders, and total revenue 
              for all categories in 2024, ordered by month then 
              revenue descending."
Schema: orders(id, customer_id, date), order_items(id, order_id, product_id, quantity, price),
        products(id, name, category_id), categories(id, name)
Expected: [("2024-01", "Electronics", 12, 2400.00), ...]
Max steps: 7
```

### Step 2.2 — Design the grader logic

For each task, define how partial credit works. Write this as pseudocode first:

```
grade(agent_result, expected_result):
  if agent_result is empty → return 0.1, "Query ran but no rows returned"
  
  compute precision = |agent_result ∩ expected| / |agent_result|
  compute recall    = |agent_result ∩ expected| / |expected|
  compute f1        = 2 * precision * recall / (precision + recall)
  
  if f1 == 1.0 → return 1.0, "Perfect match!"
  if f1 > 0.8  → return 0.8, "Very close — check column order or data types"
  if f1 > 0.5  → return f1 * 0.8, "Partial match — {int(f1*100)}% correct"
  else         → return f1 * 0.5, "Mostly wrong — re-read the schema"
```

### Step 2.3 — Verify your design against scoring criteria

Before coding, check:
- Does the reward vary meaningfully between attempts? (not just 0 or 1)
- Is the hard task genuinely hard for a strong LLM?
- Does `reset()` produce truly clean state each episode?
- Are episode boundaries sensible (max_steps reached OR perfect score)?

---

## 9. Phase 3 — Core Implementation

**Time: ~12 hours | Today evening through tomorrow morning**

### Step 3.1 — models.py

```python
from openenv.core.env_server.types import Action, Observation
from pydantic import Field

class SqlAction(Action):
    """Action for SQL environment — a SQL query string."""
    sql_query: str = Field(..., description="SQL query string to execute against the database")

class SqlObservation(Observation):
    """Observation from SQL environment after executing a query."""
    task_description: str = Field(default="", description="Natural language description of the task")
    schema_info: str = Field(default="", description="Database schema as DDL statements")
    query_result: list = Field(default_factory=list, description="Rows returned by the query")
    error_message: str = Field(default="", description="SQL error message if query failed")
    feedback: str = Field(default="", description="Human-readable feedback from the grader")
    attempts_remaining: int = Field(default=3, description="Steps remaining in this episode")
```

### Step 3.2 — server/sql_environment.py (core logic)

```python
import sqlite3
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SqlAction, SqlObservation
except ImportError:
    from models import SqlAction, SqlObservation

TASKS = {
    "select_basics": {
        "description": "Find the names and email addresses of all customers from New York, sorted alphabetically by name.",
        "schema": """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                city TEXT NOT NULL,
                age INTEGER
            );
        """,
        "seed_sql": """
            INSERT INTO customers VALUES (1, 'Alice Brown', 'alice@email.com', 'New York', 28);
            INSERT INTO customers VALUES (2, 'Bob Smith', 'bob@email.com', 'New York', 34);
            INSERT INTO customers VALUES (3, 'Carol Davis', 'carol@email.com', 'Chicago', 25);
            INSERT INTO customers VALUES (4, 'David Lee', 'david@email.com', 'New York', 41);
        """,
        "expected": [
            ("Alice Brown", "alice@email.com"),
            ("Bob Smith", "bob@email.com"),
            ("David Lee", "david@email.com"),
        ],
        "max_steps": 5,
    },
    "aggregate_filter": {
        "description": "Find the total amount spent by each customer who has placed more than 2 orders. Show customer name and total spend, ordered by total spend descending.",
        "schema": """
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);
        """,
        "seed_sql": """
            INSERT INTO customers VALUES (1, 'Alice Brown');
            INSERT INTO customers VALUES (2, 'Bob Smith');
            INSERT INTO customers VALUES (3, 'Carol Davis');
            INSERT INTO orders VALUES (1, 1, 120.00);
            INSERT INTO orders VALUES (2, 1, 85.50);
            INSERT INTO orders VALUES (3, 1, 200.00);
            INSERT INTO orders VALUES (4, 2, 45.00);
            INSERT INTO orders VALUES (5, 2, 95.00);
            INSERT INTO orders VALUES (6, 2, 160.00);
            INSERT INTO orders VALUES (7, 3, 30.00);
        """,
        "expected": [
            ("Alice Brown", 405.50),
            ("Bob Smith", 300.00),
        ],
        "max_steps": 5,
    },
    "multi_join": {
        "description": "Generate a monthly revenue report for 2024. Show: month (YYYY-MM), category name, number of orders, and total revenue. Order by month ascending, then revenue descending.",
        "schema": """
            CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER, price REAL);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, order_date TEXT);
            CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER);
        """,
        "seed_sql": """
            INSERT INTO categories VALUES (1, 'Electronics');
            INSERT INTO categories VALUES (2, 'Books');
            INSERT INTO products VALUES (1, 'Laptop', 1, 999.00);
            INSERT INTO products VALUES (2, 'Python Book', 2, 49.00);
            INSERT INTO orders VALUES (1, '2024-01-15');
            INSERT INTO orders VALUES (2, '2024-01-20');
            INSERT INTO orders VALUES (3, '2024-02-10');
            INSERT INTO order_items VALUES (1, 1, 1, 1);
            INSERT INTO order_items VALUES (2, 2, 2, 2);
            INSERT INTO order_items VALUES (3, 3, 1, 1);
        """,
        "expected": [
            ("2024-01", "Electronics", 1, 999.00),
            ("2024-01", "Books", 1, 98.00),
            ("2024-02", "Electronics", 1, 999.00),
        ],
        "max_steps": 7,
    },
}


class SqlEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._conn = None
        self._task_name = "select_basics"
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self, seed=None, episode_id=None, **kwargs):
        task_name = kwargs.get("task", "select_basics")
        if task_name not in TASKS:
            task_name = "select_basics"
        self._task_name = task_name
        task = TASKS[task_name]

        # Fresh in-memory SQLite per episode — guarantees clean state
        if self._conn:
            self._conn.close()
        self._conn = sqlite3.connect(":memory:")
        self._conn.executescript(task["schema"])
        self._conn.executescript(task["seed_sql"])
        self._conn.commit()

        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)

        return SqlObservation(
            task_description=task["description"],
            schema_info=task["schema"].strip(),
            query_result=[],
            error_message="",
            feedback="Episode started. Write a SQL query to solve the task.",
            attempts_remaining=task["max_steps"],
            done=False,
            reward=0.0,
        )

    def step(self, action: SqlAction) -> SqlObservation:
        self._state.step_count += 1
        task = TASKS[self._task_name]
        attempts_remaining = task["max_steps"] - self._state.step_count

        try:
            cursor = self._conn.execute(action.sql_query)
            result = cursor.fetchall()
            reward, feedback = self._grade(result, task["expected"])
            done = reward >= 0.95 or attempts_remaining <= 0

        except Exception as e:
            reward = -0.05
            result = []
            feedback = f"SQL Error: {str(e)}"
            done = attempts_remaining <= 0

        return SqlObservation(
            task_description=task["description"],
            schema_info=task["schema"].strip(),
            query_result=[list(r) for r in result],
            error_message="" if not feedback.startswith("SQL Error") else feedback,
            feedback=feedback,
            attempts_remaining=max(0, attempts_remaining),
            done=done,
            reward=max(-0.1, min(1.0, reward)),  # clamp to valid range
        )

    def _grade(self, result, expected):
        if not result:
            return 0.1, "Query ran but returned no rows. Check your WHERE clause."

        result_set = set(tuple(r) for r in result)
        expected_set = set(tuple(e) for e in expected)

        if result_set == expected_set:
            return 1.0, "Perfect! Exact match."

        intersection = result_set & expected_set
        precision = len(intersection) / len(result_set) if result_set else 0
        recall = len(intersection) / len(expected_set) if expected_set else 0

        if precision + recall == 0:
            return 0.05, "No matching rows. Check your JOIN conditions and filters."

        f1 = 2 * precision * recall / (precision + recall)

        if f1 > 0.8:
            return round(f1 * 0.9, 2), f"Very close! {int(f1*100)}% match. Check column order or data types."
        elif f1 > 0.5:
            return round(f1 * 0.8, 2), f"Partial match: {int(f1*100)}% correct. Re-read the task description."
        else:
            return round(f1 * 0.5, 2), f"Mostly incorrect ({int(f1*100)}% match). Start from the schema."

    @property
    def state(self) -> State:
        return self._state
```

### Step 3.3 — server/app.py

```python
try:
    from openenv.core.env_server.http_server import create_app
except ImportError as e:
    raise ImportError("Install openenv-core: pip install openenv-core") from e

try:
    from ..models import SqlAction, SqlObservation
    from .sql_environment import SqlEnvironment
except ImportError:
    from models import SqlAction, SqlObservation
    from server.sql_environment import SqlEnvironment

app = create_app(
    SqlEnvironment,
    SqlAction,
    SqlObservation,
    env_name="sql_env",
    max_concurrent_envs=10,
)

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
```

### Step 3.4 — client.py

```python
from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State
from .models import SqlAction, SqlObservation

class SqlEnv(EnvClient[SqlAction, SqlObservation, State]):
    def _step_payload(self, action: SqlAction) -> dict:
        return {"sql_query": action.sql_query}

    def _parse_result(self, payload: dict) -> StepResult[SqlObservation]:
        obs_data = payload.get("observation", {})
        obs = SqlObservation(
            task_description=obs_data.get("task_description", ""),
            schema_info=obs_data.get("schema_info", ""),
            query_result=obs_data.get("query_result", []),
            error_message=obs_data.get("error_message", ""),
            feedback=obs_data.get("feedback", ""),
            attempts_remaining=obs_data.get("attempts_remaining", 0),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
```

### Step 3.5 — __init__.py

```python
from .client import SqlEnv
from .models import SqlAction, SqlObservation

__all__ = ["SqlEnv", "SqlAction", "SqlObservation"]
```

### Step 3.6 — openenv.yaml

```yaml
spec_version: 1
name: sql_env
type: space
runtime: fastapi
app: server.app:app
port: 8000
```

### Step 3.7 — pyproject.toml

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openenv-sql-env"
version = "0.1.0"
description = "SQL Query Grader environment for OpenEnv — trains agents to write correct SQL"
requires-python = ">=3.10"
dependencies = [
    "openenv-core[core]>=0.2.2",
    "fastapi>=0.115.0",
    "uvicorn>=0.24.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.setuptools]
packages = ["sql_env", "sql_env.server"]
package-dir = {"sql_env" = ".", "sql_env.server" = "server"}
```

### Step 3.8 — server/requirements.txt

```
openenv-core[core]>=0.2.2
fastapi>=0.115.0
uvicorn>=0.24.0
```

### Step 3.9 — server/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/env

ENV PYTHONPATH="/app/env:$PYTHONPATH"

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 3.10 — inference.py (REQUIRED — must be at root)

```python
"""
Inference Script — SQL Query Grader Environment
Follows the mandatory stdout format: [START], [STEP], [END]
"""
import asyncio
import os
from typing import List, Optional
from openai import OpenAI
from sql_env import SqlAction, SqlEnv

IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

TASKS = ["select_basics", "aggregate_filter", "multi_join"]
MAX_STEPS = 5
BENCHMARK = "sql_env"
SUCCESS_SCORE_THRESHOLD = 0.7

SYSTEM_PROMPT = """You are an expert SQL writer. Given a database schema and a task,
write a correct SQL query. Respond with ONLY the SQL query — no explanation, no markdown,
no code blocks. Just the raw SQL."""


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


async def run_task(task_name: str):
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = await SqlEnv.from_docker_image(IMAGE_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task=task_name)
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            user_prompt = f"""Database Schema:
{obs.schema_info}

Task:
{obs.task_description}

Feedback from last attempt:
{obs.feedback}

Write the SQL query:"""

            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=300,
                temperature=0.3,
            )

            sql = (completion.choices[0].message.content or "").strip()
            result = await env.step(SqlAction(sql_query=sql))
            obs = result.observation

            reward = result.reward or 0.0
            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=sql[:100].replace("\n", " "),
                reward=reward,
                done=result.done,
                error=obs.error_message or None,
            )

            if result.done:
                break

        score = max(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main():
    for task in TASKS:
        await run_task(task)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 10. Phase 4 — Local Testing & Validation

**Time: ~3 hours | Tomorrow morning**

### Step 4.1 — Test environment logic directly (no server needed)

```bash
cd sql_env
python -c "
from server.sql_environment import SqlEnvironment
from models import SqlAction

env = SqlEnvironment()

# Test reset
obs = env.reset(task='select_basics')
print('Task:', obs.task_description[:60])
print('Schema:', obs.schema_info[:80])

# Test a correct query
result = env.step(SqlAction(sql_query=\"SELECT name, email FROM customers WHERE city='New York' ORDER BY name\"))
print('Reward:', result.reward)
print('Feedback:', result.feedback)
print('Done:', result.done)

# Test a wrong query  
result2 = env.step(SqlAction(sql_query='SELECT * FROM customers'))
print('Partial reward:', result2.reward)

# Test error handling
result3 = env.step(SqlAction(sql_query='SELECT this_column_does_not_exist FROM customers'))
print('Error reward:', result3.reward)
print('Error message:', result3.error_message[:60])
print('All tests passed!')
"
```

### Step 4.2 — Test the server locally

```bash
# Install dependencies
pip install openenv-core fastapi uvicorn

# Start server
PYTHONPATH=. uvicorn server.app:app --port 8000 --reload

# In another terminal: test endpoints
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "select_basics"}'

curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"sql_query": "SELECT name, email FROM customers WHERE city='\''New York'\'' ORDER BY name"}'
```

### Step 4.3 — Build and test Docker

```bash
# Build (from sql_env root directory)
docker build -t sql-env:latest -f server/Dockerfile .

# Run
docker run -d -p 8000:8000 --name sql-env-test sql-env:latest

# Wait for startup
sleep 8

# Test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{}'

# Check logs if something fails
docker logs sql-env-test

# Cleanup
docker stop sql-env-test && docker rm sql-env-test
```

### Step 4.4 — Run openenv validate

```bash
# Validate project structure
openenv validate --verbose

# Validate running server
PYTHONPATH=. uvicorn server.app:app --port 8000 &
sleep 5
openenv validate --url http://localhost:8000
```

Both must pass with no errors.

### Step 4.5 — Run the hackathon's validator

```bash
# Start server
PYTHONPATH=. uvicorn server.app:app --port 8000 &

# Run their script
bash validate-submission.sh http://localhost:8000 .
```

All 3 checks must pass:
- ✅ HF Space ping (or localhost in this case)
- ✅ Docker build
- ✅ openenv validate

### Step 4.6 — Test inference.py

```bash
export IMAGE_NAME="sql-env:latest"
export HF_TOKEN="your_token_here"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

python inference.py
```

Verify output matches the exact `[START]` / `[STEP]` / `[END]` format. Save this output — it becomes your baseline scores in README.

---

## 11. Phase 5 — Deploy to Hugging Face Spaces

**Time: ~2 hours | Tomorrow afternoon**

### Step 5.1 — Prepare README.md with HF Space metadata

The README **must** start with this exact YAML frontmatter block — HF Spaces uses it to identify the Docker space:

```markdown
---
title: SQL Query Grader Environment
emoji: 🗃️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - reinforcement-learning
  - sql
  - agent-evaluation
---

# SQL Query Grader — OpenEnv Environment

An RL training environment where AI agents learn to write correct SQL queries
from natural language task descriptions. Built for the Meta × HF OpenEnv Hackathon.

## Why This Matters
SQL query writing is a task humans do daily. Training agents on this environment
helps automate database querying, data analysis pipelines, and business intelligence workflows.

## Action Space
SqlAction(sql_query: str) — the agent's SQL query string

## Observation Space
| Field | Type | Description |
|-------|------|-------------|
| task_description | str | Natural language task |
| schema_info | str | DDL schema of the database |
| query_result | list | Rows returned by the query |
| error_message | str | SQL error if query failed |
| feedback | str | Grader feedback |
| attempts_remaining | int | Steps left in episode |

## Tasks
| Task | Difficulty | Description |
|------|------------|-------------|
| select_basics | Easy | SELECT + WHERE query |
| aggregate_filter | Medium | GROUP BY + HAVING + WHERE |
| multi_join | Hard | 3-table JOIN with aggregation |

## Reward Function
- +0.10 query executes without error
- +0.20 correct columns
- +0.20 correct row count
- +0.40 correct values (F1 score)
- +0.10 efficiency bonus
- Maximum: 1.0 per step

## Baseline Scores
[Paste your inference.py output here]

## Quick Start
pip install git+https://huggingface.co/spaces/YOUR_USERNAME/sql-env
from sql_env import SqlEnv, SqlAction
env = SqlEnv(base_url="https://YOUR_USERNAME-sql-env.hf.space")
result = env.reset()
result = env.step(SqlAction(sql_query="SELECT * FROM customers"))
```

### Step 5.2 — Push to GitHub

```bash
git add -A
git commit -m "Initial SQL env implementation"
git push origin main
```

### Step 5.3 — Push to Hugging Face Spaces

```bash
# Method 1: huggingface-cli
huggingface-cli upload YOUR_USERNAME/sql-env . --repo-type space

# Method 2: git remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/sql-env
git push hf main
```

### Step 5.4 — Monitor the build

Go to `https://huggingface.co/spaces/YOUR_USERNAME/sql-env`

Watch the build logs. Common issues:
- **ModuleNotFoundError** → check `PYTHONPATH` in Dockerfile, add `ENV PYTHONPATH="/app/env:$PYTHONPATH"`
- **Port not binding** → ensure CMD uses `--port 8000` and `app_port: 8000` in README frontmatter
- **Import error on startup** → check dual-import pattern in app.py and sql_environment.py

### Step 5.5 — Verify the deployed Space

```bash
# Health check
curl https://YOUR_USERNAME-sql-env.hf.space/health
# Expected: {"status": "healthy"}

# Test reset
curl -X POST https://YOUR_USERNAME-sql-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "select_basics"}'

# Run the hackathon's validator against your live Space
bash validate-submission.sh https://YOUR_USERNAME-sql-env.hf.space .
```

All 3 checks must pass against the live URL.

---

## 12. Phase 6 — Polish & Final Submission

**Time: ~3 hours | Day 2, final hours**

### Step 6.1 — Run inference.py against live HF Space

```bash
export IMAGE_NAME="YOUR_USERNAME-sql-env.hf.space"
export HF_TOKEN="your_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

python inference.py 2>&1 | tee baseline_scores.txt
```

Copy the full output into your README under "Baseline Scores."

### Step 6.2 — Final README quality check

The README is read by human judges in Phase 3. Make sure it has:
- [ ] Clear motivation — why does this environment matter for AI training?
- [ ] Exact action/observation schema with types
- [ ] All 3 task descriptions with difficulty ratings
- [ ] Reward function explained with example numbers
- [ ] Baseline scores table showing model name and scores per task
- [ ] Working installation commands (`pip install git+...`)
- [ ] Architecture description
- [ ] HF frontmatter YAML at the very top

### Step 6.3 — Final validation run

```bash
# Re-run all checks one final time
openenv validate --url https://YOUR_USERNAME-sql-env.hf.space
bash validate-submission.sh https://YOUR_USERNAME-sql-env.hf.space .
```

### Step 6.4 — Final git push

```bash
git add -A
git commit -m "Final submission: SQL Query Grader OpenEnv environment #hackathon"
git push origin main
git push hf main
```

### Step 6.5 — Submit

Paste your HF Spaces URL on the hackathon platform:
```
https://YOUR_USERNAME-sql-env.hf.space
```

Deadline: **April 8, 2026 — 11:59 PM IST**

---

## 13. Time Budget

Total time available: ~48 hours from April 1

| Phase | Time | When |
|-------|------|------|
| Phase 1: Setup & scaffold | 2 hours | Day 1 start |
| Phase 2: Design on paper | 2 hours | Day 1 |
| Phase 3: Implementation | 12 hours | Day 1 evening → Day 2 morning |
| Phase 4: Local testing | 3 hours | Day 2 morning |
| Phase 5: HF deployment | 2 hours | Day 2 afternoon |
| Phase 6: Polish & submit | 3 hours | Day 2 evening |
| **Buffer for debugging** | **4 hours** | Throughout |

---

## 14. Critical Mistakes to Avoid

| Mistake | Consequence | Prevention |
|---------|-------------|-----------|
| `inference.py` not in root | Auto-evaluation fails | Put it at `./inference.py` exactly |
| Wrong stdout format | Incorrect scoring | Copy format exactly from spec above |
| `rewards` not in [0.0, 1.0] | Grader check fails | Clamp with `min(max(score, 0.0), 1.0)` |
| Graders always return same score | Disqualification | Test with multiple different queries |
| Fewer than 3 tasks | Auto-fail | Implement all 3 before submitting |
| HF Space not responding to `/reset` | Disqualification | Test `curl ... /reset` before submitting |
| `None` instead of `null` for error field | Wrong format | Use Python's `None` → `"null"` string |
| `done` as `True`/`False` capitalized | Wrong format | Use `str(done).lower()` |
| No `openenv.yaml` | Spec compliance fails | Include with exact format shown |
| Binary rewards only (0 or 1) | Low grader quality score | Implement partial scoring in `_grade()` |

---

## 15. What Makes You Stand Out

**For 30% real-world utility:** Add this to your README intro:
> "This environment enables training agents that can automate SQL generation for data analysts, reducing query-writing time. Unlike code generation benchmarks, SQL has deterministic correctness that makes grading reliable and reproducible — ideal for RL training."

**For 25% grader quality:** Make the hard task (`multi_join`) actually require multi-step reasoning. The agent should not be able to pass it with a naive query. Add a row count check so that `SELECT *` fails even if column names match.

**For 20% environment design:** Add one more reward signal: **query efficiency**. Give +0.1 bonus if the agent avoids `SELECT *` and targets only the needed columns. This is a real-world consideration and shows depth.

**For 10% creativity:** Add a fourth optional task `data_anomalies` where the agent must find data quality issues (duplicates, nulls, outliers) using SQL. This is genuinely novel and directly useful for data engineering agent training.

---

## 16. Key File Reference

```
sql-env/                          ← GitHub repo root
├── inference.py                  ← REQUIRED: named exactly this, at root
├── README.md                     ← Must have HF Space YAML frontmatter
├── openenv.yaml                  ← spec_version: 1, points to server.app:app
├── pyproject.toml                ← Package dependencies
├── __init__.py                   ← Exports SqlEnv, SqlAction, SqlObservation
├── client.py                     ← SqlEnv(EnvClient) — WebSocket client
├── models.py                     ← SqlAction, SqlObservation (Pydantic)
└── server/
    ├── __init__.py
    ├── app.py                    ← create_app(SqlEnvironment, ...)
    ├── sql_environment.py        ← Core logic: reset(), step(), _grade()
    ├── requirements.txt          ← openenv-core, fastapi, uvicorn
    └── Dockerfile                ← FROM python:3.11-slim ... CMD uvicorn
```

### Quick command reference

```bash
# Local development
PYTHONPATH=. uvicorn server.app:app --port 8000 --reload

# Docker build & test
docker build -t sql-env:latest -f server/Dockerfile .
docker run -d -p 8000:8000 sql-env:latest

# Validate
openenv validate --verbose
openenv validate --url http://localhost:8000

# Deploy
git push hf main
huggingface-cli upload YOUR_USERNAME/sql-env . --repo-type space

# Run hackathon validator
bash validate-submission.sh https://YOUR_USERNAME-sql-env.hf.space .

# Test inference
IMAGE_NAME=sql-env:latest HF_TOKEN=xxx python inference.py
```

---

*Document version: April 6, 2026 | For questions, refer to OpenEnv docs at meta-pytorch.org/OpenEnv*



