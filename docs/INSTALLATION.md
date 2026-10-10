# Installation und Bedienung

Voraussetzungen: Windows-PC, Docker Desktop mit laufendem Linux-Container-Backend, Compose v2 mit `--wait`, Python 3.12 für Geheimniserzeugung/Testskripte. Keine selbständige Installation von Docker Desktop. Architektur/Ressourcen eines späteren Edge-Servers wurden nicht geprüft. Keine Hardware-Kompatibilitätszusage.

Im Projektverzeichnis:

```powershell
python scripts/init_env.py
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

Alternativ nach Erzeugung der .env: `docker compose config --quiet`, dann `docker compose up -d --build --wait --wait-timeout 240`. Images sind auf Versionen festgelegt, Python- und Frontend-Abhängigkeiten durch Lockfiles. Internet wird zum ersten Build benötigt. Produktions-Frontend wird durch Nginx ausgeliefert. API und Simulation benötigen keinen direkten Browserzugriff auf MQTT.

HMI: http://localhost:8080. Benutzer `viewer`, `operator`, `administrator`; zugehörige initiale Passwörter lokal in .env. Passwörter nie in Screenshots/Testnachweise kopieren. Initiale Passwörter gelten nur beim ersten Anlegen der Datenbank. Später Administrator-Benutzerverwaltung verwenden. Sitzungen laufen nach einer Stunde ab; Password-/Rollenänderung widerruft vorhandene Sitzungen.

Grafana: http://localhost:3000, initial `admin`, Passwort aus GRAFANA_PASSWORD. Kein anonymer Zugang. HMI-Trendlinks öffnen das Dashboard mit ausgewählten Tags und Zeitbereich. Grafana erfordert eine eigene Anmeldung. Grafana-Viewer-Konten bei Bedarf manuell anlegen; HMI-Rollen und Grafana-Benutzer sind getrennt. Grafana enthält keine Anlagenbedienung.

API-Dokumentation über den HMI-Proxy: http://localhost:8080/api/docs ist nicht belegt; die statische OpenAPI-Datei `docs/openapi.json` beschreibt alle Endpunkte. Swagger ist im Backend unter `/docs` erreichbar, aber der Backend-Port wird nicht veröffentlicht. Für die lokale Demo reicht die mitgelieferte OpenAPI-Datei.

Auto: Klappen öffnen, ab 90 % dürfen Ventilatoren anlaufen; Zulufttemperatur wird durch PI-Ausgang mit Totzeit aus Aktuator- und Temperaturbewegung geregelt. Hand: freie Einzelvorgaben im Simulationsbereich, ohne Schutzumgehung; Ventilatoren laufen nur mit offenen Klappen. Aus: Ventilatoren stoppen, Klappen schließen danach, Ventile fahren zu. Interlock hat höchste Priorität; Quittierung allein entriegelt nicht. Mit fault.inject wird der Fehler aktiviert/zurückgesetzt.

Messwert anklicken: Grafana-Trend. Komponente anklicken: Detail-/Bedienfenster. Werteänderung zeigt Alt/Neu/Ziel; nach Bestätigung die Command-ID in „Bedienung“ oder „Alarme & Ereignisse“ verfolgen. „Logik ausgeführt“ ist kein physischer Zielnachweis. Viewer-Eingaben sind gesperrt; API prüft die Rolle unabhängig.

Stop: `scripts/stop.ps1` oder `docker compose stop`. Wiederstart: `docker compose start`; neue Images mit start.ps1 bauen. Volumes bleiben erhalten. `docker compose down` entfernt Container/Netz, aber keine Daten. `down -v` löscht Daten und ist kein regulärer Stop.

Nur 127.0.0.1:8080 (HMI) und 127.0.0.1:3000 (Grafana) werden veröffentlicht. HMI/Grafana besitzen zusätzlich zum internen Anlagen-Netz ein separates Web-Netz, damit Docker Desktop diese lokalen Ports tatsächlich bereitstellt. API 8000, MQTT 1883 und Influx 8086 verbleiben ausschließlich im internen Anlagen-Netz. Tablet-/Smartphone-Layouts sind mit Browser-Viewports geprüft; physische andere Geräte haben standardmäßig keinen Netzwerkzugriff. Ein explizit geprüftes LAN-/HTTPS-Konzept und Anpassung von PUBLIC_ORIGIN/Portbindungen sind dafür nötig. Es erfolgt keine Internetveröffentlichung.

HTTPS-Vorbereitung: Nginx ist der Reverse Proxy, WebSocket-Upgrade und Sicherheitsheader sind vorhanden. Für spätere Bereitstellung geprüfte Zertifikate/443-Bindung ergänzen, PUBLIC_ORIGIN auf https setzen und COOKIE_SECURE=true. Kein automatisch erzeugtes oder ungeprüft akzeptiertes Zertifikat.

Sicherung: `scripts/backup.ps1` stoppt für konsistente Volume-Archive kurz alle Dienste und startet sie danach. .env getrennt sicher aufbewahren. Wiederherstellung mit `scripts/restore.ps1 -BackupDirectory backups/rlt-...` bei gestoppten Diensten; Archive werden überlagert, neue Dateien aus der Zeit nach der Sicherung können erhalten bleiben. Für exakte Disaster-Recovery frische Volumes mit `-VolumePrefix rlt-simulation-restore-<name> -NoStart` verwenden und anschließend gezielt an Wiederherstellungscontainer anbinden. `scripts/backup_verify.py` hat die tatsächliche Wiederherstellung in unabhängige Volumes, Benutzer/Audit/Befehle/Sollwerte sowie den identischen Influx-UTC-Bereich geprüft. Produktion wurde dabei nicht überschrieben. Backups enthalten private Zugangsdaten und bleiben außerhalb des Quellcodepakets.

Tests: `python -m pip install -r requirements.lock`, `python -m pytest -q`. Optionale Loopback-Transportprüfung: `python -m pip install -r requirements-test.lock`, dann `python -m scripts.mqtt_probe`. Dieser Test verwendet aMQTT und ein explizites Influx-HTTP-Testdouble, keine echten Datenbanken. Die Testabhängigkeiten gehören nicht zum Container-Image. Container-End-to-End nach Start: `python scripts/e2e.py` (ca. 2 Minuten; ändert ausschließlich Simulationssollwerte). Manuelle UI-Abnahme: docs/ACCEPTANCE.md.

Die lokale Browser-Testdatei tests/ui.mjs erwartet Node, einen installierten Playwright-Modulpfad in PLAYWRIGHT_MODULE, einen Python-Testenvironment-Pfad in RLT_PYTHON und optional den vorhandenen Chrome-/Edge-Pfad in RLT_BROWSER_PATH. Sie startet die Loopback-Fixture und Vite nur für den Test, speichert Screenshots/Resultate und beendet die Prozesse. Kein Browser wird automatisch installiert.
