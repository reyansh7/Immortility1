"""M2/P4 screen-target benchmark on REAL windows this script opens itself.

Opens (and afterwards closes) its own Notepad window, a local HTML page and a local PDF in a
separate Edge instance with a throwaway profile under %TEMP%. Ground truth comes from UIA
FindText in those windows (scripts/screen_ground_truth.py); each case then calls the product
path (``screen_target.read_target``: hash-pinned UIA worker, OCR fallback) at that point.
Never captures password contents: the password case asserts a refusal and that the secret
value appears nowhere in the result. No cloud, no model. Records whether the PC was in use.

Usage (broker venv): python scripts/benchmark-screen-target.py --out FILE
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from ctypes import wintypes as w
from datetime import datetime
from pathlib import Path

from immortility_broker.config import ROOT
from immortility_broker.screen_target import ScreenAccess, TargetRequest, read_target

OBSERVER = ROOT / ".venv-observer/Scripts/python.exe"
SECRET = "hunter2-BENCH-secret"
NOTE = (
    "Immortility hover benchmark alpha line\r\n"
    "The quick brown fox jumps over the lazy dog\r\n"
    "Photosynthesis converts light energy into chemical energy\r\n"
    "Serendipity means finding something good without looking for it\r\n"
)
HTML = f"""<!doctype html><html><head><meta charset="utf-8"><title>ImmScreenBench Page</title>
<style>body{{font:20px Segoe UI, Arial;margin:24px}} p{{margin:10px 0}}</style></head><body>
<h1>Screen target benchmark</h1>
<p>An ephemeral cache keeps ubiquitous data close to the algorithm that needs it.</p>
<p>The mitochondria regulate cellular entropy during metabolism.</p>
<label>Account password <input type="password" value="{SECRET}" style="font-size:20px"></label>
<p><button style="font-size:20px">Submit order</button></p>
<div style="font:16px Arial">CANVASANCHOR</div>
<canvas id="c" width="420" height="90" style="display:block"></canvas>
<script>const g=document.getElementById('c').getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,420,90);
g.fillStyle='#000';g.font='bold 46px Arial';g.fillText('QUANTUM',12,62);</script>
</body></html>"""


def pdf_bytes(lines: list[str]) -> bytes:
    text = "BT /F1 24 Tf 72 720 Td 30 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for index, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", w.UINT), ("dwTime", w.DWORD)]


def idle_ms() -> int:
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return int(ctypes.windll.kernel32.GetTickCount() - info.dwTime)


def pids(name: str) -> set[int]:
    out = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH", "/FI", f"IMAGENAME eq {name}"],
        capture_output=True,
        text=True,
    ).stdout
    found = set()
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[1].isdigit():
            found.add(int(parts[1]))
    return found


def truth(title: str, **request) -> dict:
    run = subprocess.run(
        [str(OBSERVER), "-I", str(ROOT / "scripts/screen_ground_truth.py")],
        input=json.dumps({"title": title, "topmost": True, **request}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (
        json.loads(run.stdout.strip().splitlines()[-1])
        if run.stdout.strip()
        else {"error": run.stderr[-200:]}
    )


async def probe(point: dict | None, unit: str = "word", selection: bool = False) -> dict:
    if not point or point.get("occluded", True):
        # Never read a point that is not on this benchmark's own window (user content).
        return {"target": "", "source": "skipped_occluded" if point else "no_ground_truth"}
    access = ScreenAccess()
    request = TargetRequest(
        x=point["x"] if point else None,
        y=point["y"] if point else None,
        unit=unit,
        selection=selection,
    )
    return await read_target(request, access)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    work = Path(tempfile.gettempdir()) / "imm-screen-bench"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    (work / "ImmScreenBench-notes.txt").write_text(NOTE, encoding="utf-8")
    (work / "page.html").write_text(HTML, encoding="utf-8")
    (work / "ImmScreenBench.pdf").write_bytes(
        pdf_bytes(
            [
                "Thermodynamics describes energy and work.",
                "Chemical equilibrium balances reactions.",
            ]
        )
    )
    cases: list[dict] = []
    usage = {"idle_ms_samples": []}
    started_procs: list[subprocess.Popen] = []
    notepad_before = pids("notepad.exe")
    edge_cmd = None

    def record(name, app, result, ok, expected):
        cases.append(
            {
                "name": name,
                "app": app,
                "passed": bool(ok),
                "expected": expected,
                "got": result.get("target", ""),
                "source": result.get("source"),
                "denied": result.get("denied"),
                "exact": result.get("exact"),
                "elapsed_ms": result.get("elapsed_ms"),
                "uia_ms": result.get("uia_ms"),
                "ocr_ms": result.get("ocr_ms"),
                "idle_ms_before": usage["idle_ms_samples"][-1],
            }
        )

    def run_words(app, title, words, unit_line=None):
        gt = truth(title, find=list(words) + ([unit_line] if unit_line else []))
        if "error" in gt:
            for word in words:
                cases.append(
                    {
                        "name": f"{app}: {word}",
                        "app": app,
                        "passed": False,
                        "expected": word,
                        "got": "",
                        "error": gt["error"],
                    }
                )
            return gt
        for word in words:
            point = gt["points"].get(word)
            usage["idle_ms_samples"].append(idle_ms())
            result = (
                asyncio.run(probe(point)) if point else {"target": "", "error": "no_ground_truth"}
            )
            record(
                f"{app}: word {word}",
                app,
                result,
                result.get("target", "").strip(" .,").casefold() == word.casefold(),
                word,
            )
        if unit_line:
            point = gt["points"].get(unit_line)
            usage["idle_ms_samples"].append(idle_ms())
            result = asyncio.run(probe(point, unit="line")) if point else {"target": ""}
            record(
                f"{app}: line containing {unit_line}",
                app,
                result,
                unit_line in result.get("target", "")
                and len(result.get("target", "")) > len(unit_line) + 10,
                f"line with {unit_line}",
            )
        return gt

    try:
        # ---- Notepad (skipped if the user already has Notepad open: never touch their window)
        if notepad_before:
            cases.append(
                {
                    "name": "notepad: skipped (user's Notepad is open)",
                    "app": "notepad",
                    "passed": None,
                    "skipped": True,
                }
            )
        else:
            started_procs.append(
                subprocess.Popen(["notepad.exe", str(work / "ImmScreenBench-notes.txt")])
            )
            time.sleep(2.5)
            run_words(
                "notepad",
                "ImmScreenBench-notes",
                ["Photosynthesis", "Serendipity", "brown", "lazy", "chemical", "benchmark"],
                unit_line="converts",
            )
            gt = truth("ImmScreenBench-notes", select="Serendipity")
            usage["idle_ms_samples"].append(idle_ms())
            result = (
                asyncio.run(
                    probe(gt.get("points", {}).get("Photosynthesis") or None, selection=True)
                )
                if gt.get("selected")
                else {}
            )
            ok = result.get("selection", "").strip() == "Serendipity"
            cases.append(
                {
                    "name": "notepad: selected text",
                    "app": "notepad",
                    "passed": ok,
                    "expected": "Serendipity",
                    "got": result.get("selection", ""),
                    "elapsed_ms": result.get("elapsed_ms"),
                    "idle_ms_before": usage["idle_ms_samples"][-1],
                }
            )
        # ---- Edge: own instance, throwaway profile
        edge = next(
            (
                p
                for p in [
                    Path(os.environ.get("ProgramFiles(x86)", ""))
                    / "Microsoft/Edge/Application/msedge.exe",
                    Path(os.environ.get("ProgramFiles", ""))
                    / "Microsoft/Edge/Application/msedge.exe",
                ]
                if p.is_file()
            ),
            None,
        )
        if edge is None:
            cases.append(
                {"name": "edge: unavailable", "app": "edge", "passed": None, "skipped": True}
            )
        else:
            profile = work / "edge-profile"
            edge_cmd = [
                str(edge),
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--force-renderer-accessibility",
                "--window-size=1100,900",
                "--window-position=60,40",
            ]
            started_procs.append(
                subprocess.Popen(edge_cmd + [f"--app={(work / 'page.html').as_uri()}"])
            )
            time.sleep(4)
            gt = run_words(
                "edge-html",
                "ImmScreenBench Page",
                ["ephemeral", "ubiquitous", "algorithm", "mitochondria", "entropy"],
                unit_line="cellular",
            )
            pw = truth("ImmScreenBench Page", password=True)
            point = pw.get("points", {}).get("__password__")
            usage["idle_ms_samples"].append(idle_ms())
            result = asyncio.run(probe(point, selection=True)) if point else {}
            leaked = SECRET in json.dumps(result) or "hunter2" in json.dumps(result)
            record(
                "edge-html: password field refused, no leak",
                "edge-html",
                result,
                bool(point) and result.get("denied") == "password_field" and not leaked,
                "denied",
            )
            cases[-1]["leaked"] = leaked
            anchor = gt.get("points", {}).get("CANVASANCHOR") if gt else None
            if anchor is None:
                anchor = (
                    truth("ImmScreenBench Page", find=["CANVASANCHOR"])
                    .get("points", {})
                    .get("CANVASANCHOR")
                )
            if anchor:
                scale = (truth("ImmScreenBench Page").get("dpi") or 96) / 96
                point = {
                    "x": int(anchor["left"] + 90 * scale),
                    "y": int(anchor["bottom"] + 45 * scale),
                }
                point = truth("ImmScreenBench Page", check=[point])["points"]["__check_0__"]
                usage["idle_ms_samples"].append(idle_ms())
                result = asyncio.run(probe(point))
                record(
                    "edge-html: canvas text via OCR fallback",
                    "edge-html",
                    result,
                    result.get("source") == "ocr"
                    and "quantum" in result.get("target", "").casefold(),
                    "QUANTUM",
                )
            gt = truth("ImmScreenBench Page", find=["Submit order"])
            point = gt.get("points", {}).get("Submit order")
            usage["idle_ms_samples"].append(idle_ms())
            result = asyncio.run(probe(point)) if point else {}
            record(
                "edge-html: button label",
                "edge-html",
                result,
                "submit" in result.get("target", "").casefold(),
                "Submit / Submit order",
            )
            # PDF in the same isolated instance
            started_procs.append(
                subprocess.Popen(edge_cmd + [f"--app={(work / 'ImmScreenBench.pdf').as_uri()}"])
            )
            time.sleep(5)
            run_words("edge-pdf", "ImmScreenBench", ["Thermodynamics", "equilibrium"])
    finally:
        for proc in started_procs:
            with __import__("contextlib").suppress(Exception):
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        for pid in pids("notepad.exe") - notepad_before:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        # Edge children of our throwaway profile only
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                "Where-Object { $_.CommandLine -like '*imm-screen-bench*' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
            ],
            capture_output=True,
        )
        time.sleep(1)
        shutil.rmtree(work, ignore_errors=True)

    scored = [c for c in cases if c.get("passed") is not None]
    times = [c["elapsed_ms"] for c in scored if isinstance(c.get("elapsed_ms"), (int, float))]
    uia_only = [
        c["elapsed_ms"]
        for c in scored
        if c.get("source") in {"uia_text", "uia_name"}
        and isinstance(c.get("elapsed_ms"), (int, float))
    ]
    report = {
        "benchmark": "m2-p4-screen-target",
        "inference": "none (local UIA/OCR; no cloud, no model)",
        "windows": "real Notepad / Edge(--app, throwaway profile) windows opened and closed by this script",
        "finished": datetime.now().astimezone().isoformat(),
        "passed": sum(bool(c["passed"]) for c in scored),
        "total": len(scored),
        "skipped": [c["name"] for c in cases if c.get("passed") is None],
        "latency_ms": {
            "all_p50": round(statistics.median(times), 1) if times else None,
            "all_max": max(times) if times else None,
            "uia_p50": round(statistics.median(uia_only), 1) if uia_only else None,
        },
        "pc_in_use": {
            "min_idle_ms_before_case": min(usage["idle_ms_samples"] or [0]),
            "cases_with_input_in_last_2s": sum(1 for v in usage["idle_ms_samples"] if v < 2000),
        },
        "cases": cases,
    }
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    leftovers = pids("notepad.exe") - notepad_before
    print(json.dumps({"leftover_notepad": sorted(leftovers)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
