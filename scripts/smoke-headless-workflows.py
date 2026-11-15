"""Real local broker/SDK/SQLite recovery. No GUI, model, account or service install."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"services/broker/src"))
from immortility_broker.process_owner import reap,spawn_owned


async def launch(folder):
    env={k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT","WINDIR","PATH","TEMP","TMP"}}
    env.update(PYTHONPATH=str(ROOT/"services/broker/src"),PYTHONUTF8="1",PYTHONUNBUFFERED="1",USERPROFILE=str(folder),APPDATA=str(folder),LOCALAPPDATA=str(folder))
    process,owner=await spawn_owned(sys.executable,"-m","immortility_broker","--headless","--local-workflows","--standard-mcp","--data-dir",str(folder),cwd=ROOT,env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    client=None
    try:
        handshake=json.loads(await asyncio.wait_for(process.stdout.readline(),15))
        client=httpx.AsyncClient(base_url=handshake["url"],headers={"Authorization":"Bearer "+handshake["token"]},trust_env=False,timeout=5)
        deadline=time.monotonic()+5
        while True:
            try:
                response=await client.get("/health/ready")
                response.raise_for_status()
                break
            except httpx.HTTPError:
                if time.monotonic()>=deadline:raise
                await asyncio.sleep(0.02)
        process.stdin.close()
        await asyncio.sleep(0.1)
        assert process.returncode is None
        return process,owner,client
    except BaseException:
        if client is not None:await client.aclose()
        await reap(process,owner)
        raise


async def main():
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="headless-workflow-",dir=ROOT/".cache") as folder:
        process,owner,client=await launch(folder)
        try:
            sid=(await client.post("/v1/sessions")).json()["id"]
            request={"session_id":sid,"request_id":"headless-recovery","label":"Scratch observed-time and integer calculation","local_read_consent":True,"no_cloud":True,"resume_on_restart":True,"max_retries":1,"deadline_seconds":60,"steps":[{"id":"before","capability":"clock.now.v1"},{"id":"sum","capability":"arithmetic.add.v1","arguments":{"a":7,"b":8},"depends_on":["before"]},{"id":"after","capability":"clock.now.v1","depends_on":["sum"]}]}
            submitted=await client.post("/v1/workflows",json=request)
            submitted.raise_for_status()
            task_id=submitted.json()["task_id"]
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                view=(await client.get(f"/v1/workflows/{task_id}")).json()
                steps={step["step_id"]:step for step in view["steps"]}
                if steps["before"]["status"]=="completed" and steps["sum"]["status"]=="running":break
                await asyncio.sleep(0.01)
            else:raise AssertionError("Did not observe the intended persisted checkpoint")
            expires=view["expires_at"]
        finally:
            await client.aclose()
            await reap(process,owner)
        process,owner,client=await launch(folder)
        try:
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                task=(await client.get(f"/v1/tasks/{task_id}")).json()
                if task["status"] in {"succeeded","failed","blocked","disconnected"}:break
                await asyncio.sleep(0.02)
            assert task["status"]=="succeeded",task.get("error")
            assert task["result"]["steps"]["sum"]=={"result":15}
            final=(await client.get(f"/v1/workflows/{task_id}")).json()
            attempts={step["step_id"]:step["attempts"] for step in final["steps"]}
            assert attempts=={"before":1,"sum":2,"after":1}
            assert final["expires_at"]==expires
            usage=(await client.get(f"/v1/tasks/{task_id}/usage")).json()
            assert usage["summary"]["calls"]==0
            assert (await client.post("/inference/v1/chat/completions",json={})).status_code==403
            result={"mode":"real local Uvicorn broker / SDK 2.2.0 / SQLite / native Windows process ownership","status":"passed","stdin_eof_survived":True,"scratch_crash_recovered":True,"completed_step_replayed":False,"step_attempts":attempts,"original_expiry_preserved":True,"model_calls":0,"cloud_tokens":0,"total_seconds":round(time.perf_counter()-started,3),"dashboard_attach_verified":False,"windows_service_installed":False}
            (ROOT/"docs/implementation/HEADLESS_WORKFLOW_SMOKE.json").write_text(json.dumps(result,indent=2)+"\n")
            print(json.dumps(result))
        finally:
            await client.aclose()
            await reap(process,owner)


if __name__=="__main__":
    asyncio.run(main())
