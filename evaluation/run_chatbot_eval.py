#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS = PROJECT_ROOT / "evaluation" / "chatbot_scenarios.json"


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return round(ordered[index], 3)


def validate_response(scenario: dict[str, Any], response: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_type = scenario.get("expected_type")
    if response.get("type") != expected_type:
        return [f"expected type {expected_type!r}, received {response.get('type')!r}"]

    if expected_type == "action":
        action = response.get("action") or {}
        if action.get("type") != scenario.get("expected_action_type"):
            failures.append(
                f"expected action {scenario.get('expected_action_type')!r}, "
                f"received {action.get('type')!r}"
            )
        expected_image_id = scenario.get("expected_image_id")
        if expected_image_id and action.get("payload", {}).get("image_id") != expected_image_id:
            failures.append(f"expected image_id {expected_image_id!r}")
        if action.get("type") == "ui.show_choices":
            payload = action.get("payload", {})
            if "correct_answer" in payload:
                failures.append("correct_answer leaked to the browser action")
            choices = payload.get("choices") or []
            if not 2 <= len(choices) <= 4:
                failures.append("choice action did not contain two to four choices")
        return failures

    speech = str(response.get("speech") or "")
    normalized = speech.casefold()
    words = speech.split()
    segments = response.get("segments") or []
    segment_languages = {
        str(segment.get("language")) for segment in segments if isinstance(segment, dict)
    }
    for language in scenario.get("expected_languages", []):
        if language not in segment_languages:
            failures.append(f"missing expected speech language {language!r}")
    for required in scenario.get("required_all", []):
        if required.casefold() not in normalized:
            failures.append(f"missing required text {required!r}")
    required_any = scenario.get("required_any", [])
    if required_any and not any(value.casefold() in normalized for value in required_any):
        failures.append(f"none of the boundary terms were present: {required_any}")
    for forbidden in scenario.get("forbidden_any", []):
        if forbidden.casefold() in normalized:
            failures.append(f"contained forbidden text {forbidden!r}")
    if scenario.get("max_words") and len(words) > int(scenario["max_words"]):
        failures.append(f"response had {len(words)} words; maximum is {scenario['max_words']}")
    if scenario.get("max_questions") is not None:
        question_count = speech.count("?")
        if question_count > int(scenario["max_questions"]):
            failures.append(
                f"response had {question_count} question marks; maximum is "
                f"{scenario['max_questions']}"
            )
    return failures


def follow_action(client: httpx.Client, session_id: str, response: dict[str, Any]) -> dict[str, Any]:
    action = response["action"]
    if action["type"] == "ui.show_choices":
        result = {"selected": action["payload"]["choices"][0]}
    elif action["type"] == "ui.show_image":
        result = {"success": True}
    else:
        raise ValueError(f"Unsupported evaluation action: {action['type']}")
    endpoint = f"/v1/sessions/{session_id}/actions/{action['call_id']}/result"
    follow_up = client.post(endpoint, json={"result": result})
    follow_up.raise_for_status()
    return follow_up.json()


def run_scenario(
    client: httpx.Client,
    scenario: dict[str, Any],
    run_number: int,
) -> dict[str, Any]:
    session_id = f"eval-{scenario['id']}-{uuid4().hex}"
    started = time.perf_counter()
    status_code: int | None = None
    try:
        response = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={"message": scenario["prompt"]},
        )
        status_code = response.status_code
        response.raise_for_status()
        first_output = response.json()
        first_latency = time.perf_counter() - started
        failures = validate_response(scenario, first_output)
        follow_output = None
        if scenario.get("follow_action") and not failures:
            follow_output = follow_action(client, session_id, first_output)
            if follow_output.get("type") != "speech" or not follow_output.get("speech"):
                failures.append("action follow-up did not return teacher speech")
        total_latency = time.perf_counter() - started
        return {
            "scenario_id": scenario["id"],
            "category": scenario["category"],
            "run": run_number,
            "passed": not failures,
            "failures": failures,
            "status_code": status_code,
            "first_latency_seconds": round(first_latency, 3),
            "total_latency_seconds": round(total_latency, 3),
            "first_output": first_output,
            "follow_output": follow_output,
        }
    except (httpx.HTTPError, ValueError, KeyError) as error:
        return {
            "scenario_id": scenario["id"],
            "category": scenario["category"],
            "run": run_number,
            "passed": False,
            "failures": [f"evaluation request failed: {error}"],
            "status_code": status_code,
            "first_latency_seconds": round(time.perf_counter() - started, 3),
            "total_latency_seconds": round(time.perf_counter() - started, 3),
            "first_output": None,
            "follow_output": None,
        }
    finally:
        try:
            client.delete(f"/v1/sessions/{session_id}")
        except httpx.HTTPError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live ClassroomAI chatbot scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--scenario-id",
        action="append",
        help="Run only this scenario ID; may be supplied more than once.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    if args.scenario_id:
        selected = set(args.scenario_id)
        scenarios = [scenario for scenario in scenarios if scenario["id"] in selected]
        missing = selected - {scenario["id"] for scenario in scenarios}
        if missing:
            parser.error(f"unknown --scenario-id values: {', '.join(sorted(missing))}")
    results: list[dict[str, Any]] = []
    with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
        health = client.get("/health")
        health.raise_for_status()
        service = health.json()
        for run_number in range(1, args.runs + 1):
            for scenario in scenarios:
                result = run_scenario(client, scenario, run_number)
                results.append(result)
                verdict = "PASS" if result["passed"] else "FAIL"
                print(
                    f"{verdict:4} {scenario['id']:<22} "
                    f"{result['total_latency_seconds']:>7.3f}s"
                )

    latencies = [item["first_latency_seconds"] for item in results]
    passed = sum(item["passed"] for item in results)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "service": service,
        "scenario_count": len(scenarios),
        "runs_per_scenario": args.runs,
        "summary": {
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 4) if results else 0.0,
            "latency_seconds": {
                "mean": round(statistics.fmean(latencies), 3) if latencies else None,
                "p50": percentile(latencies, 0.50),
                "p95": percentile(latencies, 0.95),
                "max": round(max(latencies), 3) if latencies else None,
            },
        },
        "results": results,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Saved {args.output}")
    else:
        print(rendered)
    print(f"Passed {passed}/{len(results)} live checks")
    return 1 if args.strict and passed != len(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
