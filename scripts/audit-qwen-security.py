"""Read public OSV/PyPI metadata only; never load models, audio, credentials or PoCs."""

import argparse
import concurrent.futures
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/qwen-remediation/public"


def public_json(url: str, name: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}", name):
        raise ValueError("Invalid public metadata cache identifier")
    target = CACHE / f"{name}.json"
    if target.is_file():
        return json.loads(target.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": "Immortility-local-dependency-audit/1"})
    with urlopen(request, timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Public metadata exceeded size limit")
    payload = json.loads(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def osv(identifier: str) -> dict:
    return public_json(f"https://api.osv.dev/v1/vulns/{identifier}", identifier)


def assessment(package: str, identifier: str) -> str:
    """Reviewed call-path assessment, not an exploit or security-clearance claim."""
    if package == "pillow":
        return (
            "No image/PDF/font/Arrow input or processing operation is exposed by the reviewed "
            "Qwen worker; incidental PIL imports do not establish decoder reachability. "
            "Would become relevant if image processing or an arbitrary Python tool were enabled."
        )
    return {
        "PYSEC-2026-3804": (
            "Requires an attacker-controlled sharded checkpoint index. The existing pinned "
            "Qwen snapshot has single model.safetensors files, no shard indexes. No arbitrary "
            "checkpoint input is exposed; replacing/tampering with model files remains a risk."
        ),
        "PYSEC-2025-49": (
            "Requires setuptools PackageIndex.download on an attacker-controlled package URL. "
            "The speech worker does not install/download Python packages. Candidate update "
            "81.0.0 includes the 78.1.1 fix; original environment remains unchanged."
        ),
        "PYSEC-2026-3447": (
            "Requires sdist creation and Unicode normalization collisions on macOS APFS/HFS+. "
            "This Windows speech runtime does neither; affected package version still present."
        ),
        "GHSA-xmj3-9gf7-h52w": (
            "Windows-specific, but requires setuptools' legacy Wheel.install_as_egg on a "
            "malicious wheel. Runtime does not call it; uv installation does not use that "
            "legacy installer. Not a fix or assurance for arbitrary future package installs."
        ),
        "PYSEC-2025-217": (
            "X-CLIP checkpoint-conversion script is not called by the Qwen model path. "
            "Tensor-only private profile loading is a different code path."
        ),
        "PYSEC-2026-2290": (
            "LightGlue model initialization is not used; reviewed model is qwen3_tts. "
            "Arbitrary model/config substitution must stay forbidden."
        ),
        "PYSEC-2026-2288": (
            "Trainer._load_rng_state is not used and advisory requires PyTorch <2.6; "
            "installed Torch is 2.11.0+cu128. Those preconditions are absent."
        ),
        "PYSEC-2026-2289": (
            "Model loading IS used. Malicious attention configuration can bypass remote-code "
            "trust checks. Fixed model revision and explicit SDPA constrain current input, "
            "but the original loader permits network/cache access; no sandbox or verified "
            "artifact-integrity proof currently closes this risk. Keep disabled."
        ),
        "PYSEC-2026-3929": (
            "Requires save_pretrained with attacker-controlled chat-template names. Worker "
            "does not call model/tokenizer save_pretrained; profile torch.save is different."
        ),
        "PYSEC-2026-4174": (
            "Generation/model initialization IS used. Requires attacker-controlled custom "
            "generation metadata. Fixed revision constrains input, but downloading before "
            "trust consent means trust_remote_code=False alone is insufficient. Keep disabled "
            "until patched or artifact/network restrictions are independently verified."
        ),
    }[identifier]


def write_review(report: dict) -> None:
    reviewed = []
    for item in report["findings"]:
        row = {key: value for key, value in item.items() if key not in {"affected", "references"}}
        levels = [s["level"] for s in row["severity_sources"] if s["level"] != "UNKNOWN"]
        if row["id"] == "PYSEC-2025-217":
            row["summary"] = "X-CLIP checkpoint conversion: unsafe deserialization"
            row["severity"] = "HIGH"
            row["severity_reference"] = "https://www.zerodayinitiative.com/advisories/ZDI-25-1144/"
            row["cvss_base_score"] = 7.8
        else:
            row["severity"] = levels[0] if levels else "UNKNOWN"
            row["severity_reference"] = next(
                (
                    f"https://github.com/advisories/{s['source']}"
                    for s in row["severity_sources"]
                    if s["level"] != "UNKNOWN" and s["source"].startswith("GHSA-")
                ),
                row["url"],
            )
        row["current_exposure"] = "Broker Qwen activation disabled; no playback authorized."
        row["conditional_reachability"] = assessment(row["package"], row["id"])
        reviewed.append(row)
    result = {
        "date": report["collected_at"],
        "source": "pip-audit scan enriched from OSV and original advisory publishers",
        "entries": len(reviewed),
        "severity_counts": dict(Counter(row["severity"] for row in reviewed)),
        "runtime_enabled": False,
        "limitations": "Source/call-path assessment only. No exploit PoCs, synthesis or playback. "
        "Known CVSS disagreements are retained in severity_sources; HIGH for X-CLIP uses ZDI 7.8.",
        "findings": reviewed,
    }
    out = ROOT / "infra/security/qwen-advisories-reviewed.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Qwen advisory register — original environment, 2026-11-13",
        "",
        "All 52 original scan entries are listed individually. Severity is the publisher's "
        "GHSA level, except X-CLIP (ZDI CVSS 7.8, High). This is package severity, not a claim "
        "of an exploitable Immortility workflow. CVSS vectors and source disagreements are "
        "preserved in `infra/security/qwen-advisories-reviewed.json`.",
        "",
        "Qwen remains disabled. These assessments describe conditional reachability IF enabled. "
        "No advisory payloads were executed. No audio/profile was uploaded or re-created.",
        "",
        "| # | Package / installed | Entry and aliases | Severity | Issue | Conditional reachability |",
        "|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(reviewed, 1):
        identifiers = f"[{row['id']}]({row['url']})<br>" + ", ".join(row["aliases"])
        summary = row["summary"].replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {index} | {row['package']} {row['installed_version']} | {identifiers} | "
            f"[{row['severity']}]({row['severity_reference']}) | {summary} | "
            f"{row['conditional_reachability']} |"
        )
    (ROOT / "docs/security").mkdir(exist_ok=True)
    (ROOT / "docs/security/QWEN_ADVISORY_REGISTER.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, default=ROOT / "data/audits/qwen-advisories.json")
    args = parser.parse_args()
    scan = json.loads(args.scan.read_text(encoding="utf-8"))
    findings = [
        (package, finding)
        for package in scan["dependencies"]
        for finding in package.get("vulns", [])
    ]
    identifiers = sorted(
        {f["id"] for _, f in findings}
        | {
            alias
            for _, f in findings
            for alias in f.get("aliases", [])
            if alias.startswith("GHSA-")
        }
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(zip(identifiers, pool.map(osv, identifiers), strict=True))
    rows = []
    for package, finding in findings:
        record = records[finding["id"]]
        aliases = sorted(set(finding.get("aliases", [])) | set(record.get("aliases", [])))
        related = [record] + [records[a] for a in aliases if a in records]
        severities = [
            {
                "source": item["id"],
                "level": item.get("database_specific", {}).get("severity", "UNKNOWN"),
                "cvss": item.get("severity", []),
            }
            for item in related
            if item.get("database_specific", {}).get("severity") or item.get("severity")
        ]
        rows.append(
            {
                "package": package["name"],
                "installed_version": package["version"],
                "id": finding["id"],
                "aliases": aliases,
                "severity_sources": severities,
                "summary": next((r["summary"] for r in related if r.get("summary")), ""),
                "fix_versions": finding.get("fix_versions", []),
                "withdrawn": record.get("withdrawn"),
                "references": record.get("references", []),
                "affected": record.get("affected", []),
                "url": f"https://osv.dev/vulnerability/{finding['id']}",
            }
        )
    packages = {}
    for name in ("qwen-tts", "accelerate", "pillow", "setuptools", "transformers"):
        package = public_json(f"https://pypi.org/pypi/{name}/json", f"pypi-{name}")
        info = package["info"]
        packages[name] = {
            "latest": info["version"],
            "requires_python": info["requires_python"],
            "requires_dist": info.get("requires_dist"),
            "url": f"https://pypi.org/project/{name}/{info['version']}/",
        }
    report = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "scan": str(args.scan.relative_to(ROOT)),
        "entries": len(rows),
        "findings": rows,
        "pypi": packages,
        "scope": "Public advisory and package metadata only. Advisory PoCs were not executed.",
    }
    out = ROOT / "data/audits/qwen-enriched.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_review(report)
    for row in rows:
        levels = sorted({s["level"] for s in row["severity_sources"]})
        print(f"{row['package']} {row['id']} {','.join(levels) or 'UNKNOWN'}: {row['summary']}")
    for name, info in packages.items():
        active = [r for r in info.get("requires_dist") or [] if "extra ==" not in r]
        print(f"PyPI {name} {info['latest']} Python {info['requires_python']}; {active}")
    print(f"Saved {len(rows)} entries to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
