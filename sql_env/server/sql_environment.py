import sqlite3
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SqlAction, SqlObservation
except ImportError:
    from models import SqlAction, SqlObservation

# ─────────────────────────────────────────────
# TASK DEFINITIONS
# ─────────────────────────────────────────────

TASKS = {
    "select_basics": {
        "description": (
            "Find the full name and email address of all customers who live in 'New York'. "
            "Return results sorted alphabetically by name (A to Z)."
        ),
        "schema": """
CREATE TABLE customers (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    email     TEXT    NOT NULL,
    city      TEXT    NOT NULL,
    age       INTEGER
);
""",
        "seed_sql": """
INSERT INTO customers VALUES (1, 'Alice Brown',  'alice@email.com',  'New York', 28);
INSERT INTO customers VALUES (2, 'Bob Smith',    'bob@email.com',    'New York', 34);
INSERT INTO customers VALUES (3, 'Carol Davis',  'carol@email.com',  'Chicago',  25);
INSERT INTO customers VALUES (4, 'David Lee',    'david@email.com',  'New York', 41);
INSERT INTO customers VALUES (5, 'Eve Wilson',   'eve@email.com',    'Boston',   30);
""",
        "expected": [
            ("Alice Brown",  "alice@email.com"),
            ("Bob Smith",    "bob@email.com"),
            ("David Lee",    "david@email.com"),
        ],
        "max_steps": 5,
    },

    "aggregate_filter": {
        "description": (
            "Find each customer who has placed MORE THAN 2 orders. "
            "Return their name and total amount spent (sum of all their order amounts). "
            "Sort by total amount spent, highest first."
        ),
        "schema": """
CREATE TABLE customers (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    order_date  TEXT    NOT NULL
);
""",
        "seed_sql": """
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
""",
        "expected": [
            ("Alice Brown", 405.50),
            ("Bob Smith",   300.00),
        ],
        "max_steps": 5,
    },

    "multi_join": {
        "description": (
            "Generate a monthly revenue report for the year 2024. "
            "For each month and product category return: "
            "month in 'YYYY-MM' format, category name, "
            "number of distinct orders, and total revenue (quantity × price). "
            "Order by month ascending, then total revenue descending within each month. "
            "Exclude any data from outside 2024."
        ),
        "schema": """
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL
);
CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    category_id INTEGER NOT NULL,
    price       REAL    NOT NULL
);
CREATE TABLE orders (
    id         INTEGER PRIMARY KEY,
    order_date TEXT    NOT NULL
);
CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL
);
""",
        "seed_sql": """
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
INSERT INTO orders VALUES (5, '2023-12-01');
INSERT INTO order_items VALUES (1, 1, 1, 1);
INSERT INTO order_items VALUES (2, 2, 3, 2);
INSERT INTO order_items VALUES (3, 2, 4, 1);
INSERT INTO order_items VALUES (4, 3, 2, 1);
INSERT INTO order_items VALUES (5, 4, 3, 3);
INSERT INTO order_items VALUES (6, 5, 1, 1);
""",
        "expected": [
            ("2024-01", "Electronics", 1,  999.00),
            ("2024-01", "Books",       1,  137.00),
            ("2024-02", "Electronics", 1,  599.00),
            ("2024-02", "Books",       1,  147.00),
        ],
        "max_steps": 7,
    },
}


# ─────────────────────────────────────────────
# ENVIRONMENT CLASS
# ─────────────────────────────────────────────

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
            feedback="Episode started. Write a SQL query to solve the task above.",
            score_breakdown={},
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
            reward, feedback, breakdown = self._grade(result, task["expected"], action.sql_query)
            error_msg = ""
        except Exception as exc:
            reward     = -0.05
            result     = []
            feedback   = f"SQL Error: {exc}. Fix your syntax and try again."
            breakdown  = {"execute": -0.05}
            error_msg  = str(exc)

        done = reward >= 0.95 or attempts_remaining <= 0

        return SqlObservation(
            task_description=task["description"],
            schema_info=task["schema"].strip(),
            query_result=[list(r) for r in result],
            error_message=error_msg,
            feedback=feedback,
            score_breakdown=breakdown,
            attempts_remaining=max(0, attempts_remaining),
            done=done,
            reward=float(max(-0.10, min(1.0, reward))),
        )

    # ── Grader ──────────────────────────────

    def _grade(self, result, expected, sql_query: str):
        breakdown = {}

        # 1. Execute bonus (already succeeded if we're here)
        breakdown["execute"] = 0.10

        if not result:
            feedback = "Query ran but returned 0 rows. Check your WHERE clause or JOIN conditions."
            total = 0.10
            return total, feedback, breakdown

        result_set   = set(tuple(r) for r in result)
        expected_set = set(tuple(e) for e in expected)

        # 2. Column score — compare number of columns per row
        result_cols   = len(result[0])   if result   else 0
        expected_cols = len(expected[0]) if expected else 0
        col_score = 0.20 if result_cols == expected_cols else 0.20 * (min(result_cols, expected_cols) / max(result_cols, expected_cols, 1))
        breakdown["columns"] = round(col_score, 3)

        # 3. Row count score
        row_ratio  = min(1.0, len(result) / max(len(expected), 1))
        row_score  = 0.20 * row_ratio
        breakdown["rows"] = round(row_score, 3)

        # 4. Value F1 score
        f1         = self._f1(result_set, expected_set)
        val_score  = 0.40 * f1
        breakdown["values"] = round(val_score, 3)

        # 5. Efficiency bonus — penalise SELECT *
        uses_star  = "select *" in sql_query.lower().replace(" ", "")
        eff_score  = 0.0 if uses_star else 0.10
        breakdown["efficiency"] = eff_score

        total = breakdown["execute"] + col_score + row_score + val_score + eff_score

        # Human-readable feedback
        pct = int(f1 * 100)
        if f1 >= 1.0 and col_score >= 0.20 and row_score >= 0.20:
            feedback = "Perfect! Exact match." if not uses_star else "Correct result but avoid SELECT * — target only needed columns."
        elif f1 >= 0.8:
            feedback = f"Very close! {pct}% of values match. Check column ordering or data type casting."
        elif f1 >= 0.5:
            feedback = f"Partial match: {pct}% correct. Re-read the task description and check your filters."
        elif result_cols != expected_cols:
            feedback = f"Got {result_cols} column(s), expected {expected_cols}. Fix your SELECT clause."
        else:
            feedback = f"Mostly incorrect ({pct}% match). Start from the schema and re-read the task."

        return round(total, 3), feedback, breakdown

    @staticmethod
    def _f1(result_set, expected_set):
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

    @property
    def state(self) -> State:
        return self._state