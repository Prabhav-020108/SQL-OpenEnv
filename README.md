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

SQL is the universal language of data. Every data analyst, data scientist, backend engineer, and business intelligence team writes SQL daily. An AI agent that can generate correct SQL from natural language descriptions has **immediate, real-world deployment value** in:

- **BI tools** — natural language to SQL for non-technical stakeholders
- **IDE copilots** — auto-completing database queries for developers  
- **Data pipelines** — automated query generation for ETL workflows
- **Database exploration** — letting agents query and analyze data autonomously

Unlike most code generation benchmarks, SQL has **deterministic, programmatic correctness** — the result set either matches the expected output or it doesn't. This makes grading perfectly reliable and reproducible, which is exactly what RL training demands.

> **No existing OpenEnv environment covers SQL query generation.** This fills a genuine gap in the ecosystem.

---

## 🏗️ Architecture

```
Agent (LLM)
    │
    │  Natural language task + schema
    │  ← receives observation
    │  → sends SQL query as action
    │
    ▼
FastAPI Server  (server/app.py)
    │
    │  WebSocket /ws  (persistent session)
    │  HTTP   /reset  /step  /health  /docs
    │
    ▼
SqlEnvironment  (server/sql_environment.py)
    ├── SQLite in-memory DB   (fresh per episode, zero cross-contamination)
    ├── Multi-component Grader (execute → columns → rows → values → efficiency)
    └── Reward computation    (F1-based partial scoring, never binary)
```

---

## ⚡ Quick Start

### Install the client

```bash
pip install git+https://huggingface.co/spaces/Codexzzz/sql-env
```

### Use with async (recommended)

```python
import asyncio
from sql_env import SqlEnv, SqlAction

async def main():
    async with SqlEnv(base_url="https://Codexzzz-sql-env.hf.space") as env:
        # Reset to a task
        result = await env.reset()
        print(result.observation.task_description)
        print(result.observation.schema_info)

        # Send a SQL query
        result = await env.step(SqlAction(
            sql_query="SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name"
        ))
        print(f"Reward: {result.reward}")
        print(f"Feedback: {result.observation.feedback}")
        print(f"Score breakdown: {result.observation.score_breakdown}")

asyncio.run(main())
```

### Use with sync wrapper

```python
from sql_env import SqlEnv, SqlAction

with SqlEnv(base_url="https://Codexzzz-sql-env.hf.space").sync() as env:
    result = env.reset()
    result = env.step(SqlAction(sql_query="SELECT name FROM customers WHERE city = 'New York'"))
    print(result.observation.feedback)
```

### Choose a specific task

```python
result = await env.reset(task="select_basics")    # Easy
result = await env.reset(task="aggregate_filter") # Medium
result = await env.reset(task="multi_join")       # Hard
```

---

## 🎯 Action Space

The agent sends exactly one thing per step: a SQL query string.

```python
SqlAction(sql_query: str)
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sql_query` | `str` | ✅ | Any valid SQL query string |

**Examples:**

```sql
-- Easy: basic filter
SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name;

-- Medium: aggregation with filter
SELECT c.name, SUM(o.amount) AS total_spent
FROM customers c JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name HAVING COUNT(o.id) > 2
ORDER BY total_spent DESC;

-- Hard: multi-table join with derived fields
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
```

---

## 👁️ Observation Space

Every observation returned by `reset()` and `step()`:

```python
SqlObservation(
    task_description:   str,   # Natural language task the agent must solve
    schema_info:        str,   # Full DDL — CREATE TABLE statements for the database
    query_result:       list,  # Rows returned by the agent's last query (empty on reset)
    error_message:      str,   # SQL error string if query failed, else ""
    feedback:           str,   # Human-readable grader explanation
    score_breakdown:    dict,  # Per-component partial scores
    attempts_remaining: int,   # Steps remaining in this episode
    done:               bool,  # True when episode ends
    reward:             float, # Step reward in [-0.10, 1.00]
)
```

**Example observation after a correct query:**

```python
SqlObservation(
    task_description="Find the full name and email of all customers from New York...",
    schema_info="CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT...)",
    query_result=[["Alice Brown", "alice@email.com"], ["Bob Smith", "bob@email.com"]],
    error_message="",
    feedback="Perfect! Exact match.",
    score_breakdown={"execute": 0.1, "columns": 0.2, "rows": 0.2, "values": 0.4, "efficiency": 0.1},
    attempts_remaining=4,
    done=True,
    reward=1.0,
)
```

**Example observation after a syntax error:**

```python
SqlObservation(
    query_result=[],
    error_message="no such column: bad_col",
    feedback="SQL Error: no such column: bad_col. Fix your syntax and try again.",
    score_breakdown={"execute": -0.05},
    reward=-0.05,
    done=False,
)
```

---

## 🏋️ Tasks

### Task 1: `select_basics` — Easy

**Goal:** The agent must retrieve the correct rows using a `SELECT` with `WHERE` and `ORDER BY`.

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

**Max steps:** 5 | **Why it's easy:** Single table, no joins, basic WHERE clause.

---

### Task 2: `aggregate_filter` — Medium

**Goal:** The agent must use `GROUP BY`, `HAVING`, aggregate functions, and a `JOIN`.

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
    id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL,
    amount REAL NOT NULL, order_date TEXT NOT NULL
);
```

**Expected result:**
```python
[("Alice Brown", 405.50), ("Bob Smith", 300.00)]
```

**Max steps:** 5 | **Why it's medium:** Requires JOIN + GROUP BY + HAVING — can't be solved with a naive SELECT.

---

### Task 3: `multi_join` — Hard

**Goal:** The agent must join 4 tables, extract month from a date, compute revenue as `quantity × price`, filter by year, and apply dual-column ordering.

**Task description given to agent:**
```
Generate a monthly revenue report for the year 2024.
For each month and product category return:
  - month in 'YYYY-MM' format
  - category name
  - number of distinct orders
  - total revenue (quantity × price)
Order by month ascending, then total revenue descending. Only include 2024 data.
```

**Database schema:**
```sql
CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category_id INTEGER NOT NULL, price REAL NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, order_date TEXT NOT NULL);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL);
```

**Expected result:**
```python
[
    ("2024-01", "Electronics", 1, 999.00),
    ("2024-01", "Books",       1, 137.00),
    ("2024-02", "Electronics", 1, 599.00),
    ("2024-02", "Books",       1, 147.00),
]
```

**Max steps:** 7 | **Why it's hard:** 4-table join, date extraction with `strftime`, derived revenue field, 2023 data must be excluded, dual sort order.

---

## 🏆 Reward Function

The reward function is designed around one principle: **never binary, always partial credit**.

### Formula

```
reward = execute_bonus + column_score + row_score + value_score + efficiency_bonus

execute_bonus    = +0.10  if query ran without error
                   -0.05  if syntax error

column_score     = +0.20 × (matching_columns / expected_columns)

row_score        = +0.20 × min(1.0, returned_rows / expected_rows)

value_score      = +0.40 × F1(result_set, expected_set)
                   where F1 = 2 × precision × recall / (precision + recall)

efficiency_bonus = +0.10  if no SELECT * used

Final clamp: reward = max(-0.10, min(1.00, reward))
```

### Why this design wins judges over

- **Never 0 or 1** — every attempt produces a learning signal
- **F1 on result sets** — partial row matches still get credit
- **Efficiency bonus** — real-world SQL best practice rewarded
- **Transparent breakdown** — `score_breakdown` dict tells the agent exactly what to fix
- **Negative penalty** — syntax errors give -0.05, teaching the agent to write valid SQL

### Score breakdown example

| Query type | execute | columns | rows | values | efficiency | total |
|-----------|---------|---------|------|--------|------------|-------|
| Perfect query | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 | **1.00** |
| `SELECT *` (correct data) | 0.10 | 0.20 | 0.20 | 0.40 | 0.00 | **0.90** |
| Wrong WHERE (no rows) | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | **0.10** |
| Syntax error | -0.05 | 0.00 | 0.00 | 0.00 | 0.00 | **-0.05** |
| 50% correct values | 0.10 | 0.20 | 0.20 | 0.20 | 0.10 | **0.80** |

---

## 📊 Baseline Scores

Model: `Qwen/Qwen2.5-72B-Instruct` | API: `https://router.huggingface.co/v1`

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
```

*Generated by running `python inference.py` with the configuration in the Environment Variables section.*

---

## 🛠️ Setup & Installation

### Option 1: Connect to the live HF Space (easiest)

```bash
pip install git+https://huggingface.co/spaces/Codexzzz/sql-env
```

```python
from sql_env import SqlEnv, SqlAction

async with SqlEnv(base_url="https://Codexzzz-sql-env.hf.space") as env:
    result = await env.reset(task="select_basics")
    result = await env.step(SqlAction(sql_query="SELECT name FROM customers"))
```

### Option 2: Run locally via Docker

```bash
# Pull from HF Spaces registry
docker pull registry.hf.space/Codexzzz-sql-env:latest

# Run locally
docker run -d -p 8000:8000 registry.hf.space/Codexzzz-sql-env:latest

# Connect
from sql_env import SqlEnv
env = SqlEnv(base_url="http://localhost:8000")
```

### Option 3: Build from source

```bash
git clone https://github.com/Prabhav-020108/SQL-OpenEnv.git
cd SQL-OpenEnv/sql_env
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

---

## 🤖 Running the Baseline Inference Script

### Required environment variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `HF_TOKEN` | Hugging Face token | `hf_...` |
| `IMAGE_NAME` | Local Docker image | `sql-env:latest` |

### Run it

```bash
# Set variables (Windows PowerShell)
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:MODEL_NAME   = "Qwen/Qwen2.5-72B-Instruct"
$env:HF_TOKEN     = "your_token_here"
$env:IMAGE_NAME   = "sql-env:latest"

python inference.py

# Set variables (Linux/Mac)
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your_token_here"
export IMAGE_NAME="sql-env:latest"

python inference.py
```

### Expected stdout format

```
[START] task=select_basics env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city='New York' ORDER BY name reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=aggregate_filter env=sql_env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=true steps=2 score=0.950 rewards=0.72,0.95
[START] task=multi_join env=sql_env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=false steps=7 score=0.720 rewards=0.10,0.48,0.72,0.72,0.72,0.72,0.72
```

---

## 📁 Project Structure

```
SQL-OpenEnv/
├── inference.py                ← Baseline agent script (REQUIRED at root)
├── README.md                   ← This file (HF Space metadata at top)
└── sql_env/
    ├── __init__.py             ← Exports SqlEnv, SqlAction, SqlObservation
    ├── models.py               ← Pydantic models: SqlAction, SqlObservation
    ├── client.py               ← SqlEnv WebSocket client
    ├── openenv.yaml            ← OpenEnv manifest
    ├── pyproject.toml          ← Package config and dependencies
    └── server/
        ├── __init__.py         ← Exports SqlEnvironment
        ├── sql_environment.py  ← Core logic: TASKS, grader, reward
        ├── app.py              ← FastAPI app via create_app()
        ├── requirements.txt    ← Docker pip dependencies
        └── Dockerfile          ← Container definition
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — returns `{"status": "healthy"}` |
| `/reset` | POST | Start new episode, optionally pass `{"task": "task_name"}` |
| `/step` | POST | Execute SQL action, returns observation + reward |
| `/state` | GET | Get current episode state |
| `/ws` | WebSocket | Persistent session endpoint (used by Python client) |
| `/docs` | GET | Interactive OpenAPI documentation |
| `/web` | GET | Built-in web UI for manual testing |

---

## ⚙️ Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `WORKERS` | 4 | Uvicorn worker processes |
| `PORT` | 8000 | Server port |
| `HOST` | 0.0.0.0 | Bind address |
| `MAX_CONCURRENT_ENVS` | 10 | Max WebSocket sessions |
| `ENABLE_WEB_INTERFACE` | Auto | Enable web UI |

---

## ✅ OpenEnv Spec Compliance

This environment passes all OpenEnv validation checks:

```bash
openenv validate --verbose
openenv validate --url https://Codexzzz-sql-env.hf.space
```

- ✅ `openenv.yaml` with `spec_version: 1`
- ✅ Typed Pydantic `Action` and `Observation` models
- ✅ `reset()`, `step()`, `state()` endpoints
- ✅ WebSocket `/ws` persistent session
- ✅ Docker containerized deployment
- ✅ HF Space with `openenv` tag
- ✅ Baseline inference script with `[START]`/`[STEP]`/`[END]` format

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with [OpenEnv](https://github.com/meta-pytorch/OpenEnv) | Meta × Hugging Face Hackathon 2026*