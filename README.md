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
- **Analytics** — window functions for ranking, percentiles, and moving averages

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
    ├── Module-level session store  (survives new-instance-per-request pattern)
    ├── Multi-component Grader  (execute → columns → rows → values → efficiency)
    ├── Float normalization  (handles IEEE 754 rounding in SUM/AVG/ROUND)
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
export LOCAL_IMAGE_NAME="Codexzzz-sql-env.hf.space"

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
result = await env.reset(task="select_basics")    # Easy    — max 5 steps
result = await env.reset(task="aggregate_filter") # Medium  — max 5 steps
result = await env.reset(task="multi_join")       # Hard    — max 7 steps
result = await env.reset(task="data_anomalies")   # Expert  — max 7 steps
result = await env.reset(task="window_functions") # Expert+ — max 8 steps
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

-- Expert+: window functions for analytics
SELECT
    e.name,
    d.name AS department,
    RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS salary_rank,
    ROUND(e.salary - AVG(e.salary) OVER (PARTITION BY e.department_id), 2) AS diff_from_avg
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name ASC, salary_rank ASC;
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

---

## 🏋️ Tasks

### Task 1: `select_basics` — Easy

**Goal:** Retrieve the correct rows using `SELECT`, `WHERE`, and `ORDER BY`.

**Task description given to agent:**
```
Find the full name and email address of all customers who live in 'New York'.
Return results sorted alphabetically by name (A to Z).
```

**Schema:**
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    email TEXT NOT NULL, city TEXT NOT NULL, age INTEGER
);
```

**Expected result:**
```python
[("Alice Brown", "alice@email.com"), ("Bob Smith", "bob@email.com"), ("David Lee", "david@email.com")]
```

**Max steps:** 5

---

### Task 2: `aggregate_filter` — Medium

**Goal:** Use `JOIN`, `GROUP BY`, aggregate functions, and `HAVING` to filter groups.

**Task description:**
```
Find each customer who has placed MORE THAN 2 orders.
Return their name and total amount spent. Sort by total amount spent, highest first.
```

**Expected result:**
```python
[("Alice Brown", 405.50), ("Bob Smith", 300.00)]
```

**Max steps:** 5

---

### Task 3: `multi_join` — Hard

**Goal:** Join 4 tables, extract date components, compute derived revenue, filter by year.

**Task description:**
```
Generate a monthly revenue report for 2024. Return month (YYYY-MM), category name,
distinct order count, and total revenue. Order by month ASC, revenue DESC.
```

**Expected result:**
```python
[("2024-01", "Electronics", 1, 999.0), ("2024-01", "Books", 1, 137.0),
 ("2024-02", "Electronics", 1, 599.0), ("2024-02", "Books", 1, 147.0)]
```

**Max steps:** 7

---

### Task 4: `data_anomalies` — Expert

**Goal:** Audit a table for data quality issues using subqueries and `UNION ALL`.

**Task description:**
```
Find data quality issues: duplicate_email, invalid_age, null_name.
Return issue type and count. Order alphabetically by issue type.
```

**Expected result:**
```python
[("duplicate_email", 2), ("invalid_age", 2), ("null_name", 1)]
```

**Max steps:** 7

---

### Task 5: `window_functions` — Expert+

**Goal:** Use SQL window functions (`RANK() OVER`, `AVG() OVER`) for analytics.

**Task description:**
```
For each employee, calculate their salary rank within their department
and the difference between their salary and their department's average salary.
Return: employee name, department name, salary rank (1 = highest),
and salary minus department average (rounded to 2 decimal places).
Order by department name ASC, then rank ASC.
```

**Schema:**
```sql
CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE employees (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    department_id INTEGER NOT NULL, salary REAL NOT NULL
);
```

**Expected result:**
```python
[("Alice", "Engineering", 1,  5000.0),
 ("Carol", "Engineering", 2,     0.0),
 ("Bob",   "Engineering", 3, -5000.0),
 ("Eve",   "Marketing",   1,  5000.0),
 ("Dave",  "Marketing",   2,     0.0),
 ("Frank", "Marketing",   3, -5000.0)]
```

**Max steps:** 8 | **Why expert+:** Requires `RANK() OVER (PARTITION BY ...)` and `AVG() OVER (PARTITION BY ...)` — real-world analytics patterns used in every data team.

---

## 🏆 Reward Function

```
reward = execute_bonus + column_score + row_score + value_score + efficiency_bonus

execute_bonus    = +0.10  if query ran without error
                   -0.05  if syntax/runtime error
                   -0.10  if query timed out (>5 seconds)

column_score     = +0.20 × (matching_columns / expected_columns)
row_score        = +0.20 × min(1.0, returned_rows / expected_rows)
value_score      = +0.40 × F1(result_set, expected_set)
efficiency_bonus = +0.10  if SELECT * is NOT used

Final clamp: reward = max(-0.10, min(1.00, reward))
```

**Float normalization:** The grader rounds all float values to 2 decimal places before comparison, preventing false mismatches from IEEE 754 floating-point arithmetic (e.g. `405.4999999999` vs `405.5`).

---

## 📊 Baseline Scores

**Model:** `Qwen/Qwen2.5-72B-Instruct` | **API:** `https://router.huggingface.co/v1`

```
[START] task=select_basics env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=0.999 done=true error=null
[END] success=true steps=1 score=0.999 rewards=0.999
[START] task=aggregate_filter env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT c.name, SUM(o.amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id G reward=0.999 done=true error=null
[END] success=true steps=1 score=0.999 rewards=0.999
[START] task=multi_join env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT      strftime('%Y-%m', o.order_date) AS month,      c.name AS category_name,      COUNT(DISTI reward=0.999 done=true error=null
[END] success=true steps=1 score=0.999 rewards=0.999
[START] task=data_anomalies env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=0.999 done=true error=null
[END] success=true steps=1 score=0.999 rewards=0.999
[START] task=window_functions env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=0.999 done=true error=null
[END] success=true steps=1 score=0.999 rewards=0.999
```

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
export LOCAL_IMAGE_NAME="Codexzzz-sql-env.hf.space"

python inference.py
```

### Option 2: Run locally via Docker

```bash
docker build -t sql-env:latest .
docker run -d -p 8000:8000 sql-env:latest

# Test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/reset \
     -H "Content-Type: application/json" \
     -d '{"task": "select_basics"}'

export LOCAL_IMAGE_NAME="sql-env:latest"
python inference.py
```

### Option 3: Development server (no Docker)

```bash
pip install -e sql_env/
PYTHONPATH=./sql_env uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🤖 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | No | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `HF_TOKEN` | **Yes** | — | Hugging Face / API key |
| `LOCAL_IMAGE_NAME` | **Yes** | — | Docker image name or Space URL |

---

## 📁 Project Structure

```
SQL-OpenEnv/                         ← repo root
├── inference.py                     ← Baseline agent script
├── README.md                        ← This file
├── openenv.yaml                     ← OpenEnv manifest
├── pyproject.toml                   ← Root package config
├── Dockerfile                       ← Container definition
├── validate-submission.sh           ← Submission validator
├── LICENSE                          ← MIT License
└── sql_env/
    ├── __init__.py
    ├── models.py                    ← SqlAction, SqlObservation
    ├── client.py                    ← SqlEnv client
    ├── openenv.yaml
    ├── pyproject.toml
    └── server/
        ├── __init__.py
        ├── sql_environment.py       ← 5 tasks, grader, reward function
        ├── app.py                   ← FastAPI app
        ├── requirements.txt
        └── Dockerfile
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/reset` | POST | Start new episode — pass `{"task": "task_name"}` |
| `/step` | POST | Execute SQL — pass `{"action": {"sql_query": "..."}}` |
| `/state` | GET | Get current episode state |
| `/ws` | WebSocket | Persistent session endpoint |
| `/docs` | GET | Interactive OpenAPI documentation |
| `/web` | GET | Built-in OpenEnv web UI |

---

## ✅ OpenEnv Spec Compliance

- ✅ `openenv.yaml` at root with `spec_version: 1`
- ✅ Typed Pydantic `Action` and `Observation` models
- ✅ `reset()`, `step()`, `state()` endpoints implemented
- ✅ WebSocket `/ws` persistent session support
- ✅ Docker containerized — builds and runs cleanly
- ✅ Deployed on HF Space tagged with `openenv`
- ✅ Baseline inference script: correct `[START]`/`[STEP]`/`[END]` format
- ✅ 5 tasks with programmatic F1-based graders
- ✅ All rewards clamped to `[-0.10, 1.00]` range
- ✅ Score output strictly in `(0, 1)` — never exactly `0.0` or `1.0`
- ✅ Float normalization prevents IEEE 754 false mismatches

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with [OpenEnv](https://github.com/meta-pytorch/OpenEnv) | Meta × Hugging Face Hackathon 2026*
*Team: Prabhav Tiwari, Shaurya Khanna, Yashraj Pala (Devsters)*