"""Own an isolated native Model Hub UI; scratch control.txt snapshot/restart/quit only."""
import asyncio
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from uuid import uuid4
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/broker/src'))
from immortility_broker.process_owner import reap,spawn_owned


async def main(data_dir=None,stream_seconds=None,stall=False,project_inspector=False):
    scope=(ROOT/'.cache/model-hub-native').resolve()
    root=(data_dir if data_dir is not None else scope/str(uuid4())).resolve()
    if root==scope or not root.is_relative_to(scope):
        raise ValueError('Native fixture data must stay inside .cache/model-hub-native.')
    root.mkdir(parents=True,exist_ok=True)
    if project_inspector:
        if stream_seconds is not None:
            raise ValueError('Project and synthetic stream scenarios must run separately.')
        from native_project_fixture import prepare
        prepare(root)
    if stream_seconds is not None:
        (root/'native-stream.json').write_text(json.dumps({'seconds':stream_seconds,**({'stall_seconds':95} if stall else {})}),encoding='utf-8')
    local=root/'Local';local.mkdir(exist_ok=True)
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','COMSPEC','PATH','PATHEXT','TEMP','TMP'}}
    env.update(USERPROFILE=str(root),LOCALAPPDATA=str(local),APPDATA=str(root/'Roaming'),
        WEBVIEW2_USER_DATA_FOLDER=str(root/'webview'),PYTHONUTF8='1',PYTHONUNBUFFERED='1')
    children=[]
    native=None
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    async def launch():
        return await spawn_owned(str(ROOT/'apps/desktop/src-tauri/target/debug/immortility-desktop.exe'),
            '--model-hub-test-root',str(root),cwd=ROOT,env=env,
            stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,creationflags=flags)
    try:
        vite=await spawn_owned(shutil.which('node') or 'node',str(ROOT/'apps/desktop/node_modules/vite/bin/vite.js'),
            'preview','--host','127.0.0.1','--port','1420','--strictPort',cwd=ROOT/'apps/desktop',env=env,
            stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,creationflags=flags)
        children.append(vite)
        async with asyncio.timeout(15),httpx.AsyncClient(trust_env=False,timeout=1) as client:
            while True:
                if vite[0].returncode is not None:
                    raise RuntimeError('Preview unavailable; no existing process or port was changed.')
                try:
                    response=await client.get('http://127.0.0.1:1420')
                    if response.status_code==200 and response.text==(ROOT/'apps/desktop/dist/index.html').read_text(encoding='utf-8'):
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(.1)
        native=await launch()
        print(json.dumps({'status':'native-fixture-started','data_root':str(root),'credentials_loaded':False,'cloud_requests_permitted':False}),flush=True)
        async with asyncio.timeout(1800):
            while True:
                control=root/'control.txt'
                if not control.exists():
                    await asyncio.sleep(.25)
                    continue
                command=control.read_text(encoding='utf-8').strip()
                control.unlink()
                if command=='quit':
                    break
                if command=='restart':
                    await reap(*native);native=await launch();print('{"status":"native-restarted"}',flush=True)
                elif command in {'task_busy','voice_busy','idle','delay_model','no_delay','fail_model_once','disconnect','slow_project','fast_project'}:
                    (root/'scenario.txt').write_text(command,encoding='utf-8')
                elif command=='snapshot':
                    path=root/'state.sqlite3'
                    if path.exists():
                        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                            row=db.execute('SELECT body FROM model_preferences WHERE id=1').fetchone()
                            print(json.dumps({'selection':json.loads(row[0]) if row else {'mode':'auto_cloud','route_id':None},'task_count':db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]}),flush=True)
                    else:
                        print('{"status":"broker-not-started"}',flush=True)
    finally:
        if native:
            await reap(*native)
        for child in reversed(children):
            await reap(*child)
        print('{"status":"owned-native-processes-reaped"}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--stream-seconds',type=int,choices=[180,285])
    parser.add_argument('--stall',action='store_true')
    parser.add_argument('--project-inspector',action='store_true')
    options=parser.parse_args()
    if options.stall and options.stream_seconds!=180:
        parser.error('--stall requires --stream-seconds 180')
    asyncio.run(main(options.data_dir,options.stream_seconds,options.stall,options.project_inspector))
