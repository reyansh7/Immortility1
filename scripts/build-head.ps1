param(
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [switch]$Preview
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$glb = Join-Path $root "apps\desktop\public\models\immortility-head.glb"
New-Item -ItemType Directory -Force (Split-Path $glb) | Out-Null
& $Blender -b --factory-startup --python (Join-Path $root "assets\blender\immortility_head.py") -- $glb |
    Select-String -Pattern "^MESH|^EXPORTED|Error|Traceback"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $glb)) { throw "Head export failed." }
if ($Preview) {
    $out = Join-Path $root "docs\visual"
    New-Item -ItemType Directory -Force $out | Out-Null
    $portrait = Join-Path (Split-Path $glb) "immortility-head-2d.png"
    & $Blender -b --factory-startup --python (Join-Path $root "assets\blender\preview_head.py") -- $glb $out $portrait |
        Select-String -Pattern "^RENDERED|Error|Traceback"
}
