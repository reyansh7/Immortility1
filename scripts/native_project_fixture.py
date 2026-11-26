"""Extra restrictions for keyless native Project Inspector acceptance only."""

import asyncio
import json
from pathlib import Path


def prepare(folder: Path) -> None:
    for name, value in [("project-one", 42), ("project-two", 99)]:
        project = folder / name
        project.mkdir()
        (project / "example.ts").write_text(
            f"export const answer = {value};\n// Synthetic acceptance project only.\n",
            encoding="utf-8",
        )
        (project / ".env").write_text("SYNTHETIC_SECRET_CANARY=withheld\n", encoding="utf-8")
    (folder / "project-inspector.json").write_text('{"synthetic":true}', encoding="utf-8")


def install(app, folder: Path) -> dict:
    marker = folder / "project-inspector.json"
    if not marker.exists():
        return {"enabled": False}
    if marker.stat().st_size > 64 or json.loads(marker.read_text()) != {"synthetic": True}:
        raise ValueError("Invalid project fixture marker")
    state = {"enabled": True, "slow": False}
    execute = app.state.engine._execute_workflow

    async def delayed(task_id):
        # Queue delay only: retain the production tool/permission deadlines.
        if state["slow"]:
            await asyncio.sleep(10)
        await execute(task_id)

    app.state.engine._execute_workflow = delayed
    return state


def allowed(path: str, body: dict, folder: Path) -> bool:
    if path == "/v1/settings/project":
        return body.get("enabled") is False or body.get("root") in {
            str(folder / "project-one"),
            str(folder / "project-two"),
        }
    if path == "/v1/workflows":
        steps = body.get("steps")
        return (
            isinstance(steps, list)
            and 1 <= len(steps) <= 16
            and all(
                isinstance(step, dict)
                and step.get("capability")
                in {"project.search.v1", "project.read.v1", "project.outline.v1"}
                for step in steps
            )
        )
    return False
