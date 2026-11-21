"""K25 measurement on the real INFERNAL worker (render to file, never plays audio).

cold: fresh worker → render.  warm: fresh worker → warm (silent) → render.
Run with the isolated runtime: .venv-infernal\\Scripts\\python.exe scripts\\infernal-warm-bench.py OUT.json
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.infernal import PRESETS  # noqa: E402

MODELS = Path.home() / "AppData/Local/Immortility/models"
TEXT = "The local model answered in under a second. Nothing left this computer."


def exchange(proc, request):
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    while line := proc.stdout.readline():
        frame = json.loads(line)
        if frame["kind"] in {"done", "error"}:
            return frame
    return {"kind": "lost"}


def run(warm_first):
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}  # same allowlist as voice.py
    env.update(
        PYTHONPATH=str(ROOT / "services/broker/src"),
        PYTHONUTF8="1",
        PYTHONUNBUFFERED="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        OMP_NUM_THREADS="2",
    )
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "immortility_broker.voice_worker"],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    preset = {k: v for k, v in PRESETS["ultron_conversational"].items()}
    base = {
        "voice": "infernal",
        "models": str(MODELS),
        "keep_alive": True,
        "infernal_authorized": True,
        **preset,
    }
    out = {}
    try:
        if warm_first:
            frame = exchange(proc, {**base, "operation": "warm"})
            out["warm_ms"] = round((time.perf_counter() - t0) * 1000)
            out["warm_frame"] = frame
        path = Path(tempfile.gettempdir()) / f"imm-k25-{int(warm_first)}.wav"
        t1 = time.perf_counter()
        frame = exchange(proc, {**base, "operation": "render", "text": TEXT, "path": str(path)})
        out["render_after_request_ms"] = round((time.perf_counter() - t1) * 1000)
        out["render_frame"] = frame
        out["wav_bytes"] = path.stat().st_size if path.exists() else 0
        path.unlink(missing_ok=True)
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return out


result = {"note": "render-to-file; no audio played", "cold": run(False), "warm": run(True)}
Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=1))
