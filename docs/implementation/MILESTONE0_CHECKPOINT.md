# Milestone 0 checkpoint — 2026-11-17

No commit, reset, delete, or cache move was performed. This file is a record so the dirty tree can be recognized. It does not contain file contents or credentials.

- Repository: `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY`
- Branch: `main`, tracking `origin/main`
- HEAD: `edafc64abca0e7340f46a4068dad4b2a33fdd6f2` (`done testing`)
- Dirty paths at inspection: 61 (43 modified, 18 untracked), before this checkpoint and the permission-policy slice
- Hermes on disk: `%LOCALAPPDATA%\hermes\hermes-agent`, version `0.21.1`, revision `04b88a4c0a7fe05ebe3bf053a103a39fe6638f11` (matches the reviewed pin)
- Hermes 0.23.2 is not installed. The warm gateway was not switched on.

`.cache`, `.tools`, and `.venv` are still inside this OneDrive folder. Their reparse attribute is the OneDrive placeholder bit, not a junction to another drive. Nothing was moved.

The folder literally named `%SystemDrive%` contains four files under `ProgramData\Microsoft\Windows\Caches\`. It looks like a helper expanded a missing environment variable. It was inspected and left in place.

Commit and relocation both need a separate approval.

Python baseline after the permission gate: 487 passed, 0 failed, 0 skipped, 137.79 s. Frontend and Rust were not rerun. No 50-task tool benchmark was run, so the 90% target is not claimed.
