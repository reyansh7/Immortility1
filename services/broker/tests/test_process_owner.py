import asyncio
import ctypes
import os
import subprocess
import sys

import pytest

from immortility_broker.process_owner import reap, spawn_owned


async def test_cancellation_during_os_spawn_still_reaps_child(monkeypatch):
    original = asyncio.create_subprocess_exec
    entered, release = asyncio.Event(), asyncio.Event()
    spawned = []

    async def delayed(*args, **kwargs):
        entered.set()
        await release.wait()
        process = await original(*args, **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
    operation = asyncio.create_task(
        spawn_owned(
            sys.executable,
            "-c",
            "import time;time.sleep(60)",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    )
    await entered.wait()
    operation.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await operation
    assert spawned and spawned[0].returncode is not None


@pytest.mark.skipif(os.name != "nt", reason="Native Windows job containment")
async def test_windows_job_reaps_a_real_descendant_started_after_attachment():
    program = "import sys,subprocess,time;sys.stdin.readline();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);print(p.pid,flush=True);time.sleep(60)"
    process, owner = await spawn_owned(
        sys.executable,
        "-u",
        "-c",
        program,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = None
    try:
        process.stdin.write(b"start\n")
        await process.stdin.drain()
        pid = int(await asyncio.wait_for(process.stdout.readline(), 3))
        handle = kernel.OpenProcess(0x1000, False, pid)
        assert handle
        assert owner.contains(pid)
        assert not owner.contains(os.getpid())
        await reap(process, owner)
        code = ctypes.c_uint32(259)
        for _ in range(100):
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            if code.value != 259:
                break
            await asyncio.sleep(0.01)
        assert code.value != 259 and process.returncode is not None
    finally:
        await reap(process, owner)
        if handle:
            kernel.CloseHandle(handle)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows whole-job memory limit")
async def test_job_commit_limit_prevents_large_worker_allocation():
    process, owner = await spawn_owned(
        sys.executable,
        "-I",
        "-u",
        "-c",
        "try:\n x=bytearray(128*1024**2)\n print('unexpected allocation')\n"
        "except MemoryError:\n print('allocation denied')",
        job_memory_limit=64 * 1024**2,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 5)
        assert output.strip() == b"allocation denied"
        # Windows' peak counter may include the rejected allocation request;
        # it is evidence, not a substitute for observing allocation refusal.
        assert owner.peak_committed_bytes() > 0
        assert process.returncode == 0
    finally:
        await reap(process, owner)


@pytest.mark.parametrize("limit", [True, 0, -1, 1024, 3 * 1024**3])
async def test_invalid_job_limit_rejected_before_launch(limit, monkeypatch):
    async def unexpected(*args, **kwargs):
        raise AssertionError("Invalid resource limit reached process creation")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unexpected)
    with pytest.raises(ValueError):
        await spawn_owned(sys.executable, job_memory_limit=limit)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows descendant file-handle cleanup")
async def test_reap_waits_for_all_descendants_to_release_owned_files(tmp_path):
    path = tmp_path / "owned-native-worker.log"
    child = "import sys,time;p=open(sys.argv[1],'w');print('ready',flush=True);time.sleep(60)"
    parent = "import subprocess,sys,time;p=subprocess.Popen([sys.executable,'-u','-c',sys.argv[1],sys.argv[2]],stdout=subprocess.PIPE);assert p.stdout.readline().strip()==b'ready';print('ready',flush=True);time.sleep(60)"
    process, owner = await spawn_owned(
        sys.executable,
        "-u",
        "-c",
        parent,
        child,
        str(path),
        stdout=asyncio.subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        assert await asyncio.wait_for(process.stdout.readline(), 3) == b"ready\r\n"
        assert owner.active_processes() >= 2
        await reap(process, owner)
        renamed = path.with_suffix(".released")
        path.rename(renamed)
        assert renamed.exists()
    finally:
        await reap(process, owner)
