# Credential-free, same-machine frozen-lock reproduction. No models, recordings or Qwen installation.
param([string]$Output=(Join-Path '.cache/p0-reproduction' ('run-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))))
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
$destination=[IO.Path]::GetFullPath((Join-Path $root $Output))
$allowed=[IO.Path]::GetFullPath((Join-Path $root '.cache/p0-reproduction'))+[IO.Path]::DirectorySeparatorChar
if (!$destination.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)) {throw 'Reproduction must be inside .cache/p0-reproduction'}
if (Test-Path -LiteralPath $destination) {throw 'Refusing to overwrite an existing reproduction'}
$extensions=@('.py','.ts','.tsx','.js','.mjs','.cjs','.css','.rs','.json','.toml','.yaml','.yml','.md','.ps1','.lock','.ico','.html')
$files=& git -c core.quotepath=false ls-files --cached --others --exclude-standard
if ($LASTEXITCODE) {throw 'Run from the local Git checkout; no source files were copied'}
foreach($relative in $files){
  $name=[IO.Path]::GetFileName($relative)
  if ($name.StartsWith('.env') -and $name -ne '.env.example') {continue}
  if ([IO.Path]::GetExtension($relative) -notin $extensions -and $name -notin @('.env.example','.gitignore','.editorconfig')) {continue}
  if ($relative -match '^(data|workspace|models|\.cache|\.venv|\.tools|node_modules)[/\\]') {continue}
  $source=[IO.Path]::GetFullPath((Join-Path $root $relative))
  $target=[IO.Path]::GetFullPath((Join-Path $destination $relative))
  if (!$target.StartsWith($destination+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Source path escaped reproduction scope'}
  New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null
  Copy-Item -LiteralPath $source -Destination $target
}
$env:UV_CACHE_DIR=Join-Path $root '.cache/uv'
uv sync --offline --frozen --extra voice --project $destination --python 3.13
if ($LASTEXITCODE) {throw 'Frozen Python reproduction failed; populate approved caches with bootstrap-dev.ps1 first'}
pnpm.cmd --dir $destination install --offline --frozen-lockfile --ignore-scripts
if ($LASTEXITCODE) {throw 'Frozen pnpm reproduction failed; populate approved caches with bootstrap-dev.ps1 first'}
$previousHermesSource=$env:HERMES_SOURCE
try {
  $env:HERMES_SOURCE=Join-Path $destination 'missing-hermes'
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $destination 'scripts/check.ps1')
  if ($LASTEXITCODE) {throw 'Clean-source checks failed'}
} finally {
  $env:HERMES_SOURCE=$previousHermesSource
}
Write-Output ('Reproduction passed: '+$destination)
