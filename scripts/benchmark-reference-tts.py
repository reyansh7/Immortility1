"""Explicit local evaluation controller. Owns, bounds and reaps only its own TTS worker."""

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.reference_contracts import ReferenceRequest, sha256


class Worker:
    def __init__(self):
        self.frames = queue.Queue()
        folder = ROOT / ".cache/reference-tts"
        self.log_path = folder / ("worker-errors-" + uuid.uuid4().hex[:10] + ".log")
        self.log = self.log_path.open("w", encoding="utf-8")
        self.peak_rss = 0
        self.stop_sampling = threading.Event()
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            in {
                "SYSTEMROOT",
                "WINDIR",
                "PATH",
                "TEMP",
                "TMP",
                "USERPROFILE",
                "LOCALAPPDATA",
                "APPDATA",
            }
        }
        env.update(
            PYTHONPATH=str(ROOT / "services/broker/src"),
            PYTHONUTF8="1",
            PYTHONUNBUFFERED="1",
            IMMORTILITY_REFERENCE_EVALUATION="1",
            IMMORTILITY_REFERENCE_PROFILE="1",
            TORCH_FORCE_WEIGHTS_ONLY_LOAD="1",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            HF_HOME=str(folder / "hf"),
            TORCH_HOME=str(folder / "torch"),
            WANDB_MODE="disabled",
            TOKENIZERS_PARALLELISM="false",
            OMP_NUM_THREADS="2",
        )
        self.process = subprocess.Popen(
            [
                str(ROOT / ".venv-reference-tts/Scripts/python.exe"),
                "-m",
                "immortility_broker.reference_worker",
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            text=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        self.monitor = threading.Thread(target=self.sample_memory, daemon=True)
        self.monitor.start()

    def sample_memory(self):
        import psutil

        process = psutil.Process(self.process.pid)
        while not self.stop_sampling.wait(0.05):
            try:
                self.peak_rss = max(self.peak_rss, process.memory_info().rss)
            except psutil.NoSuchProcess:
                return

    def read(self):
        for line in self.process.stdout:
            try:
                self.frames.put(json.loads(line))
            except ValueError:
                self.frames.put({"kind": "error", "code": "invalid_worker_protocol"})
        self.frames.put({"kind": "eof"})

    def send(self, run_id, case, reference="conditioned"):
        request = ReferenceRequest(
            evaluation_authorized=True,
            run_id=run_id,
            case=case,
            reference=reference,
            model_manifest_sha256=sha256(ROOT / "config/reference-tts-models.json"),
            reference_manifest_sha256=sha256(ROOT / "data/reference-tts/reference/reference.json"),
        )
        self.process.stdin.write(request.model_dump_json() + "\n")
        self.process.stdin.flush()

    def next(self, deadline):
        frame = self.frames.get(timeout=max(0.01, deadline - time.perf_counter()))
        if frame["kind"] in {"error", "eof"}:
            raise RuntimeError(
                "Reference worker failed; see " + str(self.log_path) + ": " + str(frame)
            )
        return frame

    def close(self):
        start = time.perf_counter()
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=3)
        self.reader.join(timeout=1)
        self.stop_sampling.set()
        self.monitor.join(timeout=1)
        if not self.log.closed:
            self.log.close()
        return (time.perf_counter() - start) * 1000


def main():
    import psutil

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--cancel-tests", action="store_true")
    args = parser.parse_args()
    cases = json.loads((ROOT / "config/reference-tts-evaluation.json").read_text())
    run_id = "eval-" + uuid.uuid4().hex[:12]
    worker = Worker()
    records = []
    try:
        for case in list(cases) if args.all else ["normal"]:
            started = time.perf_counter()
            worker.send(run_id, case)
            first = None
            peak_rss = 0
            deadline = started + 240
            while True:
                peak_rss = max(peak_rss, psutil.Process(worker.process.pid).memory_info().rss)
                frame = worker.next(deadline)
                if frame["kind"] == "chunk" and first is None:
                    first = time.perf_counter() - started
                if frame["kind"] == "done":
                    frame.update(
                        request_to_first_chunk_seconds=first,
                        total_wall_seconds=time.perf_counter() - started,
                        external_sampler_mib=max(peak_rss, worker.peak_rss) / 1024**2,
                    )
                    records.append(frame)
                    print(json.dumps(frame), flush=True)
                    break
        if args.cancel_tests:
            worker.send("cancel-" + uuid.uuid4().hex[:12], "dramatic")
            while worker.next(time.perf_counter() + 90)["kind"] != "chunk":
                pass
            records.append(
                {
                    "kind": "cancel",
                    "phase": "streaming_generation",
                    "stop_ms": worker.close(),
                    "reaped": worker.process.returncode is not None,
                }
            )
    except BaseException as error:
        failure = {
            "run_id": run_id,
            "results": records,
            "error_type": type(error).__name__,
            "worker_log": str(worker.log_path),
        }
        (ROOT / "data/audits" / (run_id + "-failed.json")).write_text(
            json.dumps(failure, indent=2) + "\n"
        )
        raise
    finally:
        worker.close()
    if args.cancel_tests:
        loading = Worker()
        try:
            loading.send("cancel-load-" + uuid.uuid4().hex[:8], "normal")
            while True:
                frame = loading.next(time.perf_counter() + 120)
                if frame.get("state") == "loading_weights":
                    break
            records.append(
                {
                    "kind": "cancel",
                    "phase": "loading_weights",
                    "stop_ms": loading.close(),
                    "reaped": loading.process.returncode is not None,
                }
            )
        finally:
            if loading.process.poll() is None:
                loading.close()
    report = {"run_id": run_id, "results": records, "new_default": False, "qwen_enabled": False}
    (ROOT / "data/audits" / (run_id + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "data/audits/reference-tts-latest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Evaluation report:", run_id, flush=True)


if __name__ == "__main__":
    main()
