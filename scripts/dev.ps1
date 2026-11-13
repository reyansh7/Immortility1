$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/dev-env.ps1"
Set-Location (Split-Path $PSScriptRoot -Parent)
pnpm.cmd dev
if ($LASTEXITCODE -ne 0) { throw 'Desktop launch failed.' }
