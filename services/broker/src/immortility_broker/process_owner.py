"""Owned Windows process trees. A job is a cleanup boundary, NOT an OS sandbox."""

import asyncio
import contextlib
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


def process_identity(pid: int) -> tuple[int, str] | None:
    """Creation time (FILETIME ticks) and image path of a live process, or None.

    The creation time distinguishes a recycled PID from the process we started.
    """
    if os.name != "nt" or pid <= 0:
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None  # STILL_ACTIVE is 259
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
            return None
        created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(1024)
        image = ""
        if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            image = buffer.value
        return created, image
    finally:
        kernel.CloseHandle(handle)


def _snapshot_children() -> dict[int, list[int]]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    class Entry(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("usage", wintypes.DWORD),
            ("process_id", wintypes.DWORD),
            ("heap", ctypes.c_size_t),
            ("module_id", wintypes.DWORD),
            ("threads", wintypes.DWORD),
            ("parent", wintypes.DWORD),
            ("priority", wintypes.LONG),
            ("flags", wintypes.DWORD),
            ("exe", wintypes.WCHAR * 260),
        ]

    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    children: dict[int, list[int]] = {}
    if snapshot in {None, ctypes.c_void_p(-1).value}:
        return children
    entry = Entry()
    entry.size = ctypes.sizeof(Entry)
    try:
        present = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while present:
            children.setdefault(int(entry.parent), []).append(int(entry.process_id))
            present = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return children


def descendants(root: int) -> list[int]:
    """Descendants of one process, excluding PIDs created before it (recycled parent IDs)."""
    if os.name != "nt" or root <= 0:
        return []
    identity = process_identity(root)
    floor = identity[0] if identity else None
    children = _snapshot_children()
    ordered: list[int] = []
    pending = list(children.get(root, []))
    while pending:
        pid = pending.pop()
        if pid == root or pid in ordered:
            continue
        found = process_identity(pid)
        # A child cannot predate its parent. An older process only reuses a stale parent ID.
        if found is None or (floor is not None and found[0] < floor):
            continue
        ordered.append(pid)
        pending.extend(children.get(pid, []))
    return ordered


def _terminate_pids(pids: list[int]) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for pid in pids:
        handle = kernel.OpenProcess(0x0001, False, pid)
        if handle:
            kernel.TerminateProcess(handle, 1)
            kernel.CloseHandle(handle)


def _terminate_descendants(root: int) -> None:
    """Stop children of one process we created. Other process IDs are left running."""
    if os.name != "nt" or root <= 0:
        return
    _terminate_pids(list(reversed(descendants(root))))


def terminate_recorded_tree(pid: int, created: int, image_prefix: str) -> bool:
    """Stop a process this broker recorded as its own, only if PID, start time and image match.

    Returns True when the recorded process was found and terminated. An unrelated process
    that happens to reuse the PID or hold the same port is never touched.
    """
    identity = process_identity(pid)
    if identity is None:
        return False
    found_created, image = identity
    if found_created != created:
        return False
    if not image or not os.path.normcase(image).startswith(os.path.normcase(image_prefix)):
        return False
    _terminate_pids(list(reversed(descendants(pid))) + [pid])
    return True


async def reap(process: asyncio.subprocess.Process, owner: ProcessOwner | None) -> None:
    """No WMI/taskkill subprocess, name lookup or broad process termination."""
    deadline = asyncio.get_running_loop().time() + 3
    try:
        if owner is not None and owner.handle:
            owner.terminate()
        elif process.returncode is None:
            # No second job is available when this process already inherited one.
            # Stop only descendants of the process we created, then that process.
            # A failed descendant lookup must never stop us from killing the exact
            # child we own (that would leak it and mask the caller's original error).
            try:
                _terminate_descendants(process.pid)
            except Exception:  # noqa: BLE001 - best effort; the owned child is killed below
                pass
            finally:
                with contextlib.suppress(ProcessLookupError):
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
