$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Stop fehlgeschlagen' }
