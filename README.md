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
  - nlp
  - text-generation
---

# 🗃️ SQL Query Grader — OpenEnv Environment

> **An RL training environment where AI agents learn to write correct SQL queries from natural language task descriptions.**
> Built for the **Meta × Hugging Face OpenEnv Hackathon 2026**.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🌍 Why This Environment Matters

SQL is the universal language of data. Every analyst, data scientist, backend engineer, and BI team writes SQL daily. An AI agent that generates correct SQL from natural language has **immediate, real-world deployment value** in:

- **BI tools** — natural language to SQL for non-technical stakeholders
- **IDE copilots** — auto-completing database queries for developers
- **Data pipelines** — automated query generation for ETL workflows
- **Database exploration** — letting agents query and analyze data autonomously
- **Data quality** — automated anomaly detection queries for data engineering

Unlike most code generation benchmarks, SQL has **deterministic, programmatic correctness** — the result set either matches expected output or it doesn't. This makes grading perfectly reliable and reproducible, exactly what RL training demands.

> **No existing OpenEnv environment covers SQL query generation.** This fills a genuine gap in the ecosystem.

---

## 🏗️ Architecture

```
Agent (LLM)
    │
    │  Natural language task + schema  ← observation
    │  SQL query string                → action
    │
    ▼
FastAPI Server  (server/app.py)
    │
    │  WebSocket /ws   (persistent session)
    │  HTTP   /reset   /step   /health   /docs
    │
    ▼
SqlEnvironment  (server/sql_environment.py)
    ├── SQLite DB           (fresh per episode, zero cross-contamination)
    ├── Multi-component Grader  (execute → columns → rows → values → efficiency)
    └── Reward computation      (F1-based partial scoring, never binary)
```

---

## ⚡ Quick Start

### Run inference against the live HF Space

```bash
git clone https://github.com/Prabhav-020108/SQL-OpenEnv.git
cd SQL-OpenEnv

export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
export IMAGE_NAME="Codexzzz-sql-env.hf.space"

pip install openai "openenv-core[core]>=0.2.2"
python inference.py
```

### Use the Python client directly

```python
import asyncio
from sql_env import SqlEnv, SqlAction

async def main():
    env = await SqlEnv.from_docker_image("Codexzzz-sql-env.hf.space")

    # Reset to start an episode on a specific task
    result = await env.reset(task="select_basics")
    obs = result.observation
    print(obs.task_description)
    print(obs.schema_info)

    # Send a SQL query as the action
    result = await env.step(SqlAction(
        sql_query="SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name"
    ))
    print(f"Reward:     {result.reward}")
    print(f"Feedback:   {result.observation.feedback}")
    print(f"Breakdown:  {result.observation.score_breakdown}")

    await env.close()

asyncio.run(main())
```

### Choose a specific task

```python
result = await env.reset(task="select_basics")    # Easy   — max 5 steps
result = await env.reset(task="aggregate_filter") # Medium — max 5 steps
result = await env.reset(task="multi_join")       # Hard   — max 7 steps
result = await env.reset(task="data_anomalies")   # Expert — max 7 steps
```

---

## 🎯 Action Space

The agent sends exactly one thing per step: a SQL query string.

```python
SqlAction(sql_query: str)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sql_query` | `str` | ✅ | Any valid SQLite SQL query string |

**Examples across difficulty levels:**

```sql
-- Easy: filter + sort
SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name;

-- Medium: JOIN + GROUP BY + HAVING
SELECT c.name, SUM(o.amount) AS total_spent
FROM customers c JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name HAVING COUNT(o.id) > 2
ORDER BY total_spent DESC;

-- Hard: 4-table JOIN with date functions
SELECT strftime('%Y-%m', o.order_date) AS month,
       cat.name, COUNT(DISTINCT o.id) AS order_count,
       SUM(oi.quantity * p.price) AS total_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.id
JOIN categories cat ON p.category_id = cat.id
JOIN orders o ON oi.order_id = o.id
WHERE strftime('%Y', o.order_date) = '2024'
GROUP BY month, cat.id
ORDER BY month ASC, total_revenue DESC;

-- Expert: data quality audit with UNION ALL
SELECT 'duplicate_email' AS issue_type,
       COUNT(*) AS affected_rows
FROM (SELECT email FROM customers GROUP BY email HAVING COUNT(*) > 1)
UNION ALL
SELECT 'invalid_age', COUNT(*)
FROM customers WHERE age IS NULL OR age < 0 OR age > 150
UNION ALL
SELECT 'null_name', COUNT(*)
FROM customers WHERE name IS NULL
ORDER BY issue_type;
```

---

## 👁️ Observation Space

Every observation returned by `reset()` and `step()`:

```python
SqlObservation(
    task_description:   str,    # Natural language task the agent must solve
    schema_info:        str,    # Full DDL — CREATE TABLE statements
    query_result:       list,   # Rows returned by last query (empty on reset)
    error_message:      str,    # SQL error string if query failed, else ""
    feedback:           str,    # Human-readable grader explanation
    score_breakdown:    dict,   # Per-component partial scores
    attempts_remaining: int,    # Steps remaining in this episode
    done:               bool,   # True when episode ends
    reward:             float,  # Step reward in [-0.10, 1.00]
)
```

**After a perfect query:**

```python
SqlObservation(
    task_description   = "Find the full name and email of all customers from New York...",
    schema_info        = "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT...)",
    query_result       = [["Alice Brown", "alice@email.com"], ["Bob Smith", "bob@email.com"], ["David Lee", "david@email.com"]],
    error_message      = "",
    feedback           = "Perfect! Exact match.",
    score_breakdown    = {"execute": 0.1, "columns": 0.2, "rows": 0.2, "values": 0.4, "efficiency": 0.1},
    attempts_remaining = 4,
    done               = True,
    reward             = 1.0,
)
```

**After a syntax error:**

```python
SqlObservation(
    query_result    = [],
    error_message   = "no such column: bad_col",
    feedback        = "SQL Error: no such column: bad_col. Fix your syntax and try again.",
    score_breakdown = {"execute": -0.05},
    reward          = -0.05,
    done            = False,
)
```

---

## 🏋️ Tasks

### Task 1: `select_basics` — Easy

**Goal:** Retrieve the correct rows using `SELECT`, `WHERE`, and `ORDER BY`.

**Task description given to agent:**
```
Find the full name and email address of all customers who live in 'New York'.
Return results sorted alphabetically by name (A to Z).
```

**Database schema:**
```sql
CREATE TABLE customers (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    email     TEXT    NOT NULL,
    city      TEXT    NOT NULL,
    age       INTEGER
);
```

**Expected result:**
```python
[("Alice Brown", "alice@email.com"), ("Bob Smith", "bob@email.com"), ("David Lee", "david@email.com")]
```

**Max steps:** 5 | **Why easy:** Single table, no joins, basic WHERE + ORDER BY.

---

### Task 2: `aggregate_filter` — Medium

**Goal:** Use `JOIN`, `GROUP BY`, aggregate functions, and `HAVING` to filter groups.

**Task description given to agent:**
```
Find each customer who has placed MORE THAN 2 orders.
Return their name and total amount spent (sum of all order amounts).
Sort by total amount spent, highest first.
```

**Database schema:**
```sql
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    order_date  TEXT    NOT NULL
);
```

**Expected result:**
```python
[("Alice Brown", 405.50), ("Bob Smith", 300.00)]
```

**Max steps:** 5 | **Why medium:** Requires JOIN + GROUP BY + HAVING — cannot be solved with a naive SELECT.

---

### Task 3: `multi_join` — Hard

**Goal:** Join 4 tables, extract date components, compute derived revenue, filter by year, and apply dual-column ordering.

**Task description given to agent:**
```
Generate a monthly revenue report for the year 2024.
For each month and product category return:
  - month in 'YYYY-MM' format
  - category name
  - number of distinct orders that included products from that category
  - total revenue (quantity × product price, summed across all items)
Order by month ascending, then total revenue descending within each month.
Only include data from 2024.
```

**Database schema:**
```sql
CREATE TABLE categories  (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE products    (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category_id INTEGER NOT NULL, price REAL NOT NULL);
CREATE TABLE orders      (id INTEGER PRIMARY KEY, order_date TEXT NOT NULL);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL);
```

**Expected result:**
```python
[
    ("2024-01", "Electronics", 1,  999.00),
    ("2024-01", "Books",       1,  137.00),
    ("2024-02", "Electronics", 1,  599.00),
    ("2024-02", "Books",       1,  147.00),
]
```

**Max steps:** 7 | **Why hard:** 4-table join, `strftime()` date extraction, `quantity × price` revenue calculation, year filter excludes 2023 data, dual-column sort order.

---

### Task 4: `data_anomalies` — Expert

**Goal:** Audit a table for data quality issues using subqueries and `UNION ALL`.

**Task description given to agent:**
```
Find data quality issues in the customers table.
Return: the type of issue as a string and the count of affected rows.
The three issue types to check are:
  1. 'duplicate_email' — email addresses that appear more than once
  2. 'invalid_age'     — age values that are NULL, negative, or greater than 150
  3. 'null_name'       — rows where name is NULL
Return all three rows ordered alphabetically by issue type.
Use UNION ALL to combine the three checks into one result set.
```

**Database schema:**
```sql
CREATE TABLE customers (
    id    INTEGER PRIMARY KEY,
    name  TEXT,
    email TEXT,
    age   INTEGER
);
```

**Expected result:**
```python
[("duplicate_email", 2), ("invalid_age", 2), ("null_name", 1)]
```

**Max steps:** 7 | **Why expert:** Requires subqueries, multi-condition NULL handling, UNION ALL across different query types, and alphabetical ordering — a common real-world data engineering pattern with no single obvious query structure.

---

## 🏆 Reward Function

The reward function is built on one principle: **never binary, always partial credit**.

### Formula

```
reward = execute_bonus + column_score + row_score + value_score + efficiency_bonus

execute_bonus    = +0.10  if query ran without error
                   -0.05  if syntax or runtime error
                   -0.10  if query timed out (> 5 seconds)

column_score     = +0.20 × (matching_columns / expected_columns)

row_score        = +0.20 × min(1.0, returned_rows / expected_rows)

value_score      = +0.40 × F1(result_set, expected_set)
                   where F1 = 2 × precision × recall / (precision + recall)

efficiency_bonus = +0.10  if SELECT * is NOT used

Final clamp: reward = max(-0.10, min(1.00, reward))
```

### Why this design is effective for RL training

- **Never 0 or 1** — every attempt produces a gradient signal
- **F1 on result sets** — partial row matches receive proportional credit
- **Efficiency bonus** — teaches real-world SQL best practice
- **Transparent breakdown** — `score_breakdown` dict pinpoints exactly what to fix
- **Negative penalty** — syntax errors teach the agent to write valid SQL before optimizing
- **Timeout penalty** — discourages infinite loops and full table scans

### Score examples

| Query type | execute | columns | rows | values | efficiency | **total** |
|-----------|---------|---------|------|--------|------------|---------|
| Perfect query (no `SELECT *`) | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 | **1.00** |
| Correct data but `SELECT *` | 0.10 | 0.20 | 0.20 | 0.40 | 0.00 | **0.90** |
| Wrong WHERE (0 rows returned) | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | **0.10** |
| Syntax error | -0.05 | 0.00 | 0.00 | 0.00 | 0.00 | **-0.05** |
| 50% values correct | 0.10 | 0.20 | 0.20 | 0.20 | 0.10 | **0.80** |
| Query timeout | -0.10 | 0.00 | 0.00 | 0.00 | 0.00 | **-0.10** |

---

## 📊 Baseline Scores

**Model:** `Qwen/Qwen2.5-72B-Instruct` | **API:** `https://router.huggingface.co/v1`

```
[START] task=select_basics env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=aggregate_filter env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT c.name, SUM(o.amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id G reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=multi_join env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT      strftime('%Y-%m', o.order_date) AS month,      c.name AS category_name,      COUNT(DISTI reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=data_anomalies env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
```

*Generated by running `python inference.py` with the environment variables listed below.*

---

## 🛠️ Setup & Installation

### Option 1: Run inference against the live HF Space (fastest)

```bash
git clone https://github.com/Prabhav-020108/SQL-OpenEnv.git
cd SQL-OpenEnv
pip install openai "openenv-core[core]>=0.2.2"

export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
export IMAGE_NAME="Codexzzz-sql-env.hf.space"

python inference.py
```

### Option 2: Run locally via Docker

```bash
# Build the image from repo root
docker build -t sql-env:latest .

# Run locally
docker run -d -p 8000:8000 sql-env:latest

# Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/reset \
     -H "Content-Type: application/json" \
     -d '{"task": "select_basics"}'

# Run inference against local container
export IMAGE_NAME="sql-env:latest"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
python inference.py
```

### Option 3: Development server (no Docker)

```bash
git clone https://github.com/Prabhav-020108/SQL-OpenEnv.git
cd SQL-OpenEnv
pip install -e sql_env/
PYTHONPATH=./sql_env uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🤖 Running the Baseline Inference Script

### Required environment variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `HF_TOKEN` | Hugging Face / API key | `hf_...` |
| `IMAGE_NAME` | Docker image name or Space URL | `sql-env:latest` |

### Linux / Mac

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
export IMAGE_NAME="sql-env:latest"
python inference.py
```

### Windows PowerShell

```powershell
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:MODEL_NAME   = "Qwen/Qwen2.5-72B-Instruct"
$env:HF_TOKEN     = "hf_your_token_here"
$env:IMAGE_NAME   = "sql-env:latest"
python inference.py
```

### Expected stdout format

```
[START] task=<task_name> env=sql_env model=<model_name>
[STEP] step=<n> action=<sql_trimmed_to_100_chars> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
```

---

## 📁 Project Structure

```
SQL-OpenEnv/                         ← repo root
├── inference.py                     ← Baseline agent script (REQUIRED at root)
├── README.md                        ← This file (HF Space frontmatter at top)
├── openenv.yaml                     ← OpenEnv manifest (spec_version, app, port)
├── pyproject.toml                   ← Root package config for openenv validate
├── Dockerfile                       ← Container definition for HF Space deployment
├── validate-submission.sh           ← Hackathon pre-submission validator
├── LICENSE                          ← MIT License
└── sql_env/
    ├── __init__.py                  ← Exports SqlEnv, SqlAction, SqlObservation
    ├── models.py                    ← Pydantic models: SqlAction, SqlObservation
    ├── client.py                    ← SqlEnv WebSocket/HTTP client (EnvClient)
    ├── openenv.yaml                 ← Package-level OpenEnv manifest
    ├── pyproject.toml               ← Package dependencies
    └── server/
        ├── __init__.py              ← Exports SqlEnvironment
        ├── sql_environment.py       ← Core logic: 4 TASKS, grader, reward function
        ├── app.py                   ← FastAPI app via create_app()
        ├── requirements.txt         ← Docker pip dependencies
        └── Dockerfile               ← Inner Dockerfile (standalone sql_env package)
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — returns `{"status": "healthy"}` |
| `/reset` | POST | Start new episode — pass `{"task": "task_name"}` optionally |
| `/step` | POST | Execute SQL action — returns observation + reward |
| `/state` | GET | Get current episode state |
| `/ws` | WebSocket | Persistent session endpoint (used by Python client) |
| `/docs` | GET | Interactive OpenAPI documentation |
| `/web` | GET | Built-in OpenEnv web UI for manual testing |

---

## ✅ OpenEnv Spec Compliance

```bash
# Validate locally
openenv validate --verbose

# Run full submission validator
bash validate-submission.sh https://Codexzzz-sql-env.hf.space .
```

- ✅ `openenv.yaml` at root with `spec_version: 1`
- ✅ Typed Pydantic `Action` and `Observation` models
- ✅ `reset()`, `step()`, `state()` endpoints implemented
- ✅ WebSocket `/ws` persistent session support
- ✅ Docker containerized — builds and runs cleanly
- ✅ Deployed on HF Space tagged with `openenv`
- ✅ Baseline inference script: correct `[START]`/`[STEP]`/`[END]` format
- ✅ 4 tasks with programmatic F1-based graders
- ✅ All rewards clamped to `[-0.10, 1.00]` range

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with [OpenEnv](https://github.com/meta-pytorch/OpenEnv) | Meta × Hugging Face Hackathon 2026*