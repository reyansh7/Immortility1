"""Create the research residual register from actual scans and existing advisory evidence."""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main():
    original = read("infra/security/qwen-advisories-reviewed.json")
    scan = read("data/audits/qwen-headless-final-pypi.json")
    packages = {p["name"]: p for p in scan["dependencies"]}
    comparisons = []
    for item in original["findings"]:
        name = item["package"]
        selected = packages.get(name)
        resolution = (
            "Component removed from the actual installed candidate, not an advisory suppression."
            if selected is None
            else "Updated beyond reported affected ranges; published package scans contain no findings."
        )
        if name == "accelerate":
            resolution += " Device-map/offload arguments are rejected. Source/controlled-reader evidence shows 1.15.0 still unsafe; it was rejected."
        comparisons.append(
            {
                "id": item["id"],
                "aliases": item["aliases"],
                "severity": item["severity"],
                "package": name,
                "original_version": item["installed_version"],
                "candidate_version": selected.get("version") if selected else None,
                "result": "component_removed" if selected is None else "updated_no_indexed_finding",
                "resolution": resolution,
                "original_reference": item["url"],
            }
        )
    assert len(comparisons) == 52 and len({p["id"] for p in comparisons}) == 52
    assert not any(p.get("vulns") for p in scan["dependencies"])
    residuals = [
        {
            "id": "R1",
            "status": "OPEN",
            "risk": "Local derivative is not indexed on PyPI; its source and behavior cannot be certified by a clean package scan.",
            "gate": "Pinned source archive, Apache provenance, review diff and CPU contracts exist; independent review and full load/generation parity are still required.",
        },
        {
            "id": "R2",
            "status": "OPEN",
            "risk": "No CPU pretrained-weight load, CUDA model load, speech generation or cancellation under real inference was authorized.",
            "gate": "Separate explicit native checkpoint approval; no automatic promotion or experimental flag change.",
        },
        {
            "id": "R3",
            "status": "OPEN",
            "risk": "Python path/hash/option checks are not an OS filesystem/network sandbox. Mutable model/profile files still present a check-to-use race.",
            "gate": "Broker must supply approved canonical roots and trusted profile/metadata hashes; read-only artifact staging, restricted token/ACLs and independently enforced egress limits require a separate Windows security design/test.",
        },
        {
            "id": "R4",
            "status": "OPEN",
            "risk": "The candidate rejects device_map and omits Accelerate. A future CPU-load then explicit .to(cuda:0) path has not been validated on the real model.",
            "gate": "Documented CPU/GPU memory, dtype, RoPE, ICL and speaker-parity checks before adoption; never silently select the candidate from the existing worker.",
        },
        {
            "id": "R5",
            "status": "OPEN",
            "risk": "Existing Windows taskkill cleanup exceeded its bound during competing imports; isolated lifecycle rerun passed.",
            "gate": "Record serial regression outcome and reproduce cancellation under realistic load before native acceptance; no timeout relaxation or suppressed failure.",
        },
        {
            "id": "R6",
            "status": "REJECTED_OPTION",
            "risk": "Accelerate 1.15.0 has unchecked checkpoint index path joins despite the advisory's last-affected range ending at 1.14.0.",
            "gate": "Synthetic reader-mocked path escape reproduced without weight reads. Component is absent from selected candidate; this is not a claim the upstream flaw is patched.",
        },
        {
            "id": "R7",
            "status": "OPEN",
            "risk": "GPU wheel/driver/native-library behavior is untested. CPU PyTorch 2.15.0 is not evidence of CUDA compatibility.",
            "gate": "Official cu132 Windows cp313 wheel identified; check Windows driver requirements and scope a separate GPU test environment after approval.",
        },
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate": "immortility-qwen-tts-headless==0.1.1.post1+immortility.2",
        "recommendation": "BLOCKED for activation; CPU research gates passed",
        "original_environment_changed": False,
        "experimental_qwen_tts": False,
        "original_entries": comparisons,
        "supplemental_torch": {
            "id": "GHSA-rrmf-rvhw-rf47",
            "severity": "LOW",
            "original_upstream_version": "2.11.0",
            "candidate_version": "2.15.0",
            "reported_fixed": "2.13.0",
            "result": "updated_no_indexed_finding; CUDA binary not tested",
        },
        "scan_packages": len(packages),
        "indexed_package_findings": 0,
        "scan_skips": [
            {"package": p["name"], "reason": p["skip_reason"]}
            for p in packages.values()
            if p.get("skip_reason")
        ],
        "residuals": residuals,
        "cpu_contracts": read("data/audits/qwen-headless-contracts.json"),
        "accelerate_source_contract": read("data/audits/qwen-accelerate-path-contract.json"),
    }
    (ROOT / "infra/security/qwen-headless-residuals.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Recorded all 52 original entries, supplemental Torch finding and seven explicit residual gates."
    )


if __name__ == "__main__":
    main()
