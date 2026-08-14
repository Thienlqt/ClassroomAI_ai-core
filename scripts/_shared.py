from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Mapping


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


def child_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    return dict(os.environ if environ is None else environ)
