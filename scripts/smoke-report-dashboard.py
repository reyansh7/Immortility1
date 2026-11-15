"""Show an already verified public-source fixture in the isolated native dashboard.

Local-only broker, no provider/vault loading, no new agent task. Owned processes
are reaped on exit; the completed fixture and its editable exports are retained.
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.process_owner import reap, spawn_owned


async def main(seconds):
    evidence = json.loads(
        (ROOT / "docs/implementation/M2_REPORT_PUBLIC_SOURCE_SMOKE.json").read_text()
    )
    root = Path(evidence["directory"]).parents[1].resolve()
    assert root.is_relative_to((ROOT / ".cache/report-workflows").resolve())
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    env.update(
        PYTHONPATH=str(ROOT / "services/broker/src"),
        PYTHONUTF8="1",
        PYTHONUNBUFFERED="1",
        USERPROFILE=str(root),
        LOCALAPPDATA=str(root),
        APPDATA=str(root),
    )
    children = []
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        broker, owner = await spawn_owned(
            sys.executable,
            "-m",
            "immortility_broker",
            "--headless",
            "--local-workflows",
            "--data-dir",
            str(root),
            "--publish-attachment",
            cwd=ROOT,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=flags,
        )
        children.append((broker, owner))
        line = await asyncio.wait_for(broker.stdout.readline(), 15)
        if not line:
            diagnostic = await asyncio.wait_for(broker.stderr.read(4000), 2)
            print(diagnostic.decode(errors="replace"), flush=True)
            raise RuntimeError("Isolated local-only broker failed before publication.")
        ready = json.loads(line)
        assert set(ready) == {"status", "instance_id"} and ready["status"] == "background-ready"
        broker.stdin.close()
        vite, owner = await spawn_owned(
            shutil.which("node") or "node",
            str(ROOT / "apps/desktop/node_modules/vite/bin/vite.js"),
            "preview",
            "--host",
            "127.0.0.1",
            "--port",
            "1420",
            "--strictPort",
            cwd=ROOT / "apps/desktop",
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=flags,
        )
        children.append((vite, owner))
        async with asyncio.timeout(15), httpx.AsyncClient(trust_env=False, timeout=1) as client:
            while True:
                if vite.returncode is not None:
                    raise RuntimeError(
                        "Isolated frontend could not start; existing port was not changed."
                    )
                try:
                    response = await client.get("http://127.0.0.1:1420")
                    if response.status_code == 200 and response.text == (
                        ROOT / "apps/desktop/dist/index.html"
                    ).read_text(encoding="utf-8"):
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
        native, owner = await spawn_owned(
            str(ROOT / "apps/desktop/src-tauri/target/debug/immortility-desktop.exe"),
            "--local-background-test-root",
            str(root),
            cwd=ROOT,
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=flags,
        )
        children.append((native, owner))
        print(
            json.dumps(
                {
                    "status": "ready for native UI inspection",
                    "root": str(root),
                    "native_pid": native.pid,
                    "seconds_available": seconds,
                    "cloud_calls": 0,
                }
            ),
            flush=True,
        )
        try:
            await asyncio.wait_for(native.wait(), seconds)
        except TimeoutError:
            pass
    finally:
        for process, owner in reversed(children):
            await reap(process, owner)
        print('{"status":"owned native fixture processes stopped"}', flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hold-seconds", type=int, default=180, choices=range(30, 601))
    asyncio.run(main(parser.parse_args().hold_seconds))
