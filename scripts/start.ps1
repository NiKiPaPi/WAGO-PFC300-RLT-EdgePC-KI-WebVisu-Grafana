$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop mit Linux-Containern und Compose v2 installieren/starten. Keine automatische Installation.' }
if (-not (Test-Path -LiteralPath '.env')) { throw 'Zuerst python scripts/init_env.py ausführen.' }
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose-Konfiguration ungültig' }
docker compose up -d --build --wait --wait-timeout 240
if ($LASTEXITCODE -ne 0) { throw 'Start fehlgeschlagen. docker compose logs --tail 100 ausführen; Zugangsdaten nicht weitergeben.' }
Write-Host 'HMI: http://localhost:8080  Grafana: http://localhost:3000'
