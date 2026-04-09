



# """
# Inference Script — SQL Query Grader Environment
# Mandatory stdout format: [START], [STEP], [END]
# Place this file at the repo ROOT (not inside sql_env/).
# """
# import asyncio
# import os
# from typing import List

# from openai import OpenAI
# from sql_env import SqlAction, SqlEnv

# IMAGE_NAME   = os.getenv("IMAGE_NAME")
# API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
# API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
# MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")

# TASKS = ["select_basics", "aggregate_filter", "multi_join", "data_anomalies"]
# TASK_MAX_STEPS = {
#     "select_basics":    5,
#     "aggregate_filter": 5,
#     "multi_join":       7,
#     "data_anomalies":   7,
# }
# BENCHMARK         = "sql_env"
# SUCCESS_THRESHOLD = 0.7

# SYSTEM_PROMPT = (
#     "You are an expert SQL writer. You will be given a database schema and a task. "
#     "Write a correct SQL query to solve the task. "
#     "Reply with ONLY the raw SQL — no markdown, no backticks, no explanation."
# )


# def log_start(task: str, env: str, model: str) -> None:
#     print(f"[START] task={task} env={env} model={model}", flush=True)


# def log_step(step: int, action: str, reward: float, done: bool, error) -> None:
#     error_val = error if error else "null"
#     print(
#         f"[STEP] step={step} action={action} "
#         f"reward={reward:.2f} done={str(done).lower()} error={error_val}",
#         flush=True,
#     )


# def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
#     rewards_str = ",".join(f"{r:.2f}" for r in rewards)
#     print(
#         f"[END] success={str(success).lower()} steps={steps} "
#         f"score={score:.3f} rewards={rewards_str}",
#         flush=True,
#     )


# async def run_task(task_name: str) -> float:
#     client    = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
#     env       = await SqlEnv.from_docker_image(IMAGE_NAME)
#     max_steps = TASK_MAX_STEPS.get(task_name, 5)

#     rewards:     List[float] = []
#     steps_taken: int         = 0
#     score:       float       = 0.0
#     success:     bool        = False

#     log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

#     try:
#         result = await env.reset(task=task_name)
#         obs    = result.observation

#         for step in range(1, max_steps + 1):
#             if result.done:
#                 break

#             completion = client.chat.completions.create(
#                 model=MODEL_NAME,
#                 messages=[
#                     {"role": "system", "content": SYSTEM_PROMPT},
#                     {
#                         "role": "user",
#                         "content": (
#                             f"Schema:\n{obs.schema_info}\n\n"
#                             f"Task:\n{obs.task_description}\n\n"
#                             f"Previous feedback:\n{obs.feedback}\n\n"
#                             "Write the SQL query:"
#                         ),
#                     },
#                 ],
#                 max_tokens=400,
#                 temperature=0.3,
#             )

#             sql    = (completion.choices[0].message.content or "").strip()
#             result = await env.step(SqlAction(sql_query=sql))
#             obs    = result.observation
#             reward = result.reward or 0.0

#             rewards.append(reward)
#             steps_taken = step
#             log_step(
#                 step   = step,
#                 action = sql[:100].replace("\n", " "),
#                 reward = reward,
#                 done   = result.done,
#                 error  = obs.error_message or None,
#             )

#             if result.done:
#                 break

#         score   = max(rewards) if rewards else 0.0
#         score   = min(max(score, 0.0), 1.0)
#         success = score >= SUCCESS_THRESHOLD

#     finally:
#         try:
#             await env.close()
#         except Exception:
#             pass
#         log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

#     return score


# async def main() -> None:
#     for task in TASKS:
#         await run_task(task)


# if __name__ == "__main__":
#     asyncio.run(main())

"""
Inference Script — SQL Query Grader Environment
Mandatory stdout format: [START], [STEP], [END]
Place this file at the repo ROOT (not inside sql_env/).
"""
import asyncio
import os
from typing import List, Optional

from openai import OpenAI
from sql_env import SqlAction, SqlEnv

# ── Required variables ────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")

# ── FIXED: all-lowercase registry URL ────────────────────────────────────────
# from_env("Codexzzz/sql-env") converts to registry.hf.space/Codexzzz-sql-env
# Docker rejects uppercase → exit 125 "invalid reference format"
# Fix: hardcode lowercase and use from_docker_image() directly
DOCKER_IMAGE = "registry.hf.space/codexzzz-sql-env:latest"

# ── Config ────────────────────────────────────────────────────────────────────
TASKS = ["select_basics", "aggregate_filter", "multi_join", "data_anomalies"]
TASK_MAX_STEPS = {
    "select_basics":    5,
    "aggregate_filter": 5,
    "multi_join":       7,
    "data_anomalies":   7,
}
BENCHMARK         = "sql_env"
SUCCESS_THRESHOLD = 0.7
# Validator-facing score bounds.
# Keep a safety margin from 0 and 1 so even downstream rounding stays in-range.
VALIDATOR_SCORE_MIN = 0.01
VALIDATOR_SCORE_MAX = 0.99

SYSTEM_PROMPT = (
    "You are an expert SQL writer. You will be given a database schema and a task. "
    "Write a correct SQL query to solve the task. "
    "Reply with ONLY the raw SQL — no markdown, no backticks, no explanation."
)


# ── Logging helpers ───────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} "
        f"reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Task runner ───────────────────────────────────────────────────────────────

async def run_task(task_name: str) -> float:
    if not HF_TOKEN:
        raise ValueError(
            "No API token found. Set HF_TOKEN or OPENAI_API_KEY environment variable."
        )

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    # FIXED: from_docker_image with all-lowercase image name
    # This avoids the uppercase conversion bug in from_env()
    env = await SqlEnv.from_docker_image(DOCKER_IMAGE)

    max_steps    = TASK_MAX_STEPS.get(task_name, 5)
    rewards:     List[float] = []
    steps_taken: int         = 0
    score:       float       = 0.0
    success:     bool        = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task=task_name)
        obs    = result.observation

        for step in range(1, max_steps + 1):
            if result.done:
                break

            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Schema:\n{obs.schema_info}\n\n"
                            f"Task:\n{obs.task_description}\n\n"
                            f"Previous feedback:\n{obs.feedback}\n\n"
                            "Write the SQL query:"
                        ),
                    },
                ],
                max_tokens=400,
                temperature=0.3,
            )

            sql    = (completion.choices[0].message.content or "").strip()
            result = await env.step(SqlAction(sql_query=sql))
            obs    = result.observation
            reward = result.reward or 0.0
            error  = obs.error_message if obs.error_message else None

            rewards.append(reward)
            steps_taken = step

            log_step(
                step   = step,
                action = sql[:100].replace("\n", " "),
                reward = reward,
                done   = result.done,
                error  = error,
            )

            if result.done:
                break

        raw_score = max(rewards) if rewards else 0.0
        # Hackathon validator requires score strictly inside (0, 1).
        # Use a visible safety margin so formatting/rounding can't bounce to 0.0/1.0.
        score   = min(max(raw_score, VALIDATOR_SCORE_MIN), VALIDATOR_SCORE_MAX)
        success = raw_score >= SUCCESS_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    for task in TASKS:
        await run_task(task)


if __name__ == "__main__":
    asyncio.run(main())