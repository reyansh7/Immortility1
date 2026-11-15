import json
from pathlib import Path

import pytest

from immortility_broker import evidence


def test_evidence_never_overwrites_prior_checkpoints_and_rejects_unscoped_paths(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    target = tmp_path / ".cache/verification/result.json"
    evidence.write_engineering_evidence({"status": "first"}, "fixture", target)
    with pytest.raises(FileExistsError):
        evidence.write_engineering_evidence({"status": "overwrite"}, "fixture", target)
    assert json.loads(target.read_text()) == {"status": "first"}
    with pytest.raises(ValueError):
        evidence.engineering_output_path(
            "fixture", Path(tmp_path.anchor) / "not-evidence-policy/result.json"
        )
    with pytest.raises(ValueError):
        evidence.engineering_output_path("fixture", tmp_path / ".cache/result.txt")
    assert evidence.engineering_output_path("fixture") != evidence.engineering_output_path(
        "fixture"
    )
