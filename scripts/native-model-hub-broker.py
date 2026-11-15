"""Explicit debug-only native acceptance broker. Real API/store; no vault or network.

Only the fixed debug native launcher calls this script. It never reads .env,
loads credentials, starts Hermes, migrates a user database, or touches audio.
The synthetic concrete route remains unavailable and cannot dispatch.
"""
import argparse
import asyncio
import json
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

    def no_network(request):
        raise RuntimeError('Native acceptance forbids provider and public-network requests.')
    def no_hermes():
        raise RuntimeError('Native acceptance forbids model runtime startup.')
    # Explicit values override any inherited environment; no credential/vault call.
    settings=Settings(_env_file=None,data_dir=folder,hermes_source=folder/'absent-hermes',
        openrouter_api_key=SecretStr(''),groq_api_key=SecretStr(''),gemini_api_key=SecretStr(''),nvidia_api_key=SecretStr(''),
        infernal_voice_enabled=False,reference_voice_enabled=False,delegation_enabled=False,
        artifact_tools_enabled=False,standard_mcp_enabled=False,local_tools_enabled=False,
        web_research_enabled=False,workspace_tools_enabled=False,durable_workflows_enabled=False)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    url=f'http://127.0.0.1:{listener.getsockname()[1]}'
    token=secrets.token_urlsafe(32)
    transport=httpx.AsyncClient(transport=httpx.MockTransport(no_network),trust_env=False)
    app=create_app(settings,token,url,client=transport,factory=no_hermes)
    @app.middleware('http')
    async def acceptance_scope(request, call_next):
        if request.method not in {'GET','OPTIONS'} and request.url.path not in {
            '/v1/sessions','/v1/tasks','/v1/settings/model-mode','/v1/stop'
        } and not (request.url.path.startswith('/v1/tasks/') and request.url.path.endswith('/cancel')):
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
        try:
            await server.serve(sockets=[listener])
        finally:
            await transport.aclose()
    asyncio.run(serve())


if __name__=='__main__':
    main()
