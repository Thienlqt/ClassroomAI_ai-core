#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Mapping

try:
    from ._shared import DEFAULT_MODEL_FILE, PROJECT_ROOT, display_command, env_value
except ImportError:  # Direct execution: python scripts/start_model.py
    from _shared import DEFAULT_MODEL_FILE, PROJECT_ROOT, display_command, env_value


def build_command(environ: Mapping[str, str] | None = None) -> list[str]:
    values = os.environ if environ is None else environ
    executable = env_value(values, "CLASSROOM_LLAMA_SERVER", "llama-server")
    model_value = env_value(values, "CLASSROOM_MODEL_FILE", str(DEFAULT_MODEL_FILE))
    model_file = Path(model_value).expanduser()
    if not model_file.is_absolute():
        model_file = PROJECT_ROOT / model_file

    command = [
        executable,
        "--model",
        str(model_file.resolve()),
        "--alias",
        env_value(values, "CLASSROOM_MODEL", "gemma4-e4b"),
        "--host",
        env_value(values, "CLASSROOM_LLAMA_HOST", "127.0.0.1"),
        "--port",
        env_value(values, "CLASSROOM_LLAMA_PORT", "8080"),
        "--ctx-size",
        env_value(values, "CLASSROOM_LLAMA_CONTEXT_SIZE", "8192"),
        "--parallel",
        env_value(values, "CLASSROOM_LLAMA_PARALLEL", "1"),
        "--jinja",
        "--no-mmproj",
        "--reasoning",
        "off",
    ]

    threads = values.get("CLASSROOM_LLAMA_THREADS", "").strip()
    if threads:
        command.extend(["--threads", threads])

    extra = values.get("CLASSROOM_LLAMA_EXTRA_ARGS", "").strip()
    if extra:
        command.extend(shlex.split(extra, posix=os.name != "nt"))
    return command


def _validate(command: list[str]) -> None:
    executable = command[0]
    if shutil.which(executable) is None and not Path(executable).is_file():
        raise SystemExit(
            "llama-server was not found. Install llama.cpp, or set "
            "CLASSROOM_LLAMA_SERVER to its full path."
        )

    model_file = Path(command[command.index("--model") + 1])
    if not model_file.is_file():
        raise SystemExit(
            f"Model file not found: {model_file}\n"
            "Follow models/README.md to download the official GGUF."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Gemma with llama.cpp.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the command without starting it."
    )
    args = parser.parse_args()
    command = build_command()
    _validate(command)
    print(f"Starting model server:\n{display_command(command)}", flush=True)
    if args.dry_run:
        return 0
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
