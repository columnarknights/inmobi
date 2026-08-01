import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Load .env from the project root (two levels up from this file), not from
# whatever directory the process happens to be launched from — dotenv_values()
# with no path only checks the current working directory, which silently
# finds nothing if `rca` is invoked from outside the project root.
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# Values from this project's own .env take priority over whatever is already
# in the ambient shell environment (rather than dotenv's usual default of
# "don't override an existing env var"). This matters concretely here: some
# dev environments (e.g. a Claude Code session) already export an
# ANTHROPIC_API_KEY of their own, which would otherwise silently shadow the
# project-specific key a user pastes into .env.
_dotenv = dotenv_values(_ENV_PATH)


def _get(key: str, default: str = "") -> str:
    val = _dotenv.get(key)
    return val if val else os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    clickhouse_host: str = _get("CLICKHOUSE_HOST", "localhost")
    clickhouse_port: int = int(_get("CLICKHOUSE_PORT", "8123"))
    clickhouse_user: str = _get("CLICKHOUSE_USER", "default")
    clickhouse_password: str = _get("CLICKHOUSE_PASSWORD", "")
    clickhouse_database: str = _get("CLICKHOUSE_DATABASE", "inmobi")
    clickhouse_secure: bool = _get("CLICKHOUSE_SECURE", "true").lower() == "true"

    gemini_api_key: str = _get("GEMINI_API_KEY", "")
    gemini_model: str = _get("GEMINI_MODEL", "gemini-flash-lite-latest")

    langfuse_public_key: str = _get("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = _get("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = _get("LANGFUSE_HOST", "https://cloud.langfuse.com")


settings = Settings()
