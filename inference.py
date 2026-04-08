



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

# ── Required variables matching the pre-submission checklist exactly ──────────
API_BASE_URL     = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME       = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN         = os.getenv("HF_TOKEN")                        # no default — required
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")  # support both

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

SYSTEM_PROMPT = (
    "You are an expert SQL writer. You will be given a database schema and a task. "
    "Write a correct SQL query to solve the task. "
    "Reply with ONLY the raw SQL — no markdown, no backticks, no explanation."
)


# ── Logging helpers (exact format required by competition) ────────────────────

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
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Task runner ───────────────────────────────────────────────────────────────

async def run_task(task_name: str) -> float:
    # All LLM calls use the OpenAI client configured via the required variables
    client    = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    env       = await SqlEnv.from_url("https://Codexzzz-sql-env.hf.space")
    max_steps = TASK_MAX_STEPS.get(task_name, 5)

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

        score   = max(rewards) if rewards else 0.0
        score   = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

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