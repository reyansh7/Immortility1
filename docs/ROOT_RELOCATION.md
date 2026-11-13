# Root relocation — 2026-11-13

The project is now rooted directly at `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY`.
All 35 top-level items from the nested directory were moved, including hidden
configuration and dependency/tool directories. 158 first-party files were hash-checked
before path documentation was edited. Existing outer-folder documents were retained.
The old running companion was stopped to release the verified-empty wrapper directory,
which was then removed. Application history under LocalAppData was not moved or deleted.

Python entry points and pnpm links contained absolute old paths and were regenerated
from the unchanged uv and pnpm lockfiles. The 30 Python tests, 4 UI tests, lint/type
checks and frontend build passed from the new root. The native executable was rebuilt
because its supervisor embeds the Cargo manifest location. No Git history existed to move.

Use `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1` from this
directory. The original content inventory is in ignored `relocation-manifest.local.json`;
it contains hashes and filenames, never credential values.
