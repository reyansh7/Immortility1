"""Own one native app for an idle benchmark, then verify descendant cleanup."""

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "apps/desktop/src-tauri/target/debug/immortility-desktop.exe"


def powershell(command: str) -> str:
    return subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", command],
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=20,
    ).strip()


def main(seconds: int, output: str) -> None:
    if powershell("@(Get-Process immortility-desktop -ErrorAction SilentlyContinue).Count") != "0":
        raise SystemExit("Close the existing Immortility instance before this owned benchmark.")
    started = time.monotonic()
    process = subprocess.Popen(
        [str(EXE)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    launch_ms = (time.monotonic() - started) * 1000
    children = []
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts/benchmark-idle.ps1"),
                "-AppPid",
                str(process.pid),
                "-DurationSeconds",
                str(seconds),
                "-Output",
                output,
            ],
            cwd=ROOT,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        encoded = powershell(
            f"$ids=@({process.pid}); $all=Get-CimInstance Win32_Process; "
            "for($i=0;$i -lt 8;$i++){foreach($p in $all){if($ids -contains $p.ParentProcessId "
            "-and $ids -notcontains $p.ProcessId){$ids+=$p.ProcessId}}}; "
            "$ids | ConvertTo-Json -Compress"
        )
        children = json.loads(encoded) if encoded else []
        if not isinstance(children, list):
            children = [children]
        if result.returncode:
            raise SystemExit(result.returncode)
    finally:
        if process.poll() is None:
            process.terminate()  # Exact owned process; native Job Object reaps descendants.
        process.wait(timeout=8)
        time.sleep(1)
        alive = []
        if children:
            encoded = powershell(
                "@(Get-Process -Id "
                + ",".join(map(str, children))
                + " -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"
            )
            alive = json.loads(encoded) if encoded else []
        report_path = ROOT / output
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            report["ProcessLaunchMilliseconds"] = round(launch_ms, 2)
            report["LaunchMetricMeaning"] = "CreateProcess only; not time to interactive UI"
            report["OwnedProcessesRemainingAfterStop"] = alive
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({k: v for k, v in report.items() if k != "Measurements"}, indent=2))
        if alive:
            raise SystemExit("Owned processes remained after native termination; see report.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--output", default="data/benchmarks/p0-current-idle.json")
    options = parser.parse_args()
    destination = (ROOT / options.output).resolve()
    if not destination.is_relative_to(ROOT) or not 10 <= options.seconds <= 86400:
        parser.error("Use a workspace-local output and a duration from 10 to 86400 seconds.")
    main(options.seconds, options.output)
