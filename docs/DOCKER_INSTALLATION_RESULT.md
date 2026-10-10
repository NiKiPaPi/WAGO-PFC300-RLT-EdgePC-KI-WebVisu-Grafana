# Docker Desktop Installation — 10.10.2026

Auf ausdrücklichen Benutzerauftrag installiert:

- Docker Desktop 4.94.0, aktueller Benutzer, WSL-2-Backend.
- Docker CLI 29.8.2, Docker Compose v5.5.1.
- Microsoft WSL 2.7.13.0, Linux-Kernel 6.18.33.2-2.
- Windows-Features VirtualMachinePlatform und Microsoft-Windows-Subsystem-Linux aktiviert, mit NoRestart.

Windows 11 Pro x64, Hardwarevirtualisierung und Hypervisor aktiv, ungefähr 31 GiB RAM, LanmanServer läuft mit Starttyp Automatic. Offizieller Docker-Installer über WinGet heruntergeladen; SHA256 a9814e31049d66156477a86614e83365669677733014ec72f74229623ff3890a geprüft. Authenticode-Status Valid, Herausgeber Docker Inc. Installationsprotokoll meldet Installation succeeded. WSL-Installation erfolgreich; Ergebnis restartNeeded=true.

Installationspfad: `%LOCALAPPDATA%\Programs\DockerDesktop`. `docker --version`, `docker compose version` und `docker compose config --quiet` über den absoluten CLI-Pfad erfolgreich; Compose-Konfiguration Exitcode 0. Docker-Engine-Abfrage derzeit fehlgeschlagen, weil kein laufender Daemon erreichbar ist. Kein Container wurde gestartet.

**Nächster erforderlicher Schritt:** Windows durch den Benutzer neu starten und Docker Desktop öffnen. Danach Docker-Engine-Bereitschaft und vollständige Simulationskette prüfen. Es wurde kein automatischer Neustart ausgelöst. Keine reale PLC-Kommunikation und kein Edge-Deployment.

Frühere Testberichte und das zuvor erstellte ZIP beschreiben den Stand vor dieser Installation. Container-/Influx-/Grafana-Abnahme und Backup/Restore bleiben bis zur tatsächlichen Durchführung offen.

Nachtrag: Der Benutzer hat Windows neu gestartet. Docker Desktop wurde gestartet, die Linux-Engine läuft und die reale Simulationskette wurde abgenommen. Siehe DOCKER_ACCEPTANCE_REPORT.md. Die obige Installationsbeschreibung bleibt als zeitlich abgegrenzter Nachweis erhalten.
