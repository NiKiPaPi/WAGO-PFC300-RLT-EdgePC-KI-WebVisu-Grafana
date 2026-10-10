# Tatsächlich ausgeführte Prüfungen — 10.10.2026

Projekt war leer; keine fremden Projekte geändert. Keine reale PLC-Kommunikation, kein Edge-Zugriff. Docker Desktop/CLI wurde weder im PATH noch am Standardinstallationspfad gefunden. Docker wurde nicht installiert.

| Prüfung | Tatsächliches Ergebnis | Nachweis |
|---|---|---|
| Python API/Modell/Protokoll-Tests | 26 bestanden; eine DeprecationWarning aus Starlette/AnyIO, kein Fehler | test-results.xml |
| TypeScript strict/noEmit | Bestanden | tsc-Aufruf in lokaler Entwicklungsumgebung |
| Vite Produktionsbuild | Bestanden; 28 Module, JS ca. 205 kB, CSS ca. 5 kB | frontend/dist |
| Python compileall | Bestanden | backend, simulation, contracts, scripts |
| Compose YAML-Struktur | 7 Services erfolgreich geparst | PyYAML; kein Ersatz für docker compose config |
| Reales MQTT + API + Uvicorn-WebSocket auf Loopback | 13 Prüfungen bestanden | mqtt-integration-results.json |
| Headless Edge: tatsächliches React-HMI über Loopback-MQTT | 17 Prüfungen bestanden; Desktop 1440×1000, Tablet 820×1180, Smartphone 390×844, zusätzlich Kommunikationswarnung | ui-results.json; hmi-desktop/tablet/phone.png |
| Visuelle Screenshotprüfung | Drei Screenshots geprüft; Layout innerhalb der Seite, SVG auf kleinen Geräten horizontal scrollbar | hmi-desktop/tablet/phone.png |
| Frontend-Lockfile, eingefrorene Installation | pnpm 11.19.0 erfolgreich; ausschließlich esbuild-Script freigegeben | pnpm-lock.yaml; pnpm-workspace.yaml |
| Influx-Line-Protocol-Encoding | Numeric/State getrennt an HTTP-Testdouble geliefert | mqtt-integration-results.json |
| Docker build/Start/Healthchecks | Nicht durchgeführt | Docker nicht verfügbar |
| Echte InfluxDB / Grafana-Trends / Persistenz nach Container-Neustart | Nicht durchgeführt | Docker nicht verfügbar |
| Backup/Restore | Nicht durchgeführt | Docker nicht verfügbar |

Loopback-Test verwendet aMQTT 0.11.3 als temporären Testbroker. Das ist echte MQTT-TCP-Kommunikation, aber kein Mosquitto-ACL-Test. Der Influx-HTTP-Endpunkt ist ausdrücklich ein Testdouble (204-Antwort und Erfassung der geschriebenen Zeilen). Keine Behauptung, dass InfluxDB oder Grafana damit live geprüft wurden. Default-Compose verwendet ausschließlich Mosquitto, InfluxDB und Grafana, keinen Testdouble.

API-/Modelltests prüfen vollständige Tag-Snapshots, endliche Zahlen und Grenzen, readonly/unbekannte Tags, dynamische PI-Reaktion ohne Sollwert-Istwert-Zuweisung, An-/Abfahrfolge, Handverriegelung, Heiz/Kühl-Exklusivität, Alarmzyklen, persistente Idempotenz, abgelaufene Befehle, Ausgangswert-Konflikte, Rollen, fremden Origin, Benutzerverwaltung, korrelierte Auditzeilen, fehlende/verspätete Bestätigung, Neustart ohne Replay sowie WebSocket-Authentifizierung. API-Unit-Tests verwenden einen Publisher-Testdouble; die separate Loopback-Prüfung bestätigt die reale Transportkette.

Umgebungseinschränkungen: Sandbox-DNS blockierte zuerst Dependency-Downloads; kontrollierte, auf das Projekt bezogene Installation erfolgte danach außerhalb dieser Einschränkung. Sandbox-Windows-realpath/Threadverhalten blockierte zunächst Build/TestClient; dieselben Projektprüfungen liefen anschließend erfolgreich. Keine systemweite Installation. Python-Lockfile und pnpm-Lockfile enthalten konkrete Versionsauflösung.

Offene Gesamtabnahme: Compose auf einem geprüften Docker-Desktop-PC starten, scripts/e2e.py ausführen, Grafana-Kurven/Einheiten/Lücken manuell kontrollieren und Historienpersistenz sowie Backup/Restore prüfen. Keine Gesamtfreigabe für reale Anlagen.

## Ergänzung nach Installation und Neustart

Die oben genannten Einschränkungen dokumentieren den früheren Stand. Die tatsächliche Docker-Abnahme wurde anschließend durchgeführt: siehe [DOCKER_ACCEPTANCE_REPORT.md](DOCKER_ACCEPTANCE_REPORT.md) und die separaten Docker-/E2E-/Backup-Nachweise. Keine Freigabe für reale Anlagen.
