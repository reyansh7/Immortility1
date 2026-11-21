<#
M2/P0 verified backup of the Immortility repository and broker data (no elevation).

Creates, outside OneDrive (default %LOCALAPPDATA%\Immortility-backups\<stamp>):
  repo.bundle          git bundle of every local ref (branches incl. the unpushed m1.7 and
                       m2 work, the checkpoint branch, tags), verified with `git bundle verify`
  data\state.sqlite3   consistent SQLite snapshot of the production broker DB. The live files
                       are first copied to a scratch dir and the snapshot is taken from that
                       copy, so the production DB is never opened by this script.
  data\*.json          small production flag/config files (no secrets live there; keys are in
                       Windows Credential Manager and are NOT exported)
  manifest.json        sizes + SHA-256 of everything above, git HEADs, integrity results

Then a restore drill: the snapshot is restored into a scratch dir, PRAGMA integrity_check
must be "ok" and the task/event/memory row counts must equal the source copy.

Never deletes, moves or modifies anything in the repo or %LOCALAPPDATA%\Immortility.
Large re-downloadable directories (models, voice, hermes-*, canary-*) are listed in the
manifest with their size but not copied.
#>
param(
    [string]$Repo = (Split-Path $PSScriptRoot -Parent),
    [string]$Data = "$env:LOCALAPPDATA\Immortility",
    [string]$Destination = "$env:LOCALAPPDATA\Immortility-backups"
)
$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = Join-Path $Destination $stamp
if ($out -match "OneDrive") { throw "Refusing to write a backup inside OneDrive." }
if (Test-Path -LiteralPath $out) { throw "Backup folder already exists: $out" }
New-Item -ItemType Directory -Force (Join-Path $out "data") | Out-Null
$python = Join-Path $Repo ".venv\Scripts\python.exe"
$manifest = [ordered]@{ created = (Get-Date).ToString("o"); repo = $Repo; data = $Data; files = [ordered]@{} }

# 1. Repository: every local ref, verified.
$bundle = Join-Path $out "repo.bundle"
& git -C $Repo bundle create $bundle --all 2>&1 | Out-Null
if ($LASTEXITCODE) { throw "git bundle create failed" }
& git -C $Repo bundle verify $bundle 2>&1 | Out-Null
if ($LASTEXITCODE) { throw "git bundle verify failed" }
$manifest.git = [ordered]@{
    head = (& git -C $Repo rev-parse HEAD); branch = (& git -C $Repo branch --show-current)
    refs = @(& git -C $Repo for-each-ref --format="%(refname:short) %(objectname:short)" refs/heads refs/tags)
    dirty = [bool](& git -C $Repo status --porcelain)
    bundle_verified = $true
}

# 2. Production data: copy live files to scratch, snapshot from the copy.
$scratch = Join-Path $env:TEMP ("imm-backup-" + $stamp)
New-Item -ItemType Directory -Force $scratch | Out-Null
foreach ($name in "state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm") {
    $src = Join-Path $Data $name
    if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination $scratch }
}
$snapshot = Join-Path $out "data\state.sqlite3"
$code = @'
import json, sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
s = sqlite3.connect(src)
d = sqlite3.connect(dst)
s.backup(d)
def counts(c):
    out = {}
    for t in ("tasks", "events", "memory_fts", "confirmed_facts"):
        try: out[t] = c.execute(f"select count(*) from {t}").fetchone()[0]
        except sqlite3.Error: out[t] = None
    return out
print(json.dumps({"source": counts(s), "integrity": d.execute("pragma integrity_check").fetchone()[0], "snapshot": counts(d)}))
s.close(); d.close()
'@
$result = $code | & $python - (Join-Path $scratch "state.sqlite3") $snapshot | ConvertFrom-Json
if ($result.integrity -ne "ok") { throw "Snapshot integrity_check failed: $($result.integrity)" }
$manifest.sqlite = $result
foreach ($f in Get-ChildItem -LiteralPath $Data -File -Filter *.json) {
    Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $out "data")
}
$manifest.not_copied = @(Get-ChildItem -LiteralPath $Data -Directory | ForEach-Object {
    $size = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    [ordered]@{ dir = $_.Name; bytes = [int64]$size }
})

# 3. Restore drill into scratch: integrity + identical counts.
$drill = Join-Path $scratch "restore-drill"
New-Item -ItemType Directory -Force $drill | Out-Null
Copy-Item -LiteralPath $snapshot -Destination (Join-Path $drill "state.sqlite3")
$check = @'
import json, sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
out = {"integrity": c.execute("pragma integrity_check").fetchone()[0]}
for t in ("tasks", "events", "memory_fts", "confirmed_facts"):
    try: out[t] = c.execute(f"select count(*) from {t}").fetchone()[0]
    except sqlite3.Error: out[t] = None
print(json.dumps(out))
'@
$restored = $check | & $python - (Join-Path $drill "state.sqlite3") | ConvertFrom-Json
$same = $true
foreach ($t in "tasks", "events", "memory_fts", "confirmed_facts") { if ($restored.$t -ne $result.source.$t) { $same = $false } }
$manifest.restore_drill = [ordered]@{ integrity = $restored.integrity; counts_match_source = $same; restored = $restored }
if ($restored.integrity -ne "ok" -or -not $same) { throw "Restore drill failed." }

foreach ($f in Get-ChildItem -LiteralPath $out -Recurse -File) {
    $manifest.files[$f.FullName.Substring($out.Length + 1)] = [ordered]@{ bytes = $f.Length; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash }
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out "manifest.json") -Encoding utf8
Remove-Item -LiteralPath $scratch -Recurse -Force  # only the scratch copy this script made
Write-Output "BACKUP_OK $out"
