# RLT / LAB — WAGO PFC300 Simulation Demo

Ausführbare Simulationsanwendung mit React/TypeScript/SVG HMI, FastAPI, MQTT, dynamischem RLT-Modell, InfluxDB und Grafana. **Keine reale SPS-Kommunikation, kein Edge-Deployment, keine CODESYS WebVisu.**

```powershell
python scripts/init_env.py
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

Voraussetzung: Docker Desktop/Compose v2 mit Linux-Containern. HMI unter http://localhost:8080, Grafana unter http://localhost:3000. Zugangsdaten werden lokal in .env erzeugt, niemals im Quellcode mitgeliefert.

- [Installation und Bedienung](docs/INSTALLATION.md)
- [Architektur und Grenzen](docs/ARCHITECTURE.md)
- [Datenvertrag / Tag-Liste](contracts/tags.json)
- [MQTT-Protokoll](docs/MQTT.md)
- [Spätere SPS-Schnittstelle](plc/INTERFACE.md)
- [Testnachweis](docs/TEST_REPORT.md)
- [Abnahmebedingungen](docs/ACCEPTANCE.md)

Die tatsächliche Docker-Simulationskette läuft und wurde mit Mosquitto, InfluxDB und Grafana geprüft. Operator-Sollwert 20→22 °C, Audit, Timeout/Veralterung, Historie nach Neustart und unabhängige Wiederherstellung sind nachgewiesen. Siehe [Container-Abnahme](docs/DOCKER_ACCEPTANCE_REPORT.md). Das erste ZIP 1.0.0 bleibt als gesicherter früherer Stand erhalten; die geprüfte Containerfassung wird als 1.0.1 ausgeliefert.
