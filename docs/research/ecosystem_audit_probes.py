"""Synthetic audit probes; fixture writes occur only in a temporary directory.

Default reports existing behavior. --expect-fixed is a future acceptance check.
No .env, user history, microphone, provider, model or external account is used.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/broker/src"))

from immortility_broker.contracts import BrokerError, TaskRequest  # noqa: E402
from immortility_broker.memory import prior_task_notes  # noqa: E402
from immortility_broker.store import Store  # noqa: E402
from immortility_broker.workspace import (  # noqa: E402
    apply_proposed,
    fingerprint,
    read_source,
)


def probe() -> dict[str, object]:
    result: dict[str, object] = {"scope": "synthetic temporary fixtures only"}
    with tempfile.TemporaryDirectory(prefix="immortility-ecosystem-audit-") as directory:
        root = Path(directory)
        (root / "credentials.json").write_text('{"dummy":"audit-fixture"}', encoding="utf-8")
        for name in ("credentials.json", "CREDENTIALS.JSON"):
            try:
                read_source(root, name)
                result[name] = "read allowed"
            except BrokerError as error:
                result[name] = error.code

        path = root / "fixture.py"
        original = b"x = 1\r\n"
        path.write_bytes(original)
        try:
            apply_proposed(
                root, "fixture.py", "x = 2\n", fingerprint(read_source(root, "fixture.py"))
            )
            result["crlf_apply"] = "applied"
        except BrokerError as error:
            result["crlf_apply"] = error.code
        result["crlf_original_preserved_on_rejection"] = path.read_bytes() == original

        store = Store(root / "state.sqlite3")
        try:
            session = store.session()["id"]
            task, _ = store.create(
                TaskRequest(
                    session_id=session,
                    request_id="audit-memory",
                    content="Audit fixture project remembers citrus",
                    cloud_consent=True,
                )
            )
            task_id = task["task_id"]
            for state in ("queued", "running", "verifying"):
                store.state(task_id, state)
            store.state(
                task_id,
                "succeeded",
                result={
                    "text": "citrus audit fixture",
                    "provider": "openrouter",
                    "model": "openrouter/free",
                    "paid_usd": 0,
                },
            )
            store.remember(session, task_id, "citrus audit fixture")
            result["fts_available"] = store.fts
            result["forgot_rows"] = store.forget(session, task_id)
            result["fts_matches_after_forget"] = len(store.recall(session, "citrus"))
            result["history_messages_after_forget"] = len(store.history(session))
            result["prior_task_note_survives_forget"] = bool(
                prior_task_notes(store.tasks(session), "citrus", "new-task")
            )
        finally:
            store.db.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-fixed", action="store_true")
    args = parser.parse_args()
    findings = probe()
    print(json.dumps(findings, indent=2))
    if args.expect_fixed:
        fixed = (
            findings["crlf_apply"] == "applied" and not findings["prior_task_note_survives_forget"]
        )
        if os.name == "nt":
            fixed = fixed and findings["CREDENTIALS.JSON"] == "tool_denied"
        raise SystemExit(0 if fixed else 1)
