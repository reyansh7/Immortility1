"""Offline evaluation boundaries; native synthesis is a separate explicitly invoked benchmark."""

import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from immortility_broker.reference_contracts import ReferenceRequest, sha256, verified_file


def request(**updates):
    return {
        "evaluation_authorized": True,
        "run_id": "test",
        "case": "normal",
        "model_manifest_sha256": "a" * 64,
        "reference_manifest_sha256": "b" * 64,
        **updates,
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"evaluation_authorized": False},
        {"evaluation_authorized": 1},
        {"run_id": "../escape"},
        {"reference": "arbitrary.wav"},
        {"model_manifest_sha256": "unverified"},
        {"output": "C:/private"},
    ],
)
def test_rejects_unauthorized_or_unbounded_evaluation_arguments(updates):
    with pytest.raises(ValidationError):
        ReferenceRequest.model_validate(request(**updates))


def test_asset_tampering_and_path_traversal_are_rejected(tmp_path):
    path = tmp_path / "model.bin"
    path.write_bytes(b"verified public fixture")
    digest = sha256(path)
    assert verified_file(tmp_path, path.name, path.stat().st_size, digest) == path
    with pytest.raises(ValueError):
        verified_file(tmp_path, "../model.bin", path.stat().st_size, digest)
    path.write_bytes(b"unauthorized substitute!")
    with pytest.raises(ValueError):
        verified_file(tmp_path, path.name, path.stat().st_size, digest)


def test_reference_worker_defaults_off_without_importing_a_model(monkeypatch, capsys):
    from immortility_broker import reference_worker

    monkeypatch.delenv("IMMORTILITY_REFERENCE_EVALUATION", raising=False)
    monkeypatch.setattr(reference_worker, "PROTOCOL", __import__("sys").stdout)
    with patch.object(reference_worker, "Engine", side_effect=AssertionError("model load")):
        reference_worker.main()
    assert json.loads(capsys.readouterr().out) == {
        "kind": "error",
        "code": "reference_evaluation_disabled",
    }
