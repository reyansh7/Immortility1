<#
Build a self-contained canary desktop without touching the production executable.

The production launcher (scripts/immortility.ps1) runs
apps\desktop\src-tauri\target\release\immortility-desktop.exe, so this script never
builds into the repository's target directory. Output goes to -TargetDir
(default %TEMP%\immortility-canary-build). It writes canary-build.json with:
  * release exe path, size and SHA-256, built with --features custom-protocol
  * whether the Vite-hashed dist asset names are embedded in the release exe
  * the same check on a no-feature debug build, which must NOT embed them
    (that build is what `tauri dev` produces and it loads devUrl instead)
#>
param(
    [string]$TargetDir = (Join-Path $env:TEMP "immortility-canary-build"),
    [switch]$SkipDebugCheck
)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$tauriDir = Join-Path $repo "apps\desktop\src-tauri"
$production = Join-Path $tauriDir "target\release\immortility-desktop.exe"
$cargo = (Get-Command cargo.exe -ErrorAction SilentlyContinue).Source
if (-not $cargo) {
    foreach ($c in "$repo\.tools\cargo\bin\cargo.exe", "$env:USERPROFILE\.cargo\bin\cargo.exe",
                   "$env:USERPROFILE\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe") {
        if (Test-Path $c) { $cargo = $c; break }
    }
}
if (-not $cargo) { throw "cargo.exe was not found." }
$env:PATH = (Split-Path $cargo) + ";" + $env:PATH
if ((Resolve-Path -LiteralPath $TargetDir -ErrorAction SilentlyContinue) -and
    ((Resolve-Path $TargetDir).Path -eq (Resolve-Path (Join-Path $tauriDir "target") -ErrorAction SilentlyContinue).Path)) {
    throw "Refusing to build into the repository target (production exe lives there)."
}
$prodBefore = if (Test-Path $production) { (Get-FileHash $production).Hash } else { "absent" }

Push-Location (Join-Path $repo "apps\desktop")
try {
    & pnpm.cmd build
    if ($LASTEXITCODE) { throw "Frontend build failed." }
} finally { Pop-Location }
$assets = @(Get-ChildItem (Join-Path $repo "apps\desktop\dist\assets") -File |
    Where-Object { $_.Name -match "-[A-Za-z0-9_-]{8}\.(js|css)$" } | ForEach-Object { $_.Name })
if (-not $assets.Count) { throw "No hashed dist assets found." }

function Embedded($exe) {
    $bytes = [System.IO.File]::ReadAllBytes($exe)
    $text = [System.Text.Encoding]::ASCII.GetString($bytes)
    return @($assets | Where-Object { $text.Contains($_) }).Count
}

$env:CARGO_TARGET_DIR = $TargetDir
Push-Location $tauriDir
try {
    $t0 = Get-Date
    & $cargo build --release --features custom-protocol
    if ($LASTEXITCODE) { throw "Release build failed." }
    $releaseSeconds = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $debugEmbedded = $null
    if (-not $SkipDebugCheck) {
        & $cargo build
        if ($LASTEXITCODE) { throw "Debug (devUrl) build failed." }
        $debugEmbedded = Embedded (Join-Path $TargetDir "debug\immortility-desktop.exe")
    }
} finally {
    Pop-Location
    Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue
}
$exe = Join-Path $TargetDir "release\immortility-desktop.exe"
$prodAfter = if (Test-Path $production) { (Get-FileHash $production).Hash } else { "absent" }
$result = [ordered]@{
    built = (Get-Date).ToString("o")
    release_exe = $exe
    release_bytes = (Get-Item $exe).Length
    release_sha256 = (Get-FileHash $exe).Hash
    release_build_seconds = $releaseSeconds
    dist_assets = $assets.Count
    release_embedded_assets = Embedded $exe
    debug_no_feature_embedded_assets = $debugEmbedded
    production_exe_sha256_before = $prodBefore
    production_exe_sha256_after = $prodAfter
}
$result | ConvertTo-Json | Set-Content (Join-Path $TargetDir "canary-build.json") -Encoding utf8
if ($result.release_embedded_assets -ne $assets.Count) { throw "Release exe does not embed every dist asset." }
if ($debugEmbedded) { throw "A no-feature build embedded assets; tauri dev would not use devUrl." }
if ($prodBefore -ne $prodAfter) { throw "Production exe changed." }
$result | ConvertTo-Json
