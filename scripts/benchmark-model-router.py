"""Measure deterministic routing overhead, never cloud quality or inference latency."""

import json
import argparse
import math
import statistics
import sys
import tempfile
import time
from pathlib import Path

from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.config import Settings
from immortility_broker.contracts import TaskRequest
from immortility_broker.evidence import (
    engineering_output_path,
    write_engineering_evidence,
    implementation_provenance,
)
from immortility_broker.providers import (
    PROVIDERS,
    ModelOffer,
    ModelRegistry,
    ModelSelection,
    Requirements,
    credential_identity,
    task_class,
)
from immortility_broker.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    output = engineering_output_path("router-benchmark", parser.parse_args().output)
    corpus = [
        ("Hello", [], "none"),
        ("Summarize this sentence", [], "none"),
        ("Extract JSON fields", [], "none"),
        ("Classify the supplied labels", [], "none"),
        ("Prove the conclusion", [], "none"),
        ("Analyze these tradeoffs", [], "none"),
        ("Debug this repository", [], "none"),
        ("Refactor Python code", [], "none"),
        ("Research MCP sources", [], "none"),
        ("Compare cited documentation", [], "none"),
        ("Verify the current UTC time", ["clock.now.v1"], "none"),
        ("Create a report", ["public.research.v1", "report.create.v1"], "markdown-and-pdf"),
    ]
    cache = ROOT / ".cache/engineering-m3"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="routing-benchmark-", dir=cache) as directory:
        started = time.perf_counter()
        settings = Settings(
            _env_file=None,
            data_dir=Path(directory),
            **{
                provider.credential_field: SecretStr("fixture-" + provider.id)
                for provider in PROVIDERS.values()
            },
        )
        store = Store(Path(directory) / "state.sqlite3")
        registry = ModelRegistry(store.db, settings, clock=lambda: 1000.0)
        cold_ms = 1000 * (time.perf_counter() - started)
        try:
            registry.models = {}
            for provider in PROVIDERS.values():
                route = ModelOffer(
                    route_id=provider.id + "/synthetic-model",
                    provider=provider.id,
                    model_id="synthetic-model",
                    context_tokens=32768,
                    tools_qualified=True,
                    structured_qualified=True,
                    qualification="offline",
                    privacy=("public", "personal"),
                    zero_price_until=2000.0,
                    account_until=2000.0,
                    available=True,
                    credential_identity=credential_identity(settings, provider.id),
                )
                registry.models[route.route_id] = route
            selection, timings, outcomes = ModelSelection(), [], {}
            for index in range(1200):
                content, capabilities, artifact = corpus[index % len(corpus)]
                tick = time.perf_counter()
                kind = task_class(content, capabilities, artifact)
                result = registry.choose(
                    selection,
                    Requirements(
                        task_class=kind,
                        tools=bool(capabilities),
                        context_tokens=6000,
                        privacy="public",
                    ),
                )
                duration = 1000 * (time.perf_counter() - tick)
                if index >= 200:
                    timings.append(duration)
                outcomes[kind] = result.provider
            # Representative successful/failed outcomes exercise the measured-
            # ranking branch. They are synthetic, not model benchmark scores.
            sid = store.session()["id"]
            for route in registry.models.values():
                for index in range(3):
                    task = store.create(
                        TaskRequest(
                            session_id=sid,
                            request_id=route.provider + str(index),
                            content="Synthetic benchmark observation",
                            cloud_consent=True,
                        )
                    )[0]
                    registry.observe(
                        route, task["task_id"], "TOOL_EXECUTION", True, True, 100 + index, 100
                    )
            measured_branch = []
            for _ in range(1000):
                tick = time.perf_counter()
                registry.choose(
                    selection,
                    Requirements(task_class="TOOL_EXECUTION", tools=True, context_tokens=6000),
                )
                measured_branch.append(1000 * (time.perf_counter() - tick))

            def summary(values):
                return {
                    "n": len(values),
                    "p50_ms": round(statistics.median(values), 4),
                    "p95_ms": round(sorted(values)[math.ceil(0.95 * len(values)) - 1], 4),
                    "max_ms": round(max(values), 4),
                }

            report = {
                "classification": "OFFLINE VERIFIED routing overhead only; synthetic model metadata/outcomes",
                "cold_store_and_registry_ms": round(cold_ms, 3),
                "warm_classification_and_selection": summary(timings),
                "warm_quality_ranking_branch": summary(measured_branch),
                "task_classes_exercised": sorted(outcomes),
                "model_quality_or_cloud_latency_measured": False,
                "cloud_requests": 0,
                "dependencies_added": 0,
            }
            report["implementation"] = implementation_provenance()
            report["evidence_path"] = str(
                write_engineering_evidence(report, "router-benchmark", output)
            )
            print(json.dumps(report))
        finally:
            store.db.close()


if __name__ == "__main__":
    main()
