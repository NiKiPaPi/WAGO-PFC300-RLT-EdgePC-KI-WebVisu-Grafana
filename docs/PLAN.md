# Architektur und Umsetzung

Bestandsaufnahme 10.10.2026: Projektverzeichnis leer, keine lokalen AGENTS.md gefunden. Gebündelte Python- und Node-Laufzeiten vorhanden; Docker CLI, FastAPI, MQTT-Client und npm nicht im PATH. Keine Installation systemweiter Komponenten. Keine reale Kommunikation.

1. Gemeinsamer Vertrag v1 mit Tag-Katalog, UTC, Qualität und MQTT-Nachrichten.
2. Deterministisches Simulationsmodell; MQTT als einzige Befehls-/Telemetrieverbindung.
3. FastAPI: persistente Benutzer, Sessions, Befehlsjournal und Audit in SQLite; WebSocket-Snapshots; Influx-Aufzeichnung.
4. React/TypeScript/SVG HMI; Grafana ausschließlich lesend.
5. Compose, lokale Geheimniserzeugung, Tests und dokumentierte Grenzen.

Alle physikalischen Modellwerte sind konfigurierbare Simulationsannahmen. Reale Grenzwerte und Schutzketten: TBD – technische Klärung erforderlich. PFC300 und Edge bleiben deaktiviert.
