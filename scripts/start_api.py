#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Mapping

try:
    from ._shared import PROJECT_ROOT, child_environment, display_command, env_value
except ImportError:  # Direct execution: python scripts/start_api.py
    from _shared import PROJECT_ROOT, child_environment, display_command, env_value


def build_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    child = child_environment(environ)
    child.setdefault("CLASSROOM_MODEL_PROVIDER", "llama_cpp")
    child.setdefault("CLASSROOM_MODEL", "gemma4-e4b")
    child.setdefault("CLASSROOM_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    child.setdefault("CLASSROOM_OPENAI_API_KEY", "local-no-key")
    return child


def build_command(
    environ: Mapping[str, str] | None = None, *, reload: bool = False
) -> list[str]:
    values = child_environment(environ)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api:app",
        "--host",
        env_value(values, "CLASSROOM_API_HOST", "127.0.0.1"),
        "--port",
        env_value(values, "CLASSROOM_API_PORT", "8000"),
    ]
    if reload:
        command.append("--reload")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the ClassroomAI HTTP API.")
    parser.add_argument("--reload", action="store_true", help="Reload after code changes.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the command without starting it."
    )
    args = parser.parse_args()
    environment = build_environment()
    command = build_command(environment, reload=args.reload)
    print(
        "Starting ClassroomAI with "
        f"provider={environment['CLASSROOM_MODEL_PROVIDER']} and "
        f"model={environment['CLASSROOM_MODEL']}:\n{display_command(command)}",
        flush=True,
    )
    if args.dry_run:
        return 0
    return subprocess.run(
        command, cwd=PROJECT_ROOT, env=environment, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
