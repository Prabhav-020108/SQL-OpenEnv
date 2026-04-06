from openenv.core.env_server.types import Action, Observation
from pydantic import Field

class SqlAction(Action):
    """The agent's action: a SQL query string."""
    sql_query: str = Field(..., description="SQL query to execute against the database")

class SqlObservation(Observation):
    """What the agent sees after each reset() or step()."""
    task_description: str   = Field(default="",  description="Natural language task")
    schema_info:      str   = Field(default="",  description="DDL schema of the database")
    query_result:     list  = Field(default_factory=list, description="Rows returned by query")
    error_message:    str   = Field(default="",  description="SQL error string if query failed")
    feedback:         str   = Field(default="",  description="Human-readable grader feedback")
    score_breakdown:  dict  = Field(default_factory=dict, description="Partial score components")
    attempts_remaining: int = Field(default=5,   description="Steps remaining in episode")