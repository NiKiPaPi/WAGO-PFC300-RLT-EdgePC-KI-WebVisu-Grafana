param([Parameter(Mandatory=$true)][string]$BackupDirectory, [string]$VolumePrefix='rlt-simulation', [switch]$NoStart)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$restorePath = (Resolve-Path -LiteralPath $BackupDirectory).Path
if (-not $restorePath.StartsWith(((Join-Path (Get-Location) 'backups') + [IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) { throw 'Nur lokale Projektbackups verwenden.' }
if ($VolumePrefix -ne 'rlt-simulation' -and ($VolumePrefix -notmatch '^rlt-simulation-restore-[a-zA-Z0-9-]+$' -or -not $NoStart)) { throw 'Separates Wiederherstellungsziel muss rlt-simulation-restore-* mit NoStart sein.' }
foreach ($volumeName in @('backend_data','simulation_data','broker_config','broker_data','influx_data','influx_config','grafana_data','weather_data')) {
  if (-not (Test-Path -LiteralPath (Join-Path $restorePath "$volumeName.tar.gz"))) { throw "Archiv fehlt: $volumeName" }
}
if ($VolumePrefix -eq 'rlt-simulation') {
  docker compose stop
  if ($LASTEXITCODE -ne 0) { throw 'Stop fehlgeschlagen' }
}
foreach ($volumeName in @('backend_data','simulation_data','broker_config','broker_data','influx_data','influx_config','grafana_data','weather_data')) {
  # Restore overlays the stopped volume. Use a clean separately named Compose project for a complete recovery test.
  docker run --rm --network none --mount "type=volume,src=${VolumePrefix}_$volumeName,dst=/target" --mount "type=bind,src=$restorePath,dst=/backup,readonly" alpine:3.21.3 tar -xzf "/backup/$volumeName.tar.gz" -C /target
  if ($LASTEXITCODE -ne 0) { throw "Wiederherstellung fehlgeschlagen: $volumeName" }
}
if (-not $NoStart) { docker compose start }
