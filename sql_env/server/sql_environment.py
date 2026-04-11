# import json
# import sqlite3
# import tempfile
# import threading
# from pathlib import Path
# from uuid import uuid4

# from openenv.core.env_server.interfaces import Environment
# from openenv.core.env_server.types import State

# try:
#     from ..models import SqlAction, SqlObservation
# except ImportError:
#     from models import SqlAction, SqlObservation


# # ─────────────────────────────────────────────────────────────────────────────
# # MODULE-LEVEL SESSION STORE
# #
# # The OpenEnv HTTP server creates a NEW SqlEnvironment instance on every
# # request, so self._episode_id would always be None in step().
# # Storing sessions at module level (shared across all instances in the same
# # process) fixes this. We also persist to disk so the DB survives a restart.
# # ─────────────────────────────────────────────────────────────────────────────

# _MEMORY_SESSIONS: dict = {}   # { episode_id -> session_dict, "__latest__" -> episode_id }
# _SESSION_DIR = Path(tempfile.gettempdir()) / "openenv_sql_env"
# _SESSION_DIR.mkdir(parents=True, exist_ok=True)


# # ─────────────────────────────────────────────────────────────────────────────
# # TASK DEFINITIONS
# # ─────────────────────────────────────────────────────────────────────────────

# TASKS = {
#     "select_basics": {
#         "description": (
#             "Find the full name and email address of all customers who live in 'New York'. "
#             "Return results sorted alphabetically by name (A to Z)."
#         ),
#         "schema": (
#             "CREATE TABLE customers (\n"
#             "    id        INTEGER PRIMARY KEY,\n"
#             "    name      TEXT    NOT NULL,\n"
#             "    email     TEXT    NOT NULL,\n"
#             "    city      TEXT    NOT NULL,\n"
#             "    age       INTEGER\n"
#             ");"
#         ),
#         "seed_sql": """
# INSERT INTO customers VALUES (1, 'Alice Brown',  'alice@email.com',  'New York', 28);
# INSERT INTO customers VALUES (2, 'Bob Smith',    'bob@email.com',    'New York', 34);
# INSERT INTO customers VALUES (3, 'Carol Davis',  'carol@email.com',  'Chicago',  25);
# INSERT INTO customers VALUES (4, 'David Lee',    'david@email.com',  'New York', 41);
# INSERT INTO customers VALUES (5, 'Eve Wilson',   'eve@email.com',    'Boston',   30);
# """,
#         "expected": [
#             ("Alice Brown", "alice@email.com"),
#             ("Bob Smith",   "bob@email.com"),
#             ("David Lee",   "david@email.com"),
#         ],
#         "max_steps": 5,
#     },

#     "aggregate_filter": {
#         "description": (
#             "Find each customer who has placed MORE THAN 2 orders. "
#             "Return their name and total amount spent (sum of all their order amounts). "
#             "Sort by total amount spent, highest first."
#         ),
#         "schema": (
#             "CREATE TABLE customers (\n"
#             "    id    INTEGER PRIMARY KEY,\n"
#             "    name  TEXT    NOT NULL\n"
#             ");\n"
#             "CREATE TABLE orders (\n"
#             "    id          INTEGER PRIMARY KEY,\n"
#             "    customer_id INTEGER NOT NULL,\n"
#             "    amount      REAL    NOT NULL,\n"
#             "    order_date  TEXT    NOT NULL\n"
#             ");"
#         ),
#         "seed_sql": """
# INSERT INTO customers VALUES (1, 'Alice Brown');
# INSERT INTO customers VALUES (2, 'Bob Smith');
# INSERT INTO customers VALUES (3, 'Carol Davis');
# INSERT INTO orders VALUES (1,  1, 120.00, '2024-01-10');
# INSERT INTO orders VALUES (2,  1,  85.50, '2024-01-15');
# INSERT INTO orders VALUES (3,  1, 200.00, '2024-02-01');
# INSERT INTO orders VALUES (4,  2,  45.00, '2024-01-20');
# INSERT INTO orders VALUES (5,  2,  95.00, '2024-02-10');
# INSERT INTO orders VALUES (6,  2, 160.00, '2024-02-15');
# INSERT INTO orders VALUES (7,  3,  30.00, '2024-01-05');
# """,
#         "expected": [
#             ("Alice Brown", 405.50),
#             ("Bob Smith",   300.00),
#         ],
#         "max_steps": 5,
#     },

#     "multi_join": {
#         "description": (
#             "Generate a monthly revenue report for the year 2024. "
#             "For each month and product category return: "
#             "month in 'YYYY-MM' format, category name, "
#             "number of distinct orders that included products from that category, "
#             "and total revenue (quantity x product price, summed across all items). "
#             "Order by month ascending, then total revenue descending within each month. "
#             "Only include data from 2024 - exclude records from other years."
#         ),
#         "schema": (
#             "CREATE TABLE categories (\n"
#             "    id    INTEGER PRIMARY KEY,\n"
#             "    name  TEXT    NOT NULL\n"
#             ");\n"
#             "CREATE TABLE products (\n"
#             "    id          INTEGER PRIMARY KEY,\n"
#             "    name        TEXT    NOT NULL,\n"
#             "    category_id INTEGER NOT NULL,\n"
#             "    price       REAL    NOT NULL\n"
#             ");\n"
#             "CREATE TABLE orders (\n"
#             "    id         INTEGER PRIMARY KEY,\n"
#             "    order_date TEXT    NOT NULL\n"
#             ");\n"
#             "CREATE TABLE order_items (\n"
#             "    id         INTEGER PRIMARY KEY,\n"
#             "    order_id   INTEGER NOT NULL,\n"
#             "    product_id INTEGER NOT NULL,\n"
#             "    quantity   INTEGER NOT NULL\n"
#             ");"
#         ),
#         "seed_sql": """
# INSERT INTO categories VALUES (1, 'Electronics');
# INSERT INTO categories VALUES (2, 'Books');
# INSERT INTO products VALUES (1, 'Laptop',       1, 999.00);
# INSERT INTO products VALUES (2, 'Phone',        1, 599.00);
# INSERT INTO products VALUES (3, 'Python Book',  2,  49.00);
# INSERT INTO products VALUES (4, 'SQL Handbook', 2,  39.00);
# INSERT INTO orders VALUES (1, '2024-01-15');
# INSERT INTO orders VALUES (2, '2024-01-20');
# INSERT INTO orders VALUES (3, '2024-02-10');
# INSERT INTO orders VALUES (4, '2024-02-28');
# INSERT INTO orders VALUES (5, '2023-12-01');
# INSERT INTO order_items VALUES (1, 1, 1, 1);
# INSERT INTO order_items VALUES (2, 2, 3, 2);
# INSERT INTO order_items VALUES (3, 2, 4, 1);
# INSERT INTO order_items VALUES (4, 3, 2, 1);
# INSERT INTO order_items VALUES (5, 4, 3, 3);
# INSERT INTO order_items VALUES (6, 5, 1, 1);
# """,
#         "expected": [
#             ("2024-01", "Electronics", 1,  999.00),
#             ("2024-01", "Books",       1,  137.00),
#             ("2024-02", "Electronics", 1,  599.00),
#             ("2024-02", "Books",       1,  147.00),
#         ],
#         "max_steps": 7,
#     },

#     "data_anomalies": {
#         "description": (
#             "Find data quality issues in the customers table. "
#             "Return: the type of issue as a string and the count of affected rows. "
#             "The three issue types to check are:\n"
#             "  1. 'duplicate_email' - email addresses that appear more than once\n"
#             "  2. 'invalid_age' - age values that are NULL, negative, or greater than 150\n"
#             "  3. 'null_name' - rows where name is NULL\n"
#             "Return all three rows ordered alphabetically by issue type. "
#             "Use UNION ALL to combine the three checks into one result set."
#         ),
#         "schema": (
#             "CREATE TABLE customers (\n"
#             "    id      INTEGER PRIMARY KEY,\n"
#             "    name    TEXT,\n"
#             "    email   TEXT,\n"
#             "    age     INTEGER\n"
#             ");"
#         ),
#         "seed_sql": """
# INSERT INTO customers VALUES (1, 'Alice', 'a@test.com',  25);
# INSERT INTO customers VALUES (2,  NULL,   'b@test.com',  30);
# INSERT INTO customers VALUES (3, 'Carol', 'a@test.com',  22);
# INSERT INTO customers VALUES (4, 'Dave',  'd@test.com',  -5);
# INSERT INTO customers VALUES (5, 'Eve',   'e@test.com', 200);
# """,
#         "expected": [
#             ("duplicate_email", 2),
#             ("invalid_age",     2),
#             ("null_name",       1),
#         ],
#         "max_steps": 7,
#     },
# }


# # ─────────────────────────────────────────────────────────────────────────────
# # THREAD-BASED QUERY TIMEOUT  (cross-platform, no SIGALRM)
# # ─────────────────────────────────────────────────────────────────────────────

# def _run_query_with_timeout(db_path: Path, sql: str, timeout_seconds: int = 5):
#     """Execute SQL in a daemon thread with a hard timeout.
#     Returns (rows, error_or_None).
#     """
#     result_box: list = [None]
#     error_box:  list = [None]

#     def _target():
#         conn = None
#         try:
#             conn = sqlite3.connect(str(db_path))
#             cursor = conn.execute(sql)
#             result_box[0] = cursor.fetchall()
#         except Exception as exc:
#             error_box[0] = exc
#         finally:
#             if conn:
#                 try:
#                     conn.close()
#                 except Exception:
#                     pass

#     t = threading.Thread(target=_target, daemon=True)
#     t.start()
#     t.join(timeout=timeout_seconds)

#     if t.is_alive():
#         return None, TimeoutError(f"Query exceeded {timeout_seconds}s — avoid full table scans.")
#     if error_box[0] is not None:
#         return None, error_box[0]
#     return result_box[0], None


# # ─────────────────────────────────────────────────────────────────────────────
# # ENVIRONMENT CLASS
# # ─────────────────────────────────────────────────────────────────────────────

# class SqlEnvironment(Environment):
#     SUPPORTS_CONCURRENT_SESSIONS = True

#     def __init__(self):
#         self._episode_id: str | None = None
#         self._state = State(episode_id=str(uuid4()), step_count=0)

#     # ── File helpers (best-effort persistence) ────────────────────────────────

#     def _db_path(self, episode_id: str) -> Path:
#         return _SESSION_DIR / f"{episode_id}.sqlite3"

#     def _meta_path(self, episode_id: str) -> Path:
#         return _SESSION_DIR / f"session_{episode_id}.json"

#     def _save_session_file(self, session: dict) -> None:
#         try:
#             path = self._meta_path(session["episode_id"])
#             tmp  = path.with_suffix(".tmp")
#             with tmp.open("w", encoding="utf-8") as f:
#                 json.dump(session, f)
#             tmp.replace(path)
#         except Exception:
#             pass  # file persistence is best-effort; memory is primary

#     def _load_session_file(self, episode_id: str) -> dict:
#         try:
#             path = self._meta_path(episode_id)
#             if not path.exists():
#                 return {}
#             with path.open("r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception:
#             return {}

#     # ── DB initialisation ─────────────────────────────────────────────────────

#     def _initialise_db(self, task_name: str, db_path: Path) -> None:
#         task = TASKS[task_name]
#         if db_path.exists():
#             try:
#                 db_path.unlink()
#             except OSError:
#                 pass
#         conn = sqlite3.connect(str(db_path))
#         try:
#             conn.executescript(task["schema"])
#             conn.executescript(task["seed_sql"])
#             conn.commit()
#         finally:
#             conn.close()

#     # ── Session resolution ────────────────────────────────────────────────────

#     def _resolve_session(self) -> dict:
#         """Find the session for the current episode.

#         Priority order:
#           1. self._episode_id  (WebSocket / persistent instance where reset was called)
#           2. _MEMORY_SESSIONS["__latest__"]  (HTTP, same process, new instance per request)
#           3. Disk fallback for the resolved episode_id  (container restart recovery)
#         """
#         episode_id = self._episode_id or _MEMORY_SESSIONS.get("__latest__")
#         if not episode_id:
#             return {}

#         session = _MEMORY_SESSIONS.get(episode_id, {})
#         if not session:
#             session = self._load_session_file(episode_id)
#             if session:
#                 _MEMORY_SESSIONS[episode_id] = session

#         if session:
#             self._episode_id = episode_id  # pin for this request

#         return session

#     # ── reset() ──────────────────────────────────────────────────────────────

#     def reset(self, seed=None, episode_id=None, **kwargs) -> SqlObservation:
#         task_name = kwargs.get("task", "select_basics")
#         if task_name not in TASKS:
#             task_name = "select_basics"

#         task    = TASKS[task_name]
#         new_id  = episode_id or str(uuid4())
#         db_path = self._db_path(new_id)

#         self._initialise_db(task_name, db_path)

#         session = {
#             "episode_id": new_id,
#             "task_name":  task_name,
#             "db_path":    str(db_path),
#             "step_count": 0,
#         }

#         # Primary store: module-level dict (survives across instances in same process)
#         _MEMORY_SESSIONS[new_id]       = session
#         _MEMORY_SESSIONS["__latest__"] = new_id
#         # Secondary store: disk (survives container restart)
#         self._save_session_file(session)

#         self._episode_id = new_id
#         self._state      = State(episode_id=new_id, step_count=0)

#         return SqlObservation(
#             task_description   = task["description"],
#             schema_info        = task["schema"],
#             query_result       = [],
#             error_message      = "",
#             feedback           = "Episode started. Write a SQL query to solve the task above.",
#             score_breakdown    = {},
#             attempts_remaining = task["max_steps"],
#             done               = False,
#             reward             = 0.0,
#         )

#     # ── step() ────────────────────────────────────────────────────────────────

#     def step(self, action: SqlAction) -> SqlObservation:
#         session = self._resolve_session()

#         if not session:
#             return SqlObservation(
#                 task_description   = "",
#                 schema_info        = "",
#                 query_result       = [],
#                 error_message      = "No active session. Call /reset first.",
#                 feedback           = "No active session — call /reset before /step.",
#                 score_breakdown    = {"execute": -0.05},
#                 attempts_remaining = 0,
#                 done               = True,
#                 reward             = -0.05,
#             )

#         task_name = session.get("task_name", "select_basics")
#         if task_name not in TASKS:
#             task_name = "select_basics"

#         db_path = Path(session.get("db_path") or str(self._db_path(session["episode_id"])))

#         # Re-seed if the DB file was lost (e.g. tmpfs wipe on restart)
#         if not db_path.exists():
#             self._initialise_db(task_name, db_path)

#         # Advance step counter
#         step_count            = int(session.get("step_count", 0)) + 1
#         session["step_count"] = step_count
#         _MEMORY_SESSIONS[self._episode_id] = session
#         self._save_session_file(session)

#         self._state = State(
#             episode_id = self._episode_id or str(uuid4()),
#             step_count = step_count,
#         )

#         task               = TASKS[task_name]
#         attempts_remaining = task["max_steps"] - step_count

#         rows, err = _run_query_with_timeout(db_path, action.sql_query, timeout_seconds=5)

#         if isinstance(err, TimeoutError):
#             reward    = -0.10
#             rows      = []
#             feedback  = str(err)
#             breakdown = {"execute": -0.10}
#             error_msg = str(err)
#         elif err is not None:
#             reward    = -0.05
#             rows      = []
#             feedback  = f"SQL Error: {err}. Fix your syntax and try again."
#             breakdown = {"execute": -0.05}
#             error_msg = str(err)
#         else:
#             reward, feedback, breakdown = self._grade(rows, task["expected"], action.sql_query)
#             error_msg = ""

#         done = reward >= 0.95 or attempts_remaining <= 0

#         return SqlObservation(
#             task_description   = task["description"],
#             schema_info        = task["schema"],
#             query_result       = [list(r) for r in (rows or [])],
#             error_message      = error_msg,
#             feedback           = feedback,
#             score_breakdown    = breakdown,
#             attempts_remaining = max(0, attempts_remaining),
#             done               = done,
#             reward             = float(max(-0.10, min(1.0, reward))),
#         )

#     # ── Grader ────────────────────────────────────────────────────────────────

#     def _grade(self, result: list, expected: list, sql_query: str):
#         breakdown: dict = {"execute": 0.10}

#         if not result:
#             return (
#                 0.10,
#                 "Query ran but returned 0 rows. Check your WHERE clause or JOIN conditions.",
#                 breakdown,
#             )

#         result_set   = set(tuple(r) for r in result)
#         expected_set = set(tuple(e) for e in expected)

#         result_cols   = len(result[0])   if result   else 0
#         expected_cols = len(expected[0]) if expected else 0
#         col_score = (
#             0.20 if result_cols == expected_cols
#             else 0.20 * (min(result_cols, expected_cols) / max(result_cols, expected_cols, 1))
#         )
#         breakdown["columns"] = round(col_score, 3)

#         row_score = 0.20 * min(1.0, len(result) / max(len(expected), 1))
#         breakdown["rows"] = round(row_score, 3)

#         f1        = self._f1(result_set, expected_set)
#         val_score = 0.40 * f1
#         breakdown["values"] = round(val_score, 3)

#         uses_star = "select*" in sql_query.lower().replace(" ", "")
#         eff_score = 0.0 if uses_star else 0.10
#         breakdown["efficiency"] = eff_score

#         total = breakdown["execute"] + col_score + row_score + val_score + eff_score
#         pct   = int(f1 * 100)

#         if f1 >= 1.0 and col_score >= 0.20 and row_score >= 0.20:
#             feedback = (
#                 "Perfect! Exact match."
#                 if not uses_star
#                 else "Correct result but avoid SELECT * — target only needed columns."
#             )
#         elif result_cols > expected_cols:
#             feedback = (
#                 f"Too many columns ({result_cols} returned, {expected_cols} expected). "
#                 "Remove extra columns from SELECT."
#             )
#         elif result_cols < expected_cols:
#             feedback = (
#                 f"Too few columns ({result_cols} returned, {expected_cols} expected). "
#                 "Add missing columns to SELECT."
#             )
#         elif len(result) > len(expected) * 1.5:
#             feedback = (
#                 f"Too many rows ({len(result)} vs {len(expected)} expected). "
#                 "Check your WHERE or HAVING — a filter may be missing."
#             )
#         elif len(result) < len(expected):
#             feedback = (
#                 f"Too few rows ({len(result)} vs {len(expected)} expected). "
#                 "Check your JOIN or WHERE — some matching rows are being excluded."
#             )
#         elif f1 >= 0.8:
#             feedback = f"Very close! {pct}% of values match. Check column ordering or data type casting."
#         elif f1 >= 0.5:
#             feedback = f"Partial match: {pct}% correct. Re-read the task and check your filters."
#         else:
#             feedback = f"Mostly incorrect ({pct}% match). Start from the schema and re-read the task."

#         return round(total, 3), feedback, breakdown

#     @staticmethod
#     def _f1(result_set: set, expected_set: set) -> float:
#         if not result_set and not expected_set:
#             return 1.0
#         if not result_set or not expected_set:
#             return 0.0
#         intersection = result_set & expected_set
#         precision    = len(intersection) / len(result_set)
#         recall       = len(intersection) / len(expected_set)
#         if precision + recall == 0:
#             return 0.0
#         return 2 * precision * recall / (precision + recall)

#     @property
#     def state(self) -> State:
#         return self._state


import json
import sqlite3
import tempfile
import threading
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SqlAction, SqlObservation
except ImportError:
    from models import SqlAction, SqlObservation


# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL SESSION STORE
#
# The OpenEnv HTTP server creates a NEW SqlEnvironment instance on every
# request, so self._episode_id would always be None in step().
# Storing sessions at module level (shared across all instances in the same
# process) fixes this. We also persist to disk so the DB survives a restart.
# ─────────────────────────────────────────────────────────────────────────────

_MEMORY_SESSIONS: dict = {}   # { episode_id -> session_dict, "__latest__" -> episode_id }
_SESSION_DIR = Path(tempfile.gettempdir()) / "openenv_sql_env"
_SESSION_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# TASK DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

TASKS = {
    "select_basics": {
        "description": (
            "Find the full name and email address of all customers who live in 'New York'. "
            "Return results sorted alphabetically by name (A to Z)."
        ),
        "schema": (
            "CREATE TABLE customers (\n"
            "    id        INTEGER PRIMARY KEY,\n"
            "    name      TEXT    NOT NULL,\n"
            "    email     TEXT    NOT NULL,\n"
            "    city      TEXT    NOT NULL,\n"
            "    age       INTEGER\n"
            ");"
        ),
        "seed_sql": """
INSERT INTO customers VALUES (1, 'Alice Brown',  'alice@email.com',  'New York', 28);
INSERT INTO customers VALUES (2, 'Bob Smith',    'bob@email.com',    'New York', 34);
INSERT INTO customers VALUES (3, 'Carol Davis',  'carol@email.com',  'Chicago',  25);
INSERT INTO customers VALUES (4, 'David Lee',    'david@email.com',  'New York', 41);
INSERT INTO customers VALUES (5, 'Eve Wilson',   'eve@email.com',    'Boston',   30);
""",
        "expected": [
            ("Alice Brown", "alice@email.com"),
            ("Bob Smith",   "bob@email.com"),
            ("David Lee",   "david@email.com"),
        ],
        "max_steps": 5,
    },

    "aggregate_filter": {
        "description": (
            "Find each customer who has placed MORE THAN 2 orders. "
            "Return their name and total amount spent (sum of all their order amounts). "
            "Sort by total amount spent, highest first."
        ),
        "schema": (
            "CREATE TABLE customers (\n"
            "    id    INTEGER PRIMARY KEY,\n"
            "    name  TEXT    NOT NULL\n"
            ");\n"
            "CREATE TABLE orders (\n"
            "    id          INTEGER PRIMARY KEY,\n"
            "    customer_id INTEGER NOT NULL,\n"
            "    amount      REAL    NOT NULL,\n"
            "    order_date  TEXT    NOT NULL\n"
            ");"
        ),
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
            "number of distinct orders that included products from that category, "
            "and total revenue (quantity x product price, summed across all items). "
            "Order by month ascending, then total revenue descending within each month. "
            "Only include data from 2024 - exclude records from other years."
        ),
        "schema": (
            "CREATE TABLE categories (\n"
            "    id    INTEGER PRIMARY KEY,\n"
            "    name  TEXT    NOT NULL\n"
            ");\n"
            "CREATE TABLE products (\n"
            "    id          INTEGER PRIMARY KEY,\n"
            "    name        TEXT    NOT NULL,\n"
            "    category_id INTEGER NOT NULL,\n"
            "    price       REAL    NOT NULL\n"
            ");\n"
            "CREATE TABLE orders (\n"
            "    id         INTEGER PRIMARY KEY,\n"
            "    order_date TEXT    NOT NULL\n"
            ");\n"
            "CREATE TABLE order_items (\n"
            "    id         INTEGER PRIMARY KEY,\n"
            "    order_id   INTEGER NOT NULL,\n"
            "    product_id INTEGER NOT NULL,\n"
            "    quantity   INTEGER NOT NULL\n"
            ");"
        ),
        "seed_sql": """
INSERT INTO categories VALUES (1, 'Electronics');
INSERT INTO categories VALUES (2, 'Books');
INSERT INTO products VALUES (1, 'Laptop',       1, 999.00);
INSERT INTO products VALUES (2, 'Phone',        1, 599.00);
INSERT INTO products VALUES (3, 'Python Book',  2,  49.00);
INSERT INTO products VALUES (4, 'SQL Handbook', 2,  39.00);
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

    "data_anomalies": {
        "description": (
            "Find data quality issues in the customers table. "
            "Return: the type of issue as a string and the count of affected rows. "
            "The three issue types to check are:\n"
            "  1. 'duplicate_email' - email addresses that appear more than once\n"
            "  2. 'invalid_age' - age values that are NULL, negative, or greater than 150\n"
            "  3. 'null_name' - rows where name is NULL\n"
            "Return all three rows ordered alphabetically by issue type. "
            "Use UNION ALL to combine the three checks into one result set."
        ),
        "schema": (
            "CREATE TABLE customers (\n"
            "    id      INTEGER PRIMARY KEY,\n"
            "    name    TEXT,\n"
            "    email   TEXT,\n"
            "    age     INTEGER\n"
            ");"
        ),
        "seed_sql": """
INSERT INTO customers VALUES (1, 'Alice', 'a@test.com',  25);
INSERT INTO customers VALUES (2,  NULL,   'b@test.com',  30);
INSERT INTO customers VALUES (3, 'Carol', 'a@test.com',  22);
INSERT INTO customers VALUES (4, 'Dave',  'd@test.com',  -5);
INSERT INTO customers VALUES (5, 'Eve',   'e@test.com', 200);
""",
        "expected": [
            ("duplicate_email", 2),
            ("invalid_age",     2),
            ("null_name",       1),
        ],
        "max_steps": 7,
    },

    # ── NEW TASK ──────────────────────────────────────────────────────────────
    "window_functions": {
        "description": (
            "For each employee, calculate their salary rank within their department "
            "and the difference between their salary and their department's average salary. "
            "Return four columns in this exact order: "
            "employee name, department name, "
            "salary rank within the department (1 = highest paid, use RANK()), "
            "and the difference between their salary and the department average salary "
            "(rounded to 2 decimal places, positive means above average). "
            "Order results by department name ascending, then by rank ascending."
        ),
        "schema": (
            "CREATE TABLE departments (\n"
            "    id   INTEGER PRIMARY KEY,\n"
            "    name TEXT    NOT NULL\n"
            ");\n"
            "CREATE TABLE employees (\n"
            "    id            INTEGER PRIMARY KEY,\n"
            "    name          TEXT    NOT NULL,\n"
            "    department_id INTEGER NOT NULL,\n"
            "    salary        REAL    NOT NULL\n"
            ");"
        ),
        "seed_sql": """
INSERT INTO departments VALUES (1, 'Engineering');
INSERT INTO departments VALUES (2, 'Marketing');
INSERT INTO employees VALUES (1, 'Alice', 1, 90000);
INSERT INTO employees VALUES (2, 'Bob',   1, 80000);
INSERT INTO employees VALUES (3, 'Carol', 1, 85000);
INSERT INTO employees VALUES (4, 'Dave',  2, 70000);
INSERT INTO employees VALUES (5, 'Eve',   2, 75000);
INSERT INTO employees VALUES (6, 'Frank', 2, 65000);
""",
        "expected": [
            ("Alice", "Engineering", 1,  5000.0),
            ("Carol", "Engineering", 2,     0.0),
            ("Bob",   "Engineering", 3, -5000.0),
            ("Eve",   "Marketing",   1,  5000.0),
            ("Dave",  "Marketing",   2,     0.0),
            ("Frank", "Marketing",   3, -5000.0),
        ],
        "max_steps": 8,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# THREAD-BASED QUERY TIMEOUT  (cross-platform, no SIGALRM)
# ─────────────────────────────────────────────────────────────────────────────

def _run_query_with_timeout(db_path: Path, sql: str, timeout_seconds: int = 5):
    """Execute SQL in a daemon thread with a hard timeout.
    Returns (rows, error_or_None).
    """
    result_box: list = [None]
    error_box:  list = [None]

    def _target():
        conn = None
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute(sql)
            result_box[0] = cursor.fetchall()
        except Exception as exc:
            error_box[0] = exc
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout_seconds)

    if t.is_alive():
        return None, TimeoutError(f"Query exceeded {timeout_seconds}s — avoid full table scans.")
    if error_box[0] is not None:
        return None, error_box[0]
    return result_box[0], None


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SqlEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._episode_id: str | None = None
        self._state = State(episode_id=str(uuid4()), step_count=0)

    # ── File helpers (best-effort persistence) ────────────────────────────────

    def _db_path(self, episode_id: str) -> Path:
        return _SESSION_DIR / f"{episode_id}.sqlite3"

    def _meta_path(self, episode_id: str) -> Path:
        return _SESSION_DIR / f"session_{episode_id}.json"

    def _save_session_file(self, session: dict) -> None:
        try:
            path = self._meta_path(session["episode_id"])
            tmp  = path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(session, f)
            tmp.replace(path)
        except Exception:
            pass  # file persistence is best-effort; memory is primary

    def _load_session_file(self, episode_id: str) -> dict:
        try:
            path = self._meta_path(episode_id)
            if not path.exists():
                return {}
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ── DB initialisation ─────────────────────────────────────────────────────

    def _initialise_db(self, task_name: str, db_path: Path) -> None:
        task = TASKS[task_name]
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass
        conn = sqlite3.connect(str(db_path))
        try:
            conn.executescript(task["schema"])
            conn.executescript(task["seed_sql"])
            conn.commit()
        finally:
            conn.close()

    # ── Session resolution ────────────────────────────────────────────────────

    def _resolve_session(self) -> dict:
        """Find the session for the current episode.

        Priority order:
          1. self._episode_id  (WebSocket / persistent instance where reset was called)
          2. _MEMORY_SESSIONS["__latest__"]  (HTTP, same process, new instance per request)
          3. Disk fallback for the resolved episode_id  (container restart recovery)
        """
        episode_id = self._episode_id or _MEMORY_SESSIONS.get("__latest__")
        if not episode_id:
            return {}

        session = _MEMORY_SESSIONS.get(episode_id, {})
        if not session:
            session = self._load_session_file(episode_id)
            if session:
                _MEMORY_SESSIONS[episode_id] = session

        if session:
            self._episode_id = episode_id  # pin for this request

        return session

    # ── reset() ──────────────────────────────────────────────────────────────

    def reset(self, seed=None, episode_id=None, **kwargs) -> SqlObservation:
        task_name = kwargs.get("task", "select_basics")
        if task_name not in TASKS:
            task_name = "select_basics"

        task    = TASKS[task_name]
        new_id  = episode_id or str(uuid4())
        db_path = self._db_path(new_id)

        self._initialise_db(task_name, db_path)

        session = {
            "episode_id": new_id,
            "task_name":  task_name,
            "db_path":    str(db_path),
            "step_count": 0,
        }

        # Primary store: module-level dict (survives across instances in same process)
        _MEMORY_SESSIONS[new_id]       = session
        _MEMORY_SESSIONS["__latest__"] = new_id
        # Secondary store: disk (survives container restart)
        self._save_session_file(session)

        self._episode_id = new_id
        self._state      = State(episode_id=new_id, step_count=0)

        return SqlObservation(
            task_description   = task["description"],
            schema_info        = task["schema"],
            query_result       = [],
            error_message      = "",
            feedback           = "Episode started. Write a SQL query to solve the task above.",
            score_breakdown    = {},
            attempts_remaining = task["max_steps"],
            done               = False,
            reward             = 0.0,
        )

    # ── step() ────────────────────────────────────────────────────────────────

    def step(self, action: SqlAction) -> SqlObservation:
        session = self._resolve_session()

        if not session:
            return SqlObservation(
                task_description   = "",
                schema_info        = "",
                query_result       = [],
                error_message      = "No active session. Call /reset first.",
                feedback           = "No active session — call /reset before /step.",
                score_breakdown    = {"execute": -0.05},
                attempts_remaining = 0,
                done               = True,
                reward             = -0.05,
            )

        task_name = session.get("task_name", "select_basics")
        if task_name not in TASKS:
            task_name = "select_basics"

        db_path = Path(session.get("db_path") or str(self._db_path(session["episode_id"])))

        # Re-seed if the DB file was lost (e.g. tmpfs wipe on restart)
        if not db_path.exists():
            self._initialise_db(task_name, db_path)

        # Advance step counter
        step_count            = int(session.get("step_count", 0)) + 1
        session["step_count"] = step_count
        _MEMORY_SESSIONS[self._episode_id] = session
        self._save_session_file(session)

        self._state = State(
            episode_id = self._episode_id or str(uuid4()),
            step_count = step_count,
        )

        task               = TASKS[task_name]
        attempts_remaining = task["max_steps"] - step_count

        rows, err = _run_query_with_timeout(db_path, action.sql_query, timeout_seconds=5)

        if isinstance(err, TimeoutError):
            reward    = -0.10
            rows      = []
            feedback  = str(err)
            breakdown = {"execute": -0.10}
            error_msg = str(err)
        elif err is not None:
            reward    = -0.05
            rows      = []
            feedback  = f"SQL Error: {err}. Fix your syntax and try again."
            breakdown = {"execute": -0.05}
            error_msg = str(err)
        else:
            reward, feedback, breakdown = self._grade(rows, task["expected"], action.sql_query)
            error_msg = ""

        done = reward >= 0.95 or attempts_remaining <= 0

        return SqlObservation(
            task_description   = task["description"],
            schema_info        = task["schema"],
            query_result       = [list(r) for r in (rows or [])],
            error_message      = error_msg,
            feedback           = feedback,
            score_breakdown    = breakdown,
            attempts_remaining = max(0, attempts_remaining),
            done               = done,
            reward             = float(max(-0.10, min(1.0, reward))),
        )

    # ── Grader ────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_row(row: tuple) -> tuple:
        """Normalize floats to 2 decimal places for robust set comparison.

        SQLite can return 405.4999999999 instead of 405.5 due to IEEE 754
        floating-point arithmetic (SUM, AVG, ROUND operations).
        Without this, F1 drops to 0 even when the answer is logically correct.
        Strings and integers are returned unchanged.

        Examples:
            (405.4999999999,) -> (405.5,)
            ('Alice', 1)      -> ('Alice', 1)
            (5000.0,)         -> (5000.0,)
        """
        def _norm(v):
            if isinstance(v, float):
                return round(v, 2)
            return v
        return tuple(_norm(v) for v in row)

    def _grade(self, result: list, expected: list, sql_query: str):
        breakdown: dict = {"execute": 0.10}

        if not result:
            return (
                0.10,
                "Query ran but returned 0 rows. Check your WHERE clause or JOIN conditions.",
                breakdown,
            )

        # Use _normalize_row so floating-point arithmetic differences don't cause
        # false mismatches (e.g. 405.4999999999 vs 405.5)
        result_set   = set(self._normalize_row(tuple(r)) for r in result)
        expected_set = set(self._normalize_row(tuple(e)) for e in expected)

        result_cols   = len(result[0])   if result   else 0
        expected_cols = len(expected[0]) if expected else 0
        col_score = (
            0.20 if result_cols == expected_cols
            else 0.20 * (min(result_cols, expected_cols) / max(result_cols, expected_cols, 1))
        )
        breakdown["columns"] = round(col_score, 3)

        row_score = 0.20 * min(1.0, len(result) / max(len(expected), 1))
        breakdown["rows"] = round(row_score, 3)

        f1        = self._f1(result_set, expected_set)
        val_score = 0.40 * f1
        breakdown["values"] = round(val_score, 3)

        uses_star = "select*" in sql_query.lower().replace(" ", "")
        eff_score = 0.0 if uses_star else 0.10
        breakdown["efficiency"] = eff_score

        total = breakdown["execute"] + col_score + row_score + val_score + eff_score
        pct   = int(f1 * 100)

        if f1 >= 1.0 and col_score >= 0.20 and row_score >= 0.20:
            feedback = (
                "Perfect! Exact match."
                if not uses_star
                else "Correct result but avoid SELECT * — target only needed columns."
            )
        elif result_cols > expected_cols:
            feedback = (
                f"Too many columns ({result_cols} returned, {expected_cols} expected). "
                "Remove extra columns from SELECT."
            )
        elif result_cols < expected_cols:
            feedback = (
                f"Too few columns ({result_cols} returned, {expected_cols} expected). "
                "Add missing columns to SELECT."
            )
        elif len(result) > len(expected) * 1.5:
            feedback = (
                f"Too many rows ({len(result)} vs {len(expected)} expected). "
                "Check your WHERE or HAVING — a filter may be missing."
            )
        elif len(result) < len(expected):
            feedback = (
                f"Too few rows ({len(result)} vs {len(expected)} expected). "
                "Check your JOIN or WHERE — some matching rows are being excluded."
            )
        elif f1 >= 0.8:
            feedback = f"Very close! {pct}% of values match. Check column ordering or data type casting."
        elif f1 >= 0.5:
            feedback = f"Partial match: {pct}% correct. Re-read the task and check your filters."
        else:
            feedback = f"Mostly incorrect ({pct}% match). Start from the schema and re-read the task."

        return round(total, 3), feedback, breakdown

    @staticmethod
    def _f1(result_set: set, expected_set: set) -> float:
        if not result_set and not expected_set:
            return 1.0
        if not result_set or not expected_set:
            return 0.0
        intersection = result_set & expected_set
        precision    = len(intersection) / len(result_set)
        recall       = len(intersection) / len(expected_set)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @property
    def state(self) -> State:
        return self._state