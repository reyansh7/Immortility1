"""Explicit debug-only native acceptance broker. Real API/store; no vault or network.

Only the fixed debug native launcher calls this script. It never reads .env,
loads credentials, starts Hermes, migrates a user database, or touches audio.
The synthetic concrete route remains unavailable and cannot dispatch.
"""
import argparse
import asyncio
import json
import os
import hmac
import time
import re
from pathlib import Path
import secrets
import socket
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"services/broker/src"))
import httpx
from pydantic import SecretStr
import uvicorn
from fastapi.responses import JSONResponse
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.providers import ModelOffer
from immortility_broker.contracts import TaskRequest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,required=True)
    args=parser.parse_args()
    # Rust canonicalize uses the Win32 extended local-drive spelling. Normalize
    # that spelling before pathlib containment; UNC/device paths remain denied.
    spelling=str(args.data_dir)
    if re.match(r"^\\\\\?\\[A-Za-z]:\\", spelling):
        spelling=spelling[4:]
    folder=Path(spelling).resolve(strict=True)
    cache=(ROOT/'.cache').resolve(strict=True)
    if folder==cache or not folder.is_relative_to(cache):
        raise SystemExit('Acceptance root must be inside workspace .cache.')
    restart_marker=folder/'restart-delay.once'
    if restart_marker.exists():
        restart_marker.unlink()
        time.sleep(3)

    def no_network(request):
        raise RuntimeError('Native acceptance forbids provider and public-network requests.')
    def no_hermes():
        raise RuntimeError('Native acceptance forbids model runtime startup.')
    # Explicit values override any inherited environment; no credential/vault call.
    settings=Settings(_env_file=None,data_dir=folder,hermes_source=folder/'absent-hermes',
        openrouter_api_key=SecretStr(''),groq_api_key=SecretStr(''),gemini_api_key=SecretStr(''),nvidia_api_key=SecretStr(''),
        infernal_voice_enabled=False,reference_voice_enabled=False,delegation_enabled=False,
        artifact_tools_enabled=True,standard_mcp_enabled=False,local_tools_enabled=False,
        web_research_enabled=True,workspace_tools_enabled=False,durable_workflows_enabled=False)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    url=f'http://127.0.0.1:{listener.getsockname()[1]}'
    token=secrets.token_urlsafe(32)
    transport=httpx.AsyncClient(transport=httpx.MockTransport(no_network),trust_env=False)
    app=create_app(settings,token,url,client=transport,factory=no_hermes)
    from native_project_fixture import install, allowed
    project_fixture=install(app,folder)
    stream_producer=None
    stream_config=folder/'native-stream.json'
    if stream_config.exists():
        if stream_config.stat().st_size>256:
            raise SystemExit('Invalid native stream fixture configuration.')
        config=json.loads(stream_config.read_text(encoding='utf-8'))
        if config not in [{'seconds':180},{'seconds':285},{'seconds':180,'stall_seconds':95}]:
            raise SystemExit('Only reviewed native stream durations are permitted.')
        from native_event_fixture import install_stream_fixture
        stream_producer=install_stream_fixture(app,folder,config['seconds'],drop_after=0 if config.get('stall_seconds') else 45,stall_seconds=config.get('stall_seconds',0))
    counts={'model_mode_requests':0}
    model_delay=0
    fail_model_once=False
    @app.middleware('http')
    async def acceptance_scope(request, call_next):
        nonlocal fail_model_once
        authenticated=hmac.compare_digest(request.headers.get('authorization',''),'Bearer '+token)
        project_request=False
        if project_fixture['enabled'] and authenticated and request.method=='POST' and request.url.path in {'/v1/settings/project','/v1/workflows'}:
            try:
                body=await request.json()
                project_request=isinstance(body,dict) and allowed(request.url.path,body,folder)
            except (ValueError,TypeError):
                pass
            if not project_request:
                return JSONResponse({'error':{'code':'acceptance_scope','message':'Only the two synthetic projects and project-read steps are allowed.'}},status_code=403)
        if authenticated and request.method=='POST' and (request.url.path=='/v1/stop' or request.url.path.endswith('/cancel')):
            category='global_stop' if request.url.path=='/v1/stop' else 'task_cancel'
            with (folder/'native-actions.jsonl').open('a',encoding='utf-8') as output:
                source=request.headers.get('x-immortility-action-source','')
                if source not in {'native-ipc-stop','native-ipc-cancel','native-context-stop','native-hotkey-stop','native-tray-stop'}:
                    source='authenticated-local-request'
                output.write(json.dumps({'category':category,'monotonic':time.monotonic(),'route':'/v1/stop' if category=='global_stop' else '/v1/tasks/{task_id}/cancel','task_id':app.state.engine.active,'reason':'explicit_stop_request','source_tag':source})+'\n')
        if authenticated and request.method=='POST' and request.url.path=='/v1/settings/model-mode':
            counts['model_mode_requests']+=1
            (folder/'native-counts.json').write_text(json.dumps(counts),encoding='utf-8')
            if model_delay:
                await asyncio.sleep(model_delay)
            if fail_model_once:
                fail_model_once=False
                return JSONResponse({'error':{'code':'synthetic_failure','message':'Synthetic model selection failure; no preference changed.'}},status_code=503)
        if request.method not in {'GET','OPTIONS'} and request.url.path not in {
            '/v1/sessions','/v1/settings/model-mode','/v1/stop'
        } and not project_request and not (request.url.path.startswith('/v1/tasks/') and request.url.path.endswith('/cancel')):
            return JSONResponse({'error':{'code':'acceptance_scope','message':'This scratch fixture allows model-mode acceptance only.'}},status_code=403)
        return await call_next(request)
    route=ModelOffer(route_id='openrouter/native-acceptance-fixture',provider='openrouter',
        model_id='native-acceptance-fixture',context_tokens=4096,qualification='offline',available=False)
    app.state.engine.registry.models[route.route_id]=route
    server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False))
    def parent_watch():
        sys.stdin.buffer.read()
        server.should_exit=True
    threading.Thread(target=parent_watch,daemon=True).start()
    # The ordinary private native stdout handshake; never printed by the harness.
    print(json.dumps({'url':url,'token':token}),flush=True)
    async def serve():
        producer=asyncio.create_task(stream_producer()) if stream_producer else None
        if producer:
            app.state.engine.worker=producer
        async def scenarios():
            nonlocal model_delay,fail_model_once
            active_fixture=None
            while True:
                path=folder/'scenario.txt'
                if path.exists():
                    scenario=path.read_text(encoding='utf-8').strip()
                    path.unlink()
                    if scenario=='delay_model':
                        model_delay=6
                    elif scenario=='disconnect':
                        # Explicit scratch-only crash injection. No live broker,
                        # unrelated process, provider or user database is involved.
                        (folder/'restart-delay.once').write_text('scratch crash recovery',encoding='utf-8')
                        with (folder/'native-actions.jsonl').open('a',encoding='utf-8') as output:
                            output.write(json.dumps({'category':'fixture_broker_crash','reason':'explicit_scratch_fault','monotonic':time.monotonic()})+'\n')
                        os._exit(17)
                    elif scenario=='no_delay':
                        model_delay=0
                    elif scenario=='fail_model_once':
                        fail_model_once=True
                    elif scenario in {'slow_project','fast_project'}:
                        project_fixture['slow']=scenario=='slow_project'
                    if scenario in {'task_busy','voice_busy','idle'}:
                        if active_fixture is not None:
                            app.state.store.state(active_fixture,'cancelled')
                            app.state.engine.active=None
                            active_fixture=None
                        app.state.voice.state='TRANSCRIBING' if scenario=='voice_busy' else 'IDLE'
                        if scenario=='task_busy':
                            store=app.state.store
                            sid=store.session()['id']
                            task,_=store.create(TaskRequest(session_id=sid,request_id=secrets.token_hex(8),content='Synthetic native busy-state fixture',cloud_consent=True))
                            active_fixture=task['task_id']
                            store.state(active_fixture,'queued');store.state(active_fixture,'running')
                            app.state.engine.active=active_fixture
                await asyncio.sleep(.1)
        monitor=asyncio.create_task(scenarios())
        try:
            await server.serve(sockets=[listener])
        finally:
            if producer:
                producer.cancel()
                try:
                    await producer
                except asyncio.CancelledError:
                    pass
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass
            await transport.aclose()
    asyncio.run(serve())


if __name__=='__main__':
    main()
