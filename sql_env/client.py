# from openenv.core.env_client import EnvClient
# from openenv.core.client_types import StepResult
# from openenv.core.env_server.types import State
# from .models import SqlAction, SqlObservation


# class SqlEnv(EnvClient[SqlAction, SqlObservation, State]):

#     def _step_payload(self, action: SqlAction) -> dict:
#         return {"sql_query": action.sql_query}

#     def _parse_result(self, payload: dict) -> StepResult[SqlObservation]:
#         obs_data = payload.get("observation", {})
#         obs = SqlObservation(
#             task_description  = obs_data.get("task_description",   ""),
#             schema_info       = obs_data.get("schema_info",         ""),
#             query_result      = obs_data.get("query_result",        []),
#             error_message     = obs_data.get("error_message",       ""),
#             feedback          = obs_data.get("feedback",            ""),
#             score_breakdown   = obs_data.get("score_breakdown",     {}),
#             attempts_remaining= obs_data.get("attempts_remaining",   0),
#             done              = payload.get("done",                False),
#             reward            = payload.get("reward",              0.0),
#         )
#         return StepResult(
#             observation=obs,
#             reward=payload.get("reward", 0.0),
#             done=payload.get("done", False),
#         )

#     def _parse_state(self, payload: dict) -> State:
#         return State(
#             episode_id=payload.get("episode_id"),
#             step_count=payload.get("step_count", 0),
#         )


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
            task_description   = obs_data.get("task_description",   ""),
            schema_info        = obs_data.get("schema_info",         ""),
            query_result       = obs_data.get("query_result",        []),
            error_message      = obs_data.get("error_message",       ""),
            feedback           = obs_data.get("feedback",            ""),
            score_breakdown    = obs_data.get("score_breakdown",     {}),
            attempts_remaining = obs_data.get("attempts_remaining",   0),
            # done and reward: prefer obs_data value, fall back to top-level payload
            done               = obs_data.get("done",   payload.get("done",   False)),
            reward             = obs_data.get("reward", payload.get("reward", 0.0)),
        )

        return StepResult(
            observation = obs,
            reward      = payload.get("reward", 0.0),
            done        = payload.get("done",   False),
        )

    def _parse_state(self, payload: dict) -> State:
        return State(
            episode_id = payload.get("episode_id"),
            step_count = payload.get("step_count", 0),
        )