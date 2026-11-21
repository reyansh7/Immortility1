"""M2/P1 strict tool schemas: every exposed capability against malformed and malicious calls.

No model is involved: these are the exact provider/Hermes call envelopes the broker validates
before anything can execute. A rejected call must raise ``tool_denied`` (403) with a
diagnostic that names the reason, and must never echo the rejected values.
"""

import json
import threading

import pytest

from immortility_broker import project_inspection as projects
from immortility_broker.agent_bridge import (
    APPROVED_CAPABILITIES,
    PROVIDER_TOOL_NAME,
    TOOL_NAME,
    capability_input,
    tool_spec,
    validate_calls,
)
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError

ALL = sorted(APPROVED_CAPABILITIES)
REPORT = {
    "title": "Weekly Report",
    "summary": "S" * 90,
    "sections": [
        {"heading": "One", "paragraphs": ["A" * 50], "citations": ["mcp-security"]},
        {"heading": "Two", "paragraphs": ["B" * 50], "citations": ["owasp-mcp"]},
    ],
}
VALID: dict[str, dict] = {
    "arithmetic.add.v1": {"a": 2, "b": 3},
    "arithmetic.multiply.v1": {"a": 6, "b": 7},
    "clock.now.v1": {},
    "public.research.v1": {"query": "mcp authorization", "source_ids": ["mcp-security"]},
    "report.create.v1": REPORT,
    "project.outline.v1": {},
    "project.search.v1": {"query": "def main"},
    "project.read.v1": {"path": "src/app.py", "start_line": 1, "lines": 20},
}


def call(capability, arguments, *, ident="call_1", name=TOOL_NAME, raw=None):
    body = (
        raw if raw is not None else json.dumps({"capability": capability, "arguments": arguments})
    )
    return {"id": ident, "type": "function", "function": {"name": name, "arguments": body}}


def denied(calls, names=ALL) -> str:
    with pytest.raises(BrokerError) as caught:
        validate_calls(calls, names)
    assert caught.value.code == "tool_denied" and caught.value.status == 403
    return caught.value.diagnostic or ""


def test_every_exposed_capability_has_a_strict_schema_and_a_valid_example():
    assert set(VALID) == APPROVED_CAPABILITIES
    for name in ALL:
        model = capability_input(name)
        assert model.model_config.get("extra") == "forbid" and model.model_config.get("strict")
        schema = model.model_json_schema()
        assert schema.get("additionalProperties") is False
        clean = validate_calls([call(name, VALID[name])], ALL)
        assert json.loads(clean[0]["function"]["arguments"])["capability"] == name
    typed = tool_spec(ALL, typed=True)
    assert json.dumps(typed)  # the typed manifest itself is valid JSON


@pytest.mark.parametrize("name", ALL)
def test_unexpected_property_is_rejected(name):
    reason = denied([call(name, {**VALID[name], "shell": "rm -rf /"})])
    assert reason.startswith("capability_arguments:" + name)
    assert "rm -rf" not in reason


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("arithmetic.add.v1", {"a": 1}),
        ("arithmetic.add.v1", {"a": "1", "b": 2}),
        ("arithmetic.add.v1", {"a": True, "b": 2}),
        ("arithmetic.add.v1", {"a": 1.5, "b": 2}),
        ("arithmetic.add.v1", {"a": 10**12, "b": 2}),
        ("arithmetic.multiply.v1", {"a": None, "b": 2}),
        ("clock.now.v1", {"timezone": "UTC"}),
        ("public.research.v1", {"query": "x"}),
        ("public.research.v1", {"query": "q" * 201}),
        ("public.research.v1", {"query": "ok query", "source_ids": ["https://evil.example"]}),
        ("public.research.v1", {"query": "ok query", "source_ids": ["mcp-security"] * 4}),
        ("report.create.v1", {**REPORT, "title": "../../etc/passwd"}),
        ("report.create.v1", {**REPORT, "title": "<script>x</script>"}),
        ("report.create.v1", {**REPORT, "sections": REPORT["sections"][:1]}),
        ("report.create.v1", {**REPORT, "summary": "short"}),
        ("project.search.v1", {"query": ""}),
        ("project.search.v1", {"query": "q", "scope_id": "x" * 64}),
        ("project.read.v1", {"path": ""}),
        ("project.read.v1", {"path": "a" * 241}),
        ("project.read.v1", {"path": "src/app.py", "lines": 1000}),
        ("project.read.v1", {"path": "src/app.py", "start_line": 0}),
        ("project.read.v1", {"path": 7}),
    ],
)
def test_missing_wrong_type_out_of_range_and_injected_fields(name, arguments):
    assert denied([call(name, arguments)]).startswith("capability_arguments:" + name)


@pytest.mark.parametrize(
    "calls,reason",
    [
        ([], ""),  # batch size is rejected before any per-call diagnostic
        ([call("clock.now.v1", {}, ident=f"c{i}") for i in range(5)], ""),
        ([{"type": "function"}], "call_identity"),
        ([call("clock.now.v1", {}, ident="bad id\n")], "call_identity"),
        ([call("clock.now.v1", {}), call("clock.now.v1", {})], "call_identity"),
        ([call("clock.now.v1", {}, name="shell.exec")], "tool_name"),
        ([call("clock.now.v1", {}, raw="x" * 16001)], "argument_encoding"),
        ([call("clock.now.v1", {}, raw="{not json")], "proposal_schema"),
        (
            [call("", {}, raw='{"capability":"clock.now.v1","capability":"x","arguments":{}}')],
            "proposal_schema",
        ),
        (
            [call("", {}, raw='{"capability":"arithmetic.add.v1","arguments":{"a":NaN,"b":1}}')],
            "proposal_schema",
        ),
        (
            [call("", {}, raw='{"capability":"arithmetic.add.v1","arguments":{"a":1e400,"b":1}}')],
            "proposal_schema",
        ),
        (
            [call("", {}, raw='{"capability":"clock.now.v1","arguments":{},"approve":true}')],
            "proposal_schema",
        ),
        ([call("", {}, raw='["clock.now.v1"]')], "proposal_schema"),
        ([call("", {}, raw="[" * 5000 + "]" * 5000)], "proposal_schema"),
        ([call("filesystem.delete.v1", {"path": "C:/"})], "capability_scope"),
    ],
)
def test_envelope_attacks(calls, reason):
    assert denied(calls).startswith(reason)


def test_arguments_must_be_a_json_string_not_an_object():
    bad = {"id": "c", "type": "function", "function": {"name": PROVIDER_TOOL_NAME, "arguments": {}}}
    assert denied([bad]) == "argument_encoding"


def test_capability_outside_this_task_grant_is_rejected_even_if_globally_approved():
    assert (
        denied([call("project.read.v1", VALID["project.read.v1"])], ["clock.now.v1"])
        == "capability_scope"
    )


def test_one_bad_call_rejects_the_whole_batch():
    batch = [
        call("clock.now.v1", {}, ident="ok"),
        call("arithmetic.add.v1", {"a": "x", "b": 1}, ident="bad"),
    ]
    assert denied(batch).startswith("capability_arguments:arithmetic.add.v1")


@pytest.mark.parametrize(
    "path",
    [
        "..\\..\\Windows\\System32\\config\\SAM",
        "\\\\server\\share\\file.py",
        "//server/share/file.py",
        "src/app.py\x00.txt",
        "CON",
        "nul.txt",
        "%2e%2e/%2e%2e/secret.py",
        "src/../../../outside.py",
        "C:file.py",
        "src/app.py::$DATA",
    ],
)
def test_read_execution_refuses_malicious_paths(tmp_path, path):
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('ok')\n")
    (tmp_path / "outside.py").write_text("SECRET")
    config = Settings(_env_file=None, data_dir=tmp_path / "data", openrouter_api_key="")
    config.workspace_root = root
    config.project_read_enabled = True
    with pytest.raises(BrokerError) as caught:
        projects.read(
            config,
            projects.ReadInput(scope_id=projects.identity(root), path=path),
            threading.Event(),
        )
    assert "SECRET" not in caught.value.message


def test_cancelled_read_never_touches_the_file(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = Settings(_env_file=None, data_dir=tmp_path / "data", openrouter_api_key="")
    config.workspace_root = root
    config.project_read_enabled = True
    stopped = threading.Event()
    stopped.set()
    with pytest.raises(BrokerError) as caught:
        projects.read(
            config, projects.ReadInput(scope_id=projects.identity(root), path="x.py"), stopped
        )
    assert caught.value.code == "tool_cancelled"
