#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def measure(call: Callable[[], Any]) -> tuple[float, Any]:
    started = time.perf_counter()
    result = call()
    return round(time.perf_counter() - started, 3), result


def latency_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "mean": round(statistics.fmean(values), 3),
        "max": round(max(values), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local ClassroomAI components.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--health-runs", type=int, default=30)
    parser.add_argument(
        "--face-image",
        type=Path,
        default=PROJECT_ROOT / "frontend" / "src" / "assets" / "teacher-avatar-preview.png",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "components": {},
    }
    errors: list[str] = []

    with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
        health_latencies = []
        for _ in range(args.health_runs):
            latency, response = measure(lambda: client.get("/health"))
            response.raise_for_status()
            health_latencies.append(latency)
        report["components"]["health"] = {
            "runs": args.health_runs,
            "latency_seconds": latency_summary(health_latencies),
            "response": response.json(),
        }

        speech_text = "The eagle can fly."
        speech_latencies = []
        speech_audio: bytes | None = None
        for _ in range(3):
            try:
                latency, response = measure(
                    lambda: client.post("/v1/speech", json={"text": speech_text})
                )
                response.raise_for_status()
                speech_audio = response.content
                speech_latencies.append(latency)
            except httpx.HTTPError as error:
                errors.append(f"speech benchmark failed: {error}")
                break
        report["components"]["speech"] = {
            "runs": len(speech_latencies),
            "latency_seconds": latency_summary(speech_latencies) if speech_latencies else None,
            "audio_bytes": len(speech_audio) if speech_audio else 0,
        }

        if speech_audio:
            try:
                latency, response = measure(
                    lambda: client.post(
                        "/v1/audio/transcriptions",
                        files={"file": ("evaluation.wav", speech_audio, "audio/wav")},
                    )
                )
                response.raise_for_status()
                transcript = response.json().get("text", "")
                report["components"]["transcription"] = {
                    "runs": 1,
                    "latency_seconds": latency,
                    "input_text": speech_text,
                    "transcript": transcript,
                    "contains_expected_words": all(
                        word in transcript.casefold() for word in ("eagle", "fly")
                    ),
                }
            except httpx.HTTPError as error:
                errors.append(f"transcription benchmark failed: {error}")

        try:
            image = base64.b64encode(args.face_image.read_bytes()).decode("ascii")
            latency, response = measure(
                lambda: client.post("/v1/faces/recognize", json={"image_base64": image})
            )
            response.raise_for_status()
            faces = response.json()
            report["components"]["face_recognition"] = {
                "runs": 1,
                "latency_seconds": latency,
                "synthetic_image": str(args.face_image.relative_to(PROJECT_ROOT)),
                "faces_detected": len(faces),
                "results": faces,
                "limitation": "Synthetic-image smoke test; not an identity-accuracy test.",
            }
        except (OSError, ValueError, httpx.HTTPError) as error:
            errors.append(f"face-recognition benchmark failed: {error}")

        for name, path in (
            ("frontend", "/"),
            ("avatar", "/assets/avatar/teacher.vrm"),
        ):
            try:
                latency, response = measure(lambda path=path: client.get(path))
                response.raise_for_status()
                report["components"][name] = {
                    "latency_seconds": latency,
                    "bytes": len(response.content),
                    "content_type": response.headers.get("content-type"),
                }
            except httpx.HTTPError as error:
                errors.append(f"{name} asset benchmark failed: {error}")

    report["errors"] = errors
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Saved {args.output}")
    else:
        print(rendered)
    if errors:
        print("Completed with component errors:")
        for error in errors:
            print(f"- {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
