try:
    from openenv.core.env_server.http_server import create_app
except ImportError as e:
    raise ImportError("Run: pip install openenv-core") from e

try:
    from ..models import SqlAction, SqlObservation
    from .sql_environment import SqlEnvironment
except ImportError:
    from models import SqlAction, SqlObservation
    from server.sql_environment import SqlEnvironment

app = create_app(
    SqlEnvironment,
    SqlAction,
    SqlObservation,
    env_name="sql_env",
    max_concurrent_envs=10,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()