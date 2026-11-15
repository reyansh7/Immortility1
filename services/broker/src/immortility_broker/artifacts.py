"""Scoped, on-demand report publication. Model input contains no path or executable."""

import asyncio
import hashlib
import json
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path
from itertools import islice
from typing import Any, Literal, Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from .capabilities import StrictModel
from .config import ROOT
from .contracts import BrokerError
from .process_owner import reap, spawn_owned
from .workspace import _directory_guard, _read_bytes


class ReportSection(StrictModel):
    heading: str = Field(pattern=r"^[A-Za-z0-9 ]{3,80}$")
    paragraphs: list[str] = Field(min_length=1, max_length=4)
    citations: list[str] = Field(min_length=1, max_length=3)


class ReportInput(StrictModel):
    title: str = Field(pattern=r"^[A-Za-z0-9 ]{3,100}$")
    summary: str = Field(min_length=80, max_length=1000)
    sections: list[ReportSection] = Field(min_length=2, max_length=5)


def minimum_report_output_reservation() -> int:
    """Conservative headroom for one minimum ASCII proposal, not token calibration.

    500 prose characters, two distinct paragraphs, longest reviewed citation ID,
    JSON scaffolding, and the existing 64+32 envelope allowance. This is only an
    admission floor; it cannot guarantee a model produces a complete good report.
    """
    draft = ReportInput(
        title="Report",
        summary="S" * 80,
        sections=[
            ReportSection(
                heading=heading, paragraphs=[letter * 210], citations=["mcp-authorization"]
            )
            for heading, letter in (("One", "A"), ("Two", "B"))
        ],
    )
    proposal = {"capability": "report.create.v1", "arguments": draft.model_dump()}
    return len(json.dumps(proposal, separators=(",", ":"), ensure_ascii=False).encode()) + 96


class ArtifactRef(StrictModel):
    artifact_id: Literal["report.md", "report.pdf"]
    size: int = Field(ge=1, le=8000000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verification: Literal["reopened", "reopened-and-rendered"]


class ReportOutput(StrictModel):
    artifacts: list[ArtifactRef] = Field(min_length=2, max_length=2)
    pdf_pages: int = Field(ge=1, le=8)
    docx_available: Literal[False] = False

    @model_validator(mode="after")
    def published_pair(self) -> Self:
        actual = {ref.artifact_id: ref.verification for ref in self.artifacts}
        if actual != {"report.md": "reopened", "report.pdf": "reopened-and-rendered"}:
            raise ValueError("Both reviewed report formats need their required verification")
        return self


def reviewed_runtime() -> tuple[Path, Path]:
    python = ROOT / ".venv-artifacts/Scripts/python.exe"
    script = ROOT / "integrations/artifacts/report_worker.py"
    try:
        manifest = json.loads((ROOT / "config/artifact-runtime.json").read_text())
        for name, digest in manifest["files"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError
        if hashlib.sha256(python.read_bytes()).hexdigest() != manifest["python_sha256"]:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise BrokerError(
            "artifact_unavailable", "Reviewed report runtime is unavailable or changed.", 503
        ) from None
    return python, script


class Artifacts:
    def __init__(self, data_root: Path):
        self.root = data_root / "artifacts"

    def directory(self, task_id: str) -> Path:
        try:
            valid = str(UUID(task_id)) == task_id
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise BrokerError("tool_denied", "Invalid artifact scope.", 403)
        return self.root / task_id

    def editable_copy(self, task_id: str, artifact_id: str) -> dict[str, Any]:
        data, _ = self.read(task_id, artifact_id)
        folder = self.directory(task_id) / "copies"
        ident = str(uuid4())
        path = folder / (ident + Path(artifact_id).suffix)
        with _directory_guard(folder.parent):
            folder.mkdir(exist_ok=True)
            with _directory_guard(folder):
                if sum(1 for _ in islice(folder.iterdir(), 20)) >= 20:
                    raise BrokerError(
                        "artifact_limit", "This task already has twenty editable copies.", 409
                    )
                with path.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if _read_bytes(path, 8000000) != data:
                    raise BrokerError("artifact_changed", "Artifact copy readback failed.", 409)
        return {
            "copy_id": ident,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "extension": Path(artifact_id).suffix,
            "open_allowed": True,
        }

    def receipt(self, task_id: str) -> dict[str, Any]:
        folder = self.directory(task_id)
        try:
            with _directory_guard(folder):
                receipt = json.loads(_read_bytes(folder / "receipt.json", 16000))
                result = ReportOutput.model_validate(receipt["result"])
                if receipt["task_id"] != task_id:
                    raise ValueError
                for item in result.artifacts:
                    data = _read_bytes(folder / item.artifact_id, 8000000)
                    if len(data) != item.size or hashlib.sha256(data).hexdigest() != item.sha256:
                        raise ValueError
            return dict(receipt)
        except (OSError, ValueError, KeyError, TypeError):
            raise BrokerError(
                "artifact_unavailable", "Artifact readback or scope verification failed.", 503
            ) from None

    def read(self, task_id: str, artifact_id: str) -> tuple[bytes, str]:
        receipt = self.receipt(task_id)
        if artifact_id not in {item["artifact_id"] for item in receipt["result"]["artifacts"]}:
            raise BrokerError("tool_denied", "Artifact is not published for this task.", 403)
        with _directory_guard(self.directory(task_id)):
            data = _read_bytes(self.directory(task_id) / artifact_id, 8000000)
            expected = next(
                item["sha256"]
                for item in receipt["result"]["artifacts"]
                if item["artifact_id"] == artifact_id
            )
            if hashlib.sha256(data).hexdigest() != expected:
                raise BrokerError("artifact_changed", "Published artifact changed.", 409)
        return data, "application/pdf" if artifact_id.endswith(
            ".pdf"
        ) else "text/markdown; charset=utf-8"

    async def create(
        self, task_id: str, arguments: dict[str, Any], sources: list[dict[str, Any]]
    ) -> dict[str, Any]:
        draft = ReportInput.model_validate(arguments)
        expected_ids = {source["source_id"] for source in sources}
        if not sources or any(
            not set(section.citations) <= expected_ids for section in draft.sections
        ):
            raise BrokerError(
                "source_unverified",
                "Every report section needs actually retrieved source references.",
                403,
            )
        encoded = draft.model_dump_json().encode()
        if len(encoded) > 16000 or any(
            not 20 <= len(p) <= 1200 for section in draft.sections for p in section.paragraphs
        ):
            raise BrokerError("input_limit", "Report draft exceeds the short-report contract.", 413)
        digest = hashlib.sha256(encoded).hexdigest()
        target = self.directory(task_id)
        if target.exists():
            existing = self.receipt(task_id)
            if existing["draft_sha256"] != digest:
                raise BrokerError(
                    "idempotency_conflict", "This task already published a different report.", 409
                )
            return dict(existing["result"])
        python, script = reviewed_runtime()
        with _directory_guard(self.root.parent):
            self.root.mkdir(exist_ok=True)
        with (
            _directory_guard(self.root),
            tempfile.TemporaryDirectory(prefix=".building-", dir=self.root) as directory,
        ):
            stage = Path(directory)
            env = {
                key: value
                for key, value in os.environ.items()
                if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
            }
            env.update(
                PYTHONUTF8="1",
                PYTHONUNBUFFERED="1",
                HF_HUB_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="",
                USERPROFILE=directory,
                LOCALAPPDATA=directory,
                APPDATA=directory,
            )
            process, owner = await spawn_owned(
                str(python),
                "-I",
                "-B",
                "-X",
                "pycache_prefix=" + str(stage / "bytecode"),
                str(script),
                cwd=directory,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                job_memory_limit=512 * 1024**2,
            )
            started = time.monotonic()
            reaped = False
            try:
                async with asyncio.timeout(25):
                    assert process.stdin and process.stdout
                    process.stdin.write(
                        (
                            json.dumps(
                                {
                                    "output_dir": directory,
                                    "draft": draft.model_dump(),
                                    "sources": sources,
                                }
                            )
                            + "\n"
                        ).encode()
                    )
                    await process.stdin.drain()
                    process.stdin.close()
                    line = await process.stdout.readline()
                    if len(line) > 16000:
                        raise ValueError
                    built = json.loads(line)
                    await process.wait()
                    if (
                        process.returncode != 0
                        or not built.get("pdf_rendered")
                        or built.get("error")
                    ):
                        raise ValueError
                    refs = [
                        ArtifactRef(
                            artifact_id=file["name"],
                            size=file["size"],
                            sha256=file["sha256"],
                            verification="reopened-and-rendered"
                            if file["name"] == "report.pdf"
                            else "reopened",
                        )
                        for file in built["files"]
                        if file["publication_allowed"]
                    ]
                    result = ReportOutput(artifacts=refs, pdf_pages=built["pdf_pages"])
                    receipt = {
                        "task_id": task_id,
                        "draft_sha256": digest,
                        "sources": sources,
                        "result": result.model_dump(),
                        "worker_ms": round(1000 * (time.monotonic() - started), 2),
                        "docx_status": "structure verified; renderer unavailable; publication disabled",
                    }
                    # Numeric, fixed-key observations only; never copy worker bodies.
                    timings = built.get("timing_ms", {})
                    receipt["worker_phases_ms"] = {
                        key: timings[key]
                        for key in (
                            "dependency_import",
                            "construction",
                            "readback",
                            "rendering",
                            "hashing",
                        )
                        if isinstance(timings, dict)
                        and type(timings.get(key)) in {int, float}
                        and math.isfinite(timings[key])
                        and 0 <= timings[key] <= 60000
                    }
                    try:
                        receipt["worker_resources"] = owner.statistics()
                    except OSError:
                        pass
                    # Commit complete metadata before atomic publication; no user file overwritten.
                    with (stage / "receipt.json").open("x", encoding="utf-8") as stream:
                        json.dump(receipt, stream)
                        stream.flush()
                        os.fsync(stream.fileno())
                    # Finish every cancellable await before publication. The caller
                    # checkpoints synchronously on return, closing the Stop race.
                    await reap(process, owner)
                    reaped = True
                    if target.exists():
                        raise BrokerError(
                            "idempotency_conflict", "Concurrent artifact publication refused.", 409
                        )
                    os.rename(stage, target)
                    self.receipt(task_id)  # Independently reopen and hash published files.
                    return result.model_dump(mode="json")
            except (OSError, ValueError, KeyError, TimeoutError):
                raise BrokerError(
                    "artifact_failed",
                    "Report construction or verification failed; no completion claimed.",
                    503,
                ) from None
            finally:
                if not reaped:
                    await reap(process, owner)
