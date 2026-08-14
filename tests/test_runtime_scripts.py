import sys

from classroom_ai.config import Settings
from scripts.start_api import build_command as build_api_command
from scripts.start_api import build_environment
from scripts.start_hermes_teacher import build_command as build_hermes_command
from scripts.start_hermes_teacher import build_environment as build_hermes_environment
from scripts.start_model import build_command as build_model_command


def test_llama_cpp_is_the_default_provider(monkeypatch):
    monkeypatch.delenv("CLASSROOM_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("CLASSROOM_MODEL", raising=False)

    config = Settings()

    assert config.model_provider == "llama_cpp"
    assert config.model == "gemma4-e4b"


def test_model_launcher_uses_memory_safe_classroom_defaults():
    command = build_model_command({})

    assert command[0] == "llama-server"
    assert command[command.index("--ctx-size") + 1] == "8192"
    assert command[command.index("--parallel") + 1] == "1"
    assert command[command.index("--alias") + 1] == "gemma4-e4b"
    assert command[command.index("--model") + 1].endswith(
        "models/gemma-4-E4B_q4_0-it.gguf"
    )
    assert "--jinja" in command
    assert "--no-mmproj" in command


def test_model_launcher_accepts_intel_cpu_thread_tuning():
    command = build_model_command(
        {
            "CLASSROOM_LLAMA_THREADS": "8",
            "CLASSROOM_LLAMA_EXTRA_ARGS": "--no-warmup",
        }
    )

    assert command[command.index("--threads") + 1] == "8"
    assert "--no-warmup" in command


def test_api_launcher_supplies_llama_cpp_environment():
    environment = build_environment({})
    command = build_api_command(environment, reload=True)

    assert environment["CLASSROOM_MODEL_PROVIDER"] == "llama_cpp"
    assert environment["CLASSROOM_MODEL"] == "gemma4-e4b"
    assert environment["CLASSROOM_OPENAI_BASE_URL"].endswith(":8080/v1")
    assert command[:3] == [sys.executable, "-m", "uvicorn"]
    assert "--reload" in command


def test_hermes_launcher_is_isolated_and_memory_only():
    environment = build_hermes_environment({})
    command = build_hermes_command(environment, query="Plan an animal lesson")

    assert environment["HERMES_HOME"].endswith(".runtime/hermes-teacher")
    assert command[:2] == ["hermes", "chat"]
    assert command[command.index("--toolsets") + 1] == "memory"
    assert command[-2:] == ["--query", "Plan an animal lesson"]
