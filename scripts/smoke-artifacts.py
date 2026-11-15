"""Synthetic, clearly labelled artifact acceptance; no model or network calls."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.artifacts import Artifacts
from immortility_broker.research import SOURCES


async def main():
    root = ROOT / ".cache/artifact-fixture"
    root.mkdir(parents=True, exist_ok=True)
    store = Artifacts(root)
    tid = str(uuid4())
    sources = [{"source_id": "mcp-security", "title": "Synthetic fixture reference not researched claims", "url": SOURCES["mcp-security"][1], "sha256": "0"*64, "retrieved_at": "synthetic fixture only"}]
    draft = {"title": "Synthetic Artifact Verification Fixture", "summary": "This synthetic fixture checks report construction and validation. It is not a researched security recommendation and must not be treated as a completed public research task. The content tests editable text and stable source references.", "sections": [{"heading": "Construction checks", "paragraphs": ["The report worker constructs real Markdown, PDF and DOCX files from plain structured text. This synthetic paragraph deliberately identifies itself as test data. File existence alone does not establish successful rendering or factual research. The caller must inspect the actual recorded verification status before publishing a deliverable."], "citations": ["mcp-security"]}, {"heading": "Verification checks", "paragraphs": ["The PDF is reopened, its text is compared with the input, and every page is rasterized. The editable Markdown is hashed after publication. The DOCX file is reopened structurally but remains unpublished because an independently verified renderer is unavailable in this environment."], "citations": ["mcp-security"]}]}
    result = await store.create(tid, draft, sources)
    assert await store.create(tid, draft, sources) == result
    assert {item["artifact_id"] for item in result["artifacts"]} == {"report.md", "report.pdf"}
    for item in result["artifacts"]:
        data, mime = store.read(tid, item["artifact_id"])
        assert data and mime
    print(json.dumps({"status": "passed", "classification": "VERIFIED LOCAL INTEGRATION, synthetic content only", "directory": str(store.directory(tid)), "result": result, "docx_publication": "disabled pending renderer", "cloud_calls": 0}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
