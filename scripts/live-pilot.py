"""Gated live-model pilot harness (Milestone 1.7). NOT RUN as part of M1.7.

By default this prints a plan with request/token reservations and exits 2 without
contacting anything. It only dispatches when *all* of these are true:

  * --execute is given,
  * --approval equals "I-APPROVE-LIVE-PILOT-<provider>-<YYYY-MM-DD>" for today's local date,
  * the environment has IMMORTILITY_LIVE_PILOT=authorized,
  * caps are within hard limits (<=5 tasks, <=10 requests, <=20000 tokens),
  * no earlier reservation in the pilot directory is still open,
  * the pilot directory is a fresh ``canary-live-pilot*`` folder (never production data).

A reservation is written before the first request and settled after every request.
No retry is made on any provider error, quota error or timeout. Results are labelled
``live_model``; simulated results are never mixed in.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

HARD_TASKS, HARD_REQUESTS, HARD_TOKENS = 5, 10, 20_000
PROVIDERS = {"groq", "gemini", "nvidia"}
PROMPTS = [
    "Reply with one short sentence: what is 2 + 2?",
    "Name the capital of France in one word.",
    "What time is it? Use the clock tool if you have it.",
    "Multiply 247 by 36 and give only the number.",
    "Say hello in five words or fewer.",
]


def approval_phrase(provider: str, today: date | None = None) -> str:
    return f"I-APPROVE-LIVE-PILOT-{provider}-{(today or date.today()).isoformat()}"


def plan(args: argparse.Namespace) -> dict:
    per_request = max(1, args.max_tokens // max(1, args.max_requests))
    return {
        "inference_category": "live_model",
        "provider": args.provider,
        "tasks": args.tasks,
        "reservation": {
            "requests": args.max_requests,
            "tokens": args.max_tokens,
            "tokens_per_request_cap": per_request,
            "retries": 0,
            "paid_usd": 0,
        },
        "prompts": PROMPTS[: args.tasks],
        "pilot_dir": str(args.pilot_dir),
    }


def gate(args: argparse.Namespace, environ: dict[str, str] | None = None) -> list[str]:
    """Every reason the pilot must not run. Empty only when every gate passes."""
    env = os.environ if environ is None else environ
    reasons = []
    if args.provider not in PROVIDERS:
        reasons.append("provider must be one of groq, gemini, nvidia")
    if not args.execute:
        reasons.append("--execute was not given (plan only)")
    if args.approval != approval_phrase(args.provider):
        reasons.append("--approval does not match today's explicit approval phrase")
    if env.get("IMMORTILITY_LIVE_PILOT") != "authorized":
        reasons.append("IMMORTILITY_LIVE_PILOT=authorized is not set")
    if not 1 <= args.tasks <= HARD_TASKS:
        reasons.append(f"tasks must be 1..{HARD_TASKS}")
    if not 1 <= args.max_requests <= HARD_REQUESTS:
        reasons.append(f"max requests must be 1..{HARD_REQUESTS}")
    if not 1 <= args.max_tokens <= HARD_TOKENS:
        reasons.append(f"max tokens must be 1..{HARD_TOKENS}")
    if args.max_requests < args.tasks:
        reasons.append("max requests is below the task count")
    name = Path(args.pilot_dir).name
    if not name.startswith("canary-live-pilot"):
        reasons.append("pilot dir must be a canary-live-pilot* folder")
    ledger = Path(args.pilot_dir) / "live-pilot-reservations.json"
    if ledger.exists():
        try:
            entries = json.loads(ledger.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            entries = [{"open": True}]
        if any(entry.get("open") for entry in entries):
            reasons.append("an earlier reservation is still open; settle it by hand first")
    return reasons


def reserve(args: argparse.Namespace) -> Path:
    directory = Path(args.pilot_dir)
    directory.mkdir(parents=True, exist_ok=True)
    ledger = directory / "live-pilot-reservations.json"
    entries = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    entries.append(
        {
            **plan(args)["reservation"],
            "open": True,
            "used_requests": 0,
            "used_tokens": 0,
            "opened": datetime.now().astimezone().isoformat(),
        }
    )
    ledger.write_text(json.dumps(entries, indent=1), encoding="utf-8")
    return ledger


def settle(ledger: Path, requests: int, tokens: int, close: bool) -> None:
    entries = json.loads(ledger.read_text(encoding="utf-8"))
    entries[-1].update(used_requests=requests, used_tokens=tokens, open=not close)
    if close:
        entries[-1]["closed"] = datetime.now().astimezone().isoformat()
    ledger.write_text(json.dumps(entries, indent=1), encoding="utf-8")


def execute(args: argparse.Namespace) -> dict:  # pragma: no cover - never run in M1.7
    """Dispatch through the real broker (in-process, isolated pilot dir). Stops on first error."""
    import socket
    import threading
    import time
    import urllib.request

    import uvicorn

    from immortility_broker.app import create_app
    from immortility_broker.config import Settings
    from immortility_broker.contracts import uid

    ledger = reserve(args)
    settings = Settings(data_dir=Path(args.pilot_dir), model_call_cap=min(6, args.max_requests))
    token = os.urandom(32).hex()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(create_app(settings, token, url), log_level="critical"))
    thread = threading.Thread(
        target=lambda: __import__("asyncio").run(server.serve(sockets=[listener])), daemon=True
    )
    thread.start()
    while not server.started:
        time.sleep(0.05)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def call(method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            url + path,
            method=method,
            headers=headers,
            data=None if body is None else json.dumps(body).encode(),
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode())

    results, requests_used, tokens_used = [], 0, 0
    try:
        session = call("POST", "/v1/sessions")["id"]
        for prompt in PROMPTS[: args.tasks]:
            if requests_used >= args.max_requests or tokens_used >= args.max_tokens:
                break
            task = call(
                "POST",
                "/v1/tasks",
                {
                    "schema_version": "1.0",
                    "session_id": session,
                    "request_id": uid(),
                    "content": prompt,
                    "cloud_consent": True,
                    "budget_mode": "fast",
                },
            )
            while task["status"] not in {
                "succeeded",
                "failed",
                "blocked",
                "cancelled",
                "disconnected",
                "rate_limited",
            }:
                time.sleep(0.5)
                task = call("GET", f"/v1/tasks/{task['task_id']}")
            usage = (task.get("result") or {}).get("usage") or {}
            requests_used += int(usage.get("calls", 1))
            tokens_used += int(usage.get("total_tokens", 0))
            settle(ledger, requests_used, tokens_used, close=False)
            results.append(
                {
                    "task_id": task["task_id"],
                    "status": task["status"],
                    "error": (task.get("error") or {}).get("code"),
                }
            )
            if task["status"] != "succeeded":
                break  # no retry, no fallback
    finally:
        settle(ledger, requests_used, tokens_used, close=True)
        server.should_exit = True
        thread.join(timeout=30)
    return {
        "inference_category": "live_model",
        "results": results,
        "requests_used": requests_used,
        "tokens_used": tokens_used,
    }


def parse(argv: list[str]) -> argparse.Namespace:
    local = Path(os.environ.get("LOCALAPPDATA", ".")) / "Immortility" / "canary-live-pilot"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", default="groq")
    parser.add_argument("--tasks", type=int, default=3)
    parser.add_argument("--max-requests", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--pilot-dir", type=Path, default=local)
    parser.add_argument("--approval", default="")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    reasons = gate(args)
    report = {
        "status": "blocked" if reasons else "authorized",
        "calls_made": 0,
        "plan": plan(args),
        "blocked_by": reasons,
    }
    if reasons:
        print(json.dumps(report, indent=2))
        return 2
    report.update(status="ran", **execute(args))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
