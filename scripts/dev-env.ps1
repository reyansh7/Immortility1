$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (Test-Path "$repo/.tools/cargo/bin/cargo.exe") {
  $env:CARGO_HOME = "$repo/.tools/cargo"
  $env:RUSTUP_HOME = "$repo/.tools/rustup"
  $env:PATH = "$env:CARGO_HOME/bin;$env:PATH"
}
$env:UV_CACHE_DIR = "$repo/.cache/uv"
$vswhere = 'C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
if (Test-Path $vswhere) {
  $vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  if ($vs -and (Test-Path "$vs/Common7/Tools/Microsoft.VisualStudio.DevShell.dll")) {
    Import-Module "$vs/Common7/Tools/Microsoft.VisualStudio.DevShell.dll"
    Enter-VsDevShell -VsInstallPath $vs -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
  }
}
