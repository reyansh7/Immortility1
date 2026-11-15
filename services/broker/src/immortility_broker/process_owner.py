"""Owned Windows process trees. A job is a cleanup boundary, NOT an OS sandbox."""

import asyncio
import ctypes
import os
import subprocess
from ctypes import wintypes
from typing import Any


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("ProcessTime", ctypes.c_longlong),
        ("JobTime", ctypes.c_longlong),
        ("Flags", wintypes.DWORD),
        ("MinimumWorkingSet", ctypes.c_size_t),
        ("MaximumWorkingSet", ctypes.c_size_t),
        ("ActiveProcesses", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("Priority", wintypes.DWORD),
        ("Scheduling", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong)
        for name in (
            "ReadOperations",
            "WriteOperations",
            "OtherOperations",
            "ReadBytes",
            "WriteBytes",
            "OtherBytes",
        )
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("Basic", _BasicLimits),
        ("Io", _IoCounters),
        ("ProcessMemory", ctypes.c_size_t),
        ("JobMemory", ctypes.c_size_t),
        ("PeakProcessMemory", ctypes.c_size_t),
        ("PeakJobMemory", ctypes.c_size_t),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_longlong)
        for name in ("UserTime", "KernelTime", "PeriodUserTime", "PeriodKernelTime")
    ] + [
        (name, wintypes.DWORD)
        for name in ("PageFaults", "TotalProcesses", "ActiveProcesses", "TerminatedProcesses")
    ]


class ProcessOwner:
    """Keep a non-inheritable job handle until all owned work is stopped.

    spawn_owned attaches while the primary thread is suspended, before the
    Windows venv launcher or worker can start descendants. This is NOT a sandbox.
    """

    def __init__(self, pid: int, *, memory_limit: int | None = None):
        self.handle: Any = None
        self.kernel: Any = None
        if os.name != "nt":
            return
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        handle = kernel.CreateJobObjectW(None, None)
        process = kernel.OpenProcess(0x0100 | 0x0001, False, pid)
        limits = _ExtendedLimits()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if memory_limit is not None:
            limits.Basic.Flags |= 0x0200  # JOB_OBJECT_LIMIT_JOB_MEMORY (committed bytes)
            limits.JobMemory = memory_limit
        try:
            if (
                not handle
                or not process
                or not kernel.SetInformationJobObject(
                    handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
                )
                or not kernel.AssignProcessToJobObject(handle, process)
            ):
                raise OSError("Cannot establish worker process ownership")
            self.handle = handle
        finally:
            if process:
                kernel.CloseHandle(process)
            if handle and self.handle is None:
                kernel.CloseHandle(handle)

    def contains(self, pid: int) -> bool:
        """Verify a claimed native indicator actually belongs to this exact owned job."""
        if not self.handle:
            return False
        process = self.kernel.OpenProcess(0x1000, False, pid)
        inside = wintypes.BOOL()
        self.kernel.IsProcessInJob.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.BOOL),
        ]
        try:
            return bool(
                process
                and self.kernel.IsProcessInJob(process, self.handle, ctypes.byref(inside))
                and inside.value
            )
        finally:
            if process:
                self.kernel.CloseHandle(process)

    def peak_committed_bytes(self) -> int | None:
        """Observed whole-job peak commit, including launchers; not RSS/working set."""
        if not self.handle:
            return None
        limits = _ExtendedLimits()
        if not self.kernel.QueryInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits), None
        ):
            raise OSError("Cannot read owned worker resource accounting")
        return int(limits.PeakJobMemory)

    def active_processes(self) -> int:
        if not self.handle:
            return 0
        accounting = _Accounting()
        if not self.kernel.QueryInformationJobObject(
            self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
        ):
            raise OSError("Cannot confirm owned worker job exit")
        return int(accounting.ActiveProcesses)

    def statistics(self) -> dict[str, int | float]:
        """Cumulative counters for this exact owned job, including exited children."""
        if not self.handle:
            return {}
        accounting = _Accounting()
        if not self.kernel.QueryInformationJobObject(
            self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
        ):
            raise OSError("Cannot read owned job accounting")
        return {
            "cpu_seconds": (accounting.UserTime + accounting.KernelTime) / 10000000,
            "total_processes": int(accounting.TotalProcesses),
            "active_processes": int(accounting.ActiveProcesses),
            "peak_job_commit_bytes": self.peak_committed_bytes() or 0,
        }

    def terminate(self) -> None:
        if self.handle and not self.kernel.TerminateJobObject(self.handle, 1):
            raise OSError("Cannot terminate owned worker job")

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


async def reap(process: asyncio.subprocess.Process, owner: ProcessOwner | None) -> None:
    """No WMI/taskkill subprocess, name lookup or broad process termination."""
    deadline = asyncio.get_running_loop().time() + 3
    try:
        if owner is not None:
            owner.terminate()
        elif process.returncode is None:
            process.kill()
        await asyncio.wait_for(
            process.wait(), max(0.001, deadline - asyncio.get_running_loop().time())
        )
        # Venv launcher exit is not proof its Python descendants released files.
        # Query our exact job, never enumerate/kill unrelated process names.
        while owner is not None and owner.active_processes():
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Owned worker descendants did not exit within the reap deadline")
            await asyncio.sleep(0.01)
    finally:
        if owner is not None:
            owner.close()


async def spawn_owned(
    *args: str, job_memory_limit: int | None = None, **kwargs: Any
) -> tuple[asyncio.subprocess.Process, ProcessOwner]:
    """Finish an in-flight OS spawn even on cancellation, then reap that exact child."""
    if job_memory_limit is not None and (
        os.name != "nt"
        or type(job_memory_limit) is not int
        or not 16 * 1024**2 <= job_memory_limit <= 2 * 1024**3
    ):
        raise ValueError("A native Windows job memory limit from 16 MiB to 2 GiB is required")
    if os.name == "nt":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | getattr(
            subprocess, "CREATE_SUSPENDED", 4
        )
    spawning = asyncio.create_task(asyncio.create_subprocess_exec(*args, **kwargs))
    owner = None
    try:
        process = await asyncio.shield(spawning)
        owner = ProcessOwner(process.pid, memory_limit=job_memory_limit)
        if os.name == "nt":
            _resume_primary(process.pid)
        return process, owner
    except BaseException:
        process = await spawning
        await reap(process, owner)
        raise


def _resume_primary(pid: int) -> None:
    """Resume only the primary thread of our newly created suspended process."""

    class Entry(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("usage", wintypes.DWORD),
            ("thread_id", wintypes.DWORD),
            ("owner_pid", wintypes.DWORD),
            ("priority", wintypes.LONG),
            ("delta", wintypes.LONG),
            ("flags", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
    if snapshot in {None, ctypes.c_void_p(-1).value}:
        raise OSError("Cannot enumerate owned primary thread")
    entry, found = Entry(), []
    entry.size = ctypes.sizeof(Entry)
    try:
        present = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while present:
            if entry.owner_pid == pid:
                found.append(entry.thread_id)
            present = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        if len(found) != 1:
            raise OSError("Unexpected suspended worker thread inventory")
        thread = kernel.OpenThread(2, False, found[0])
        if not thread:
            raise OSError("Cannot open owned primary thread")
        try:
            if kernel.ResumeThread(thread) != 1:
                raise OSError("Cannot resume owned primary thread")
        finally:
            kernel.CloseHandle(thread)
    finally:
        kernel.CloseHandle(snapshot)
