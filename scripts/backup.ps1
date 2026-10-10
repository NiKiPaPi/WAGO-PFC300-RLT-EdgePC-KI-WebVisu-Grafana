$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$backupName = 'rlt-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$backupPath = Join-Path (Get-Location) ('backups/' + $backupName)
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Stop fehlgeschlagen; keine konsistente Sicherung möglich.' }
try {
  foreach ($volumeName in @('backend_data','simulation_data','broker_config','broker_data','influx_data','influx_config','grafana_data')) {
    docker run --rm --network none --mount "type=volume,src=rlt-simulation_$volumeName,dst=/source,readonly" --mount "type=bind,src=$backupPath,dst=/backup" alpine:3.21.3 tar -czf "/backup/$volumeName.tar.gz" -C /source .
    if ($LASTEXITCODE -ne 0) { throw "Sicherung fehlgeschlagen: $volumeName" }
  }
  Write-Host "Sicherung: $backupPath. .env getrennt sicher aufbewahren; Archive enthalten personenbezogene Daten und Zugangsdaten."
} finally { docker compose start }
