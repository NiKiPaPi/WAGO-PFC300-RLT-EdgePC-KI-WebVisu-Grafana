# Tatsächliche Docker-Abnahme — 10.10.2026

Nach dem vom Benutzer ausgeführten Windows-Neustart wurde Docker Desktop gestartet. Engine 29.8.2, Linux/WSL2, Compose v5.5.1. Sechs dauerhafte Services sind gesund; broker-init beendet sich nach erfolgreicher Einrichtung mit Exitcode 0.

| Prüfumfang | Ergebnis | Nachweis |
|---|---|---|
| Docker-Build und kontrollierter Start | Bestanden, alle Healthchecks gesund | Lokaler Compose-Start Exitcode 0; container-state.json |
| Operator 20→22 °C, Command-ID, Audit, dynamische Temperatur, Influx und Grafana, Viewer-Schreibsperre | 13 Prüfungen bestanden | e2e-results.json |
| Ungültige Eingabe, Operator-Rechte, Interlock, Alarm aktiv/quittiert/zurückgekehrt, Duplikate, fehlende Bestätigung, Wiederverbindung, Historienpersistenz | 14 Prüfungen bestanden | docker-acceptance-results.json |
| Tatsächlich provisionierte Grafana-Panels über Datenquellen-API | Beide Panels erfolgreich, jeweils drei Serien | grafana-query-results.json |
| Sieben Volume-Backups und unabhängige Wiederherstellung | 6 Prüfungen bestanden | backup-restore-results.json |
| Reales HMI/Grafana im Headless Edge; Desktop/Tablet/Phone-Viewports | 20 Browserprüfungen bestanden, inklusive Einheiten und gemischter Achsen; Screenshots visuell geprüft | docker-ui-results.json; docker-hmi-*.png; docker-grafana*.png |
| API-/Modellregression | 26 Tests bestanden, eine bekannte Starlette/AnyIO-DeprecationWarning | test-results.xml |

Die reale HMI/MQTT/Influx/Grafana-Kette wurde verwendet. Keine HTTP-Testdouble-Historie im Compose-Betrieb. Die vorherigen Loopback-Prüfungen und deren Screenshots bleiben als frühere Entwicklungsnachweise erhalten.

End-to-End-Command-ID: `f67cf663-b348-4d10-bd30-f00fc6ceab4f`. Der akzeptierte Sollwert ist 22 °C. Die Isttemperatur wurde nicht direkt übernommen; im 120-s-Sampling stieg sie von etwa 19,80 auf 21,31 °C. Modelltests prüfen zusätzlich die Annäherung über 600 Simulationssekunden. Das ist eine Simulation, keine physische RLT-Regelungsabnahme.

Gateway-Ausfall: Container simulation vorübergehend pausiert; unmittelbar danach angenommene HTTP-Anforderung erhielt keine Gateway-Bestätigung. API meldete Timeout, Telemetrie wurde veraltet. Nach Resume blieb der Sollwert 22 °C; die inzwischen abgelaufene 24-°C-Anforderung wurde nicht ausgeführt. Interlock wurde nach dem Test zurückgesetzt.

Persistenz: Identischer festgelegter UTC-Zeitraum der Zulufttemperatur wurde vor/nach Influx/Grafana-Neustart verglichen. CSV-Ausgaben waren identisch. Backup stoppt Dienste für konsistente Archive. Wiederherstellung erfolgte in separat benannte temporäre Volumes. Benutzer/Audit/Befehle/Einstellungen, akzeptierter Sollwert und Idempotenzjournal wurden verglichen; die wiederhergestellte InfluxDB lieferte denselben UTC-Zeitraum wie die Quelle. Grafana-Datenbank wurde im Wiederherstellungsvolume nachgewiesen. Temporäre Wiederherstellungscontainer/-volumes wurden entfernt; produktive Volumes und Backup-Archive bleiben erhalten.

Im ersten echten Start wurden zwei Fehler erkannt und behoben: Die ausschließlich interne Netzwerkzuordnung verhinderte veröffentlichte Windows-Ports; HMI/Grafana erhielten ein separates Web-Netz mit weiterhin ausschließlich 127.0.0.1-Bindungen. Der Simulations-Healthcheck erkannte eine nicht zyklisch aktualisierte Heartbeat-Datei; sie wird jetzt bei jedem Zeitschritt aktualisiert. Später wurde ein durch Grafana automatisch heruntergeladenes inkompatibles optionales Loki-Plugin erkannt und deaktiviert. Preinstallation und Plugin-Updateprüfung sind deaktiviert, die eingebaute Influx-Datenquelle bleibt aktiv. Grafana-Seriennamen/Einheiten werden über eindeutige Query-IDs pro Tag zugeordnet; die native Flux-Zeitspalte bleibt erhalten.

Grenzen: Ausschließlich lokale Simulationsabnahme. Keine echten Tablets/Smartphones im LAN geprüft; responsive Viewports werden im Browser getestet. Keine reale PLC-/I/O-Verbindung, keine WebVisu, kein Edge-Deployment, keine sicherheitsgerichtete Freigabe. HTTPS/LAN, Dauerlast, reale Geräteparameter und reale Schutzfunktionen bleiben gesondert zu klären. Historische Viewports 6 h/24 h/7 Tage sind konfiguriert, aber die Demo besitzt noch keine so lange Laufhistorie. Backup-Restore in bestehende Volumes arbeitet als Overlay; exakte Wiederherstellung ist mit frischen separaten Volumes geprüft.
