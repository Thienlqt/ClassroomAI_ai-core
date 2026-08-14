#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping

try:
    from ._shared import PROJECT_ROOT, child_environment, display_command, env_value
except ImportError:  # Direct execution: python scripts/start_hermes_teacher.py
    from _shared import PROJECT_ROOT, child_environment, display_command, env_value


TEMPLATE_DIR = PROJECT_ROOT / "integrations" / "hermes" / "teacher_assistant"
DEFAULT_HOME = PROJECT_ROOT / ".runtime" / "hermes-teacher"


def build_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    child = child_environment(environ)
    child.setdefault("HERMES_HOME", str(DEFAULT_HOME))
    return child


def build_command(
    environ: Mapping[str, str] | None = None,
    *,
    query: str | None = None,
) -> list[str]:
    values = os.environ if environ is None else environ
    command = [
        env_value(values, "CLASSROOM_HERMES_COMMAND", "hermes"),
        "chat",
        "--toolsets",
        "memory",
    ]
    if query:
        command.extend(["--query", query])
    return command


def prepare_home(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in ("config.yaml", "SOUL.md"):
        destination = path / name
        if not destination.exists():
            shutil.copyfile(TEMPLATE_DIR / name, destination)


def _validate(command: list[str]) -> None:
    executable = command[0]
    if shutil.which(executable) is None and not Path(executable).is_file():
        raise SystemExit(
            "Hermes Agent was not found. Follow docs/OPTIONAL_COMPONENTS.md to "
            "install the official Hermes CLI."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start the isolated ClassroomAI teacher assistant with Hermes."
    )
    parser.add_argument("--query", help="Run one teacher query and exit.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print settings without starting Hermes."
    )
    args = parser.parse_args()
    environment = build_environment()
    command = build_command(environment, query=args.query)
    hermes_home = Path(environment["HERMES_HOME"])
    print(
        "Starting the teacher-only Hermes mode. Gemma must be running with a "
        "65536-token context.\n"
        f"HERMES_HOME={hermes_home}\n{display_command(command)}",
        flush=True,
    )
    if args.dry_run:
        return 0
    _validate(command)
    prepare_home(hermes_home)
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
