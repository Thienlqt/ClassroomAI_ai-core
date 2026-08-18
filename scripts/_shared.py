from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_FILE = PROJECT_ROOT / "models" / "gemma-4-E4B_q4_0-it.gguf"


def env_value(environ: Mapping[str, str], name: str, default: str) -> str:
    value = environ.get(name, "").strip()
    return value or default


def resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def display_command(command: list[str]) -> str:
    return shlex.join(command)


def project_environment(
    environ: Mapping[str, str] | None = None,
    *,
    env_path: Path = PROJECT_ROOT / ".env",
) -> dict[str, str]:
    if environ is not None:
        return dict(environ)

    file_values = {
        key: value
        for key, value in dotenv_values(env_path).items()
        if value is not None
    }
    # Explicit process variables always take priority over the local .env file.
    return {**file_values, **os.environ}


def child_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    return project_environment(environ)
