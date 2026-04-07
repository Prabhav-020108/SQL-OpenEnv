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

SQL query writing is a task humans do every day. Training agents on this
environment directly enables automation of database querying, data analysis
pipelines, and business intelligence workflows. Unlike code generation
benchmarks, SQL has deterministic correctness — the result set either matches
or it doesn't — making grading reliable and reproducible. This is ideal for RL
training where reward signal must be trustworthy.

## Architecture
inference.py (LLM agent)
│  WebSocket /ws
▼
FastAPI Server  (server/app.py)
│
▼
SqlEnvironment  (server/sql_environment.py)
├── SQLite in-memory DB per session
├── Grader logic (F1 scoring)
└── Reward computation

## Action Space
```python
SqlAction(sql_query: str)
# Example:
SqlAction(sql_query="SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name")
```

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `task_description` | str | Natural language task to solve |
| `schema_info` | str | Full DDL (CREATE TABLE statements) |
| `query_result` | list | Rows returned by the agent's query |
| `error_message` | str | SQL error string if query failed |
| `feedback` | str | Human-readable grader feedback |
| `score_breakdown` | dict | Partial scores per component |
| `attempts_remaining` | int | Steps left in this episode |

## Tasks

| Task | Difficulty | Description |
|------|------------|-------------|
| `select_basics` | Easy | SELECT + WHERE with ORDER BY |
| `aggregate_filter` | Medium | GROUP BY + HAVING + JOIN |
| `multi_join` | Hard | 4-table JOIN with month extraction and aggregation |

## Reward Function
+0.10  Query executes without syntax error
+0.20  Correct number of columns
+0.20  Correct row count
+0.40  Correct values (F1 score on result set)
+0.10  Efficiency bonus (no SELECT *)
──────
1.00  Maximum reward per step
-0.05  Syntax error penalty

## Baseline Scores
[START] task=select_basics env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=aggregate_filter env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT c.name, SUM(o.amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id G reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=multi_join env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT      strftime('%Y-%m', orders.order_date) AS month,     categories.name AS category_name,     reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00

## Quick Start
```python
from sql_env import SqlEnv, SqlAction

async with SqlEnv(base_url="https://Codexzzz-sql-env.hf.space") as env:
    result = await env.reset()
    result = await env.step(SqlAction(sql_query="SELECT name FROM customers"))
    print(result.observation.feedback)
```

## Setup
```bash
pip install git+https://huggingface.co/spaces/Codexzzz/sql-env
```

## Environment Variables for inference.py
API_BASE_URL   — LLM API endpoint
MODEL_NAME     — model identifier
HF_TOKEN       — Hugging Face token
IMAGE_NAME     — local Docker image name