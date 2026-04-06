# Phase 2: SQL Query Grader — Environment Design Document

> **Status:** Design phase — read this fully before writing any code.  
> **Purpose:** Define every decision about tasks, rewards, state, and grading before implementation.  
> Commit this file to your repo so teammates and judges can see the design intent.

---

## Why SQL? (Justify the 30% real-world utility score)

SQL query writing is one of the most common technical tasks in data-driven companies. Every analyst, data scientist, and backend engineer writes SQL daily. Training agents to write correct SQL has immediate, demonstrable value:

- Automates database querying for non-technical users
- Powers natural language to SQL (NL2SQL) systems used in BI tools
- Enables AI copilots for database exploration
- Has **deterministic, reproducible grading** — the result set is either correct or it isn't
- Natural difficulty ladder from `SELECT` → `GROUP BY` → multi-table `JOIN`

Unlike games or toy tasks, a SQL-writing agent trained on this environment can be directly deployed in production tools. That is the argument for maximum real-world utility points.

---

## Environment Name & Structure

```
Environment name:  sql_env
HF Space URL:      https://YOUR_USERNAME-sql-env.hf.space
Episode model:     One task per episode, up to max_steps attempts
Concurrency:       SUPPORTS_CONCURRENT_SESSIONS = True (SQLite in-memory per session)
```

---

## Action Space

The agent sends exactly one thing: a SQL query string.

```python
SqlAction(sql_query: str)
```

**Examples:**
```sql
SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name;
SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id HAVING COUNT(o.id) > 2 ORDER BY 2 DESC;
```

**Why single-action design?**  
Keeps the environment simple and focused. The agent's entire intelligence goes into writing better SQL based on feedback from previous attempts. No tool-calling complexity, no multi-step action sequences within a single step.

---

## Observation Space

Every observation the agent receives after `reset()` or `step()`:

```python
SqlObservation(
    task_description:   str,    # Natural language task to solve
    schema_info:        str,    # Full DDL (CREATE TABLE statements + column comments)
    query_result:       list,   # Rows returned by the agent's query (empty on reset)
    error_message:      str,    # SQL error string if query failed, else ""
    feedback:           str,    # Human-readable grader explanation
    score_breakdown:    dict,   # Partial scores: {"columns": 0.2, "rows": 0.1, "values": 0.3}
    attempts_remaining: int,    # How many steps left in this episode
    done:               bool,
    reward:             float,  # Step reward in [-0.1, 1.0]
)
```

**Key design decision — include `score_breakdown`:**  
Most environments only return a scalar reward. By including a breakdown dict, the agent gets richer signal: it can see it got columns right but values wrong, and adjust accordingly. This also makes the reward function transparent and explainable to judges.

---

## State

```python
State(
    episode_id:  str,   # UUID, new per reset()
    step_count:  int,   # Increments on every step()
    task_name:   str,   # Which of the 3 tasks is active
)
```

---

## The 3 Tasks — Full Specification

### Task 1: `select_basics` — Easy

**Why this task:**  
A beginner-level SQL task. Any model that knows SQL should be able to pass this in 1-2 attempts. It establishes a non-trivial but achievable baseline score.

**Natural language description given to agent:**
```
Find the full name and email address of all customers who live in 'New York'.
Return results sorted alphabetically by name (A→Z).
```

**Database schema:**
```sql
CREATE TABLE customers (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,   -- full name, e.g. 'Alice Brown'
    email     TEXT    NOT NULL,   -- email address
    city      TEXT    NOT NULL,   -- city of residence
    age       INTEGER             -- age in years, nullable
);
```

**Seed data:**
```sql
INSERT INTO customers VALUES (1, 'Alice Brown',  'alice@email.com',  'New York', 28);
INSERT INTO customers VALUES (2, 'Bob Smith',    'bob@email.com',    'New York', 34);
INSERT INTO customers VALUES (3, 'Carol Davis',  'carol@email.com',  'Chicago',  25);
INSERT INTO customers VALUES (4, 'David Lee',    'david@email.com',  'New York', 41);
INSERT INTO customers VALUES (5, 'Eve Wilson',   'eve@email.com',    'Boston',   30);
```

**Expected result (exact):**
```python
[
    ("Alice Brown",  "alice@email.com"),
    ("Bob Smith",    "bob@email.com"),
    ("David Lee",    "david@email.com"),
]
```

**Perfect query:**
```sql
SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name;
```

**Max steps:** 5  
**Pass threshold:** reward >= 0.95

---

### Task 2: `aggregate_filter` — Medium

**Why this task:**  
Requires understanding GROUP BY, HAVING, and aggregate functions. Cannot be solved with a naive SELECT. Genuinely tests SQL knowledge beyond basics.

**Natural language description given to agent:**
```
Find each customer who has placed MORE THAN 2 orders.
Return their name and total amount spent (sum of all order amounts).
Sort by total amount spent, highest first.
```

**Database schema:**
```sql
CREATE TABLE customers (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,  -- foreign key → customers.id
    amount      REAL    NOT NULL,  -- order value in dollars
    order_date  TEXT    NOT NULL   -- ISO date string 'YYYY-MM-DD'
);
```

**Seed data:**
```sql
INSERT INTO customers VALUES (1, 'Alice Brown');
INSERT INTO customers VALUES (2, 'Bob Smith');
INSERT INTO customers VALUES (3, 'Carol Davis');

INSERT INTO orders VALUES (1,  1, 120.00, '2024-01-10');
INSERT INTO orders VALUES (2,  1,  85.50, '2024-01-15');
INSERT INTO orders VALUES (3,  1, 200.00, '2024-02-01');
INSERT INTO orders VALUES (4,  2,  45.00, '2024-01-20');
INSERT INTO orders VALUES (5,  2,  95.00, '2024-02-10');
INSERT INTO orders VALUES (6,  2, 160.00, '2024-02-15');
INSERT INTO orders VALUES (7,  3,  30.00, '2024-01-05');
-- Carol only has 1 order → should NOT appear in results
```

**Expected result (exact):**
```python
[
    ("Alice Brown", 405.50),
    ("Bob Smith",   300.00),
]
```

**Perfect query:**
```sql
SELECT c.name, SUM(o.amount) AS total_spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 2
ORDER BY total_spent DESC;
```

**Max steps:** 5  
**Pass threshold:** reward >= 0.95

---

### Task 3: `multi_join` — Hard

**Why this task:**  
Requires joining 4 tables, computing derived fields (month extraction, revenue = price × quantity), grouping on multiple dimensions, and applying dual-column ordering. This should challenge frontier LLMs and will almost never be solved on the first attempt.

**Natural language description given to agent:**
```
Generate a monthly revenue report for the year 2024.
For each month and product category, return:
  - month in 'YYYY-MM' format
  - category name
  - number of distinct orders that included products from that category
  - total revenue (quantity × product price, summed across all items)
Order results by month ascending, then by total revenue descending within each month.
Only include data from 2024.
```

**Database schema:**
```sql
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL   -- e.g. 'Electronics', 'Books'
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    category_id INTEGER NOT NULL,  -- foreign key → categories.id
    price       REAL    NOT NULL   -- unit price
);

CREATE TABLE orders (
    id         INTEGER PRIMARY KEY,
    order_date TEXT    NOT NULL    -- ISO date 'YYYY-MM-DD'
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL,   -- foreign key → orders.id
    product_id INTEGER NOT NULL,   -- foreign key → products.id
    quantity   INTEGER NOT NULL    -- units purchased
);
```

**Seed data:**
```sql
INSERT INTO categories VALUES (1, 'Electronics');
INSERT INTO categories VALUES (2, 'Books');

INSERT INTO products VALUES (1, 'Laptop',       1, 999.00);
INSERT INTO products VALUES (2, 'Phone',         1, 599.00);
INSERT INTO products VALUES (3, 'Python Book',   2,  49.00);
INSERT INTO products VALUES (4, 'SQL Handbook',  2,  39.00);

INSERT INTO orders VALUES (1, '2024-01-15');
INSERT INTO orders VALUES (2, '2024-01-20');
INSERT INTO orders VALUES (3, '2024-02-10');
INSERT INTO orders VALUES (4, '2024-02-28');
INSERT INTO orders VALUES (5, '2023-12-01');  -- ← 2023, must be excluded

INSERT INTO order_items VALUES (1, 1, 1, 1);   -- order 1: 1× Laptop
INSERT INTO order_items VALUES (2, 2, 3, 2);   -- order 2: 2× Python Book
INSERT INTO order_items VALUES (3, 2, 4, 1);   -- order 2: 1× SQL Handbook
INSERT INTO order_items VALUES (4, 3, 2, 1);   -- order 3: 1× Phone
INSERT INTO order_items VALUES (5, 4, 3, 3);   -- order 4: 3× Python Book
INSERT INTO order_items VALUES (6, 5, 1, 1);   -- order 5: 1× Laptop (2023 — excluded)
```

**Expected result (exact):**
```python
[
    ("2024-01", "Electronics", 1,  999.00),   # 1 order, 1×999
    ("2024-01", "Books",       1,  137.00),   # 1 order, 2×49 + 1×39
    ("2024-02", "Books",       1,  147.00),   # 1 order, 3×49
    ("2024-02", "Electronics", 1,  599.00),   # 1 order, 1×599
]
```

**Wait — check ordering:** month ASC, then revenue DESC within month:
```python
[
    ("2024-01", "Electronics", 1,  999.00),   # 2024-01, revenue 999 > 137
    ("2024-01", "Books",       1,  137.00),
    ("2024-02", "Electronics", 1,  599.00),   # 2024-02, revenue 599 > 147
    ("2024-02", "Books",       1,  147.00),
]
```

**Perfect query:**
```sql
SELECT
    strftime('%Y-%m', o.order_date) AS month,
    cat.name                        AS category,
    COUNT(DISTINCT o.id)            AS order_count,
    SUM(oi.quantity * p.price)      AS total_revenue
FROM order_items oi
JOIN products p   ON oi.product_id = p.id
JOIN categories cat ON p.category_id = cat.id
JOIN orders o     ON oi.order_id = o.id
WHERE strftime('%Y', o.order_date) = '2024'
GROUP BY month, cat.id
ORDER BY month ASC, total_revenue DESC;
```

**Max steps:** 7  
**Pass threshold:** reward >= 0.95

---

## Reward Function — Full Specification

### Design principles
1. **Never binary** — always partial credit between 0.0 and 1.0
2. **Penalize errors but not harshly** — -0.05 for syntax error, not -1.0
3. **Reward improvement** — agent that gets 50% right should score ~0.4, not 0.0
4. **Transparent** — return a breakdown dict so the agent knows what to fix

### Step reward formula

```
reward = execute_bonus + column_score + row_score + value_score + efficiency_bonus

Where:
  execute_bonus    = 0.10  if query ran without error, else -0.05
  column_score     = 0.20  × (correct columns / expected columns)
  row_score        = 0.20  × min(1.0, correct_row_count / expected_row_count)
  value_score      = 0.40  × F1(result_set, expected_set)
  efficiency_bonus = 0.10  if query does NOT use SELECT * AND selects only needed columns

Final clamp: reward = max(-0.10, min(1.0, reward))
```

### F1 score for value matching

```python
def f1_score(result_set, expected_set):
    if not result_set and not expected_set:
        return 1.0
    if not result_set or not expected_set:
        return 0.0
    intersection = result_set & expected_set
    precision = len(intersection) / len(result_set)
    recall    = len(intersection) / len(expected_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
```

### Feedback messages (what agent reads)

| Situation | Feedback message |
|-----------|-----------------|
| Perfect match | "Perfect! Exact match. Score: 1.00" |
| Query syntax error | "SQL Error: {error}. Check your syntax near line X." |
| Empty result | "Query ran but returned 0 rows. Check your WHERE clause or JOIN condition." |
| Wrong columns | "Got {n} columns, expected {m}. Check your SELECT clause." |
| Correct columns, wrong values | "Columns correct but {pct}% of values match. Check your filters or aggregation." |
| Over-fetching rows | "Too many rows returned ({n} vs expected {m}). Check your WHERE/HAVING clause." |
| Very close | "Very close! {pct}% match. Check column ordering or data type casting." |

---

## Episode Flow

```
reset(task="select_basics")
  → fresh SQLite in-memory DB created
  → task schema + seed data loaded
  → returns SqlObservation(task_description, schema_info, query_result=[], ...)

step(SqlAction(sql_query="SELECT ..."))
  → execute query against in-memory DB
  → grade result vs expected
  → return SqlObservation(query_result=rows, feedback=msg, reward=score, ...)
  → done = True if reward >= 0.95 OR step_count >= max_steps

close()
  → SQLite connection closed
  → container memory freed
```

---

## Key Implementation Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Database engine | SQLite in-memory | Zero setup, fast, fully isolated per session |
| Concurrency | `SUPPORTS_CONCURRENT_SESSIONS = True` | Each WebSocket gets its own `SqlEnvironment` instance with its own DB |
| Task selection | Via `reset(task="task_name")` kwargs | Standard OpenEnv pattern, compatible with inference.py |
| Partial rewards | F1 on result set | Gives gradient signal for RL training, not just pass/fail |
| Timeout | 5 seconds per query | Prevents infinite loops or full-table scans on large seeds |
| Error handling | Catch all exceptions, return -0.05 reward | Never crash the server, always return valid observation |

---

## Files and What Each One Does

```
sql_env/
├── models.py              ← SqlAction, SqlObservation (Pydantic models)
├── client.py              ← SqlEnv client (WebSocket, inherits EnvClient)
├── __init__.py            ← Exports SqlEnv, SqlAction, SqlObservation
├── openenv.yaml           ← OpenEnv manifest (spec_version, name, app, port)
├── pyproject.toml         ← Dependencies and package config
├── inference.py           ← Baseline agent script (MUST be here at root)
└── server/
    ├── sql_environment.py ← Core logic: TASKS dict, SqlEnvironment class
    ├── app.py             ← FastAPI app via create_app()
    ├── requirements.txt   ← pip deps for Docker
    ├── Dockerfile         ← Container definition
    └── __init__.py        ← Exports SqlEnvironment
```

---

## What to Implement in Each File (Summary for Phase 3)

| File | What goes in it |
|------|----------------|
| `models.py` | `SqlAction(sql_query: str)` and `SqlObservation(...)` as Pydantic models inheriting from `Action` and `Observation` |
| `server/sql_environment.py` | `TASKS` dict with all 3 task definitions + `SqlEnvironment` class with `reset()`, `step()`, `_grade()`, `state` |
| `server/app.py` | `create_app(SqlEnvironment, SqlAction, SqlObservation, ...)` — 10 lines |
| `server/__init__.py` | `from .sql_environment import SqlEnvironment` |
| `client.py` | `SqlEnv(EnvClient[SqlAction, SqlObservation, State])` with `_step_payload`, `_parse_result`, `_parse_state` |
| `__init__.py` | `from .client import SqlEnv` and `from .models import SqlAction, SqlObservation` |
| `openenv.yaml` | `spec_version: 1`, `name: sql_env`, `app: server.app:app`, `port: 8000` |
| `pyproject.toml` | Already scaffolded — just verify dependencies |
| `server/requirements.txt` | `openenv-core[core]>=0.2.2`, `fastapi>=0.115.0`, `uvicorn>=0.24.0` |
| `server/Dockerfile` | python:3.11-slim base, copy files, set PYTHONPATH, CMD uvicorn |
| `inference.py` | Loop over 3 tasks, call reset+step, print [START]/[STEP]/[END] format |
| `README.md` | HF Space YAML frontmatter + description, schemas, tasks, baseline scores |

---

*Design complete. Move to Phase 3 only after reading this document fully.*