# Codex Entwicklungsauftrag
## WAGO PFC300 – RLT Web-HMI & Grafana AI Demo

### 1. Ziel und verbindliche Architektur

Entwickle ein ausführbares Gebäudeautomations-Demosystem für eine RLT-Anlage mit Bedienung, Echtzeitvisualisierung und historischen Trends.

Verbindliche Architektur:

- Browser auf PC, Tablet und Smartphone
- Eigenständiges Web-HMI: React + TypeScript + SVG
- Backend API: Python FastAPI, Authentifizierung, Autorisierung, Befehlsverwaltung und Audit
- MQTT Broker / PLC Gateway: Telemetrie, Bedienbefehle und Rückmeldungen
- InfluxDB: historische Zeitreihendaten
- Grafana: Dashboards und Trends, keine Steuerungsfunktion
- WAGO PFC300 mit CODESYS: spätere Ausführung von Regelung, Anlagenlogik, Verriegelungen und I/O
- Docker Compose: Bereitstellung auf Windows-PC und später auf einem geprüften Edge Server

CODESYS WebVisu gehört ausdrücklich nicht zum Projektumfang.

„AI/KI“ bezeichnet zunächst die KI-unterstützte Entwicklung. Laufzeit-KI, beispielsweise Prognosen oder Optimierung, gehört ohne gesonderten Auftrag nicht zum Umfang.

### 2. Umfang und Arbeitsweise

Implementiere zunächst ausschließlich eine vollständige, startbare Simulationsversion ohne reale SPS und physische I/O.

Die erste Version muss die gesamte Kette enthalten:

Web-HMI → Backend → MQTT → Simulation → MQTT → Backend → Web-HMI

Telemetrie wird zusätzlich in InfluxDB gespeichert und durch Grafana dargestellt.

Die reale PFC300-Anbindung und das Edge-Deployment sind spätere, getrennt abzunehmende Phasen. Bereite ihre Schnittstellen vor, aktiviere sie jedoch nicht.

Prüfe zuerst den vorhandenen Projektstand, lokale Anweisungen und die Entwicklungsumgebung. Arbeite im aktuellen Projektverzeichnis. Verändere keine fremden Projekte und überschreibe keine bestehenden Artefakte ohne Versionssicherung.

Erstelle nach der Bestandsaufnahme eine kurze Architektur- und Implementierungsplanung und beginne anschließend mit der Entwicklung der Simulationsversion. Arbeite schrittweise und behebe festgestellte Fehler.

Installiere fehlende Komponenten nicht ungeprüft. Dokumentiere Voraussetzungen und tatsächliche Einschränkungen. Lege nachvollziehbare Softwareversionen und Lockfiles fest; vermeide unkontrollierte `latest`-Abhängigkeiten.

### 3. Projektstruktur

Verwende eine modulare Struktur:

- `/frontend` – React, TypeScript, SVG
- `/backend` – FastAPI, API, Benutzerverwaltung, Audit, Datenaufzeichnung
- `/simulation` – RLT-Modell und simulierte PLC-Logik
- `/mqtt` – Broker-Konfiguration
- `/contracts` – versionierte Datenverträge und Tag-Liste
- `/grafana` – Dashboards und Provisioning
- `/influxdb` – Datenbankkonfiguration
- `/plc` – Schnittstellendefinitionen für die spätere CODESYS-Anbindung
- `/docker` – Container- und Deployment-Konfiguration
- `/docs` – Architektur, Bedienung, Installation und Testnachweise

Die erste Version erfordert kein ausführbares CODESYS-Projekt. Beschreibe diese Grenze ausdrücklich in der Dokumentation.

### 4. Datenvertrag

Definiere vor der Implementierung eine gemeinsame, versionierte Datenbasis für Frontend, Backend, Simulation, Historie und spätere SPS.

Die Tag-Liste enthält mindestens:

- Eindeutige Tag-ID und deutsche Bezeichnung
- Komponente und Funktion
- Datentyp und Einheit
- Leserichtung beziehungsweise Schreibrichtung
- Wertebereich und Schreibberechtigung
- Zeitstempel und Datenqualität
- Zuordnung zu MQTT-Nachrichten und historischen Daten

Unterscheide konsequent:

- Angeforderter Sollwert
- Akzeptierter Sollwert
- Stellbefehl
- Rückmeldung
- Tatsächlicher Anlagenzustand

Verwende UTC für gespeicherte Zeitstempel und eine konfigurierbare lokale Zeitzone für die Anzeige.

Erfinde keine realen technischen Daten. Unbekannte Gerätedaten, Grenzwerte und reale Schutzfunktionen bleiben:

`TBD – technische Klärung erforderlich`

Für die Simulation darfst du nachvollziehbare Modellparameter festlegen. Kennzeichne sie ausdrücklich als Simulationsannahmen und halte sie konfigurierbar.

### 5. Web-HMI

Entwickle ein responsives, deutschsprachiges RLT-Anlagenbild mit:

- Außenluft, Zuluft, Abluft und Fortluft
- Außenluft- und Fortluftklappe
- Zuluft- und Abluftventilator
- Zu- und Abluftfilter
- Wärmerückgewinnung
- Heiz- und Kühlregister
- Regelventilen
- Temperatur- und Drucksensoren

Verwende SVG mit dynamischen Zuständen, klaren Luftwegen und gut lesbaren Messwerten. Animationen müssen aus tatsächlichen Rückmeldungen abgeleitet werden.

Status darf nicht ausschließlich durch Farbe vermittelt werden. Zeige zusätzlich Text oder Symbole. Stelle Kommunikationsausfall und veraltete Daten deutlich dar.

Implementiere folgende Bereiche:

1. Anlagenübersicht und RLT-Anlagenbild
2. Bedienung und Sollwerte
3. Trends und Historie
4. Alarme und Ereignisse
5. Systemeinstellungen

Ein Klick auf eine Komponente öffnet ein Bedienfenster mit Messwerten, Sollwerten, Betriebsart, Freigaben, Verriegelungen und Störungen.

Unterstütze entsprechend der definierten Betriebslogik:

- Temperatursollwertänderung
- Auto / Hand / Aus
- Ventilator Start / Stopp
- Drehzahlvorgaben
- Klappen- und Ventilstellungen

Validiere Eingaben im Frontend und verbindlich im Backend sowie in der Simulation beziehungsweise späteren SPS. Bestätigungsdialoge zeigen den alten und neuen Wert sowie das Ziel der Änderung.

### 6. Simulation und Anlagenlogik

Entwickle eine eigenständige, zeitabhängige Simulation mit:

- Temperaturentwicklung
- Ventilatordrehzahlen und Druck
- Klappen- und Ventilbewegungen
- Heiz- und Kühlwirkung
- Wärmerückgewinnung
- Vereinfachter PI-Regelung
- Zustandsmaschine
- Konfigurierbaren Störungen und Verriegelungen

Definiere die Bedeutung von Auto / Hand / Aus, die Priorität der Bedienbefehle sowie Anfahr- und Abfahrsequenzen. Handbetrieb darf simulierte Schutzfunktionen nicht umgehen.

Vermeide gleichzeitiges Heizen und Kühlen durch eine dokumentierte Regelstrategie.

Die Simulation muss auf Bedienbefehle dynamisch reagieren. Ein geänderter Temperatursollwert darf nicht einfach als Istwert übernommen werden.

Ermögliche reproduzierbare Tests durch konfigurierbare Anfangsbedingungen und gezielte Fehlereinspeisung.

Die Simulation verwendet dieselben MQTT-Nachrichtenschemas und dieselbe Befehlslogik wie die spätere SPS. Keine direkte Sonderverbindung zwischen Simulation und Web-HMI.

### 7. MQTT und Befehlsverarbeitung

Definiere getrennte Topics für:

- Telemetrie und akzeptierte Sollwerte
- Bedienbefehle
- Befehlsbestätigungen und Ergebnisse
- Alarme
- Verbindungsstatus

Verwende getrennte Namensräume und Konfigurationen für Simulation und Realbetrieb.

Jeder Befehl enthält mindestens:

- Eindeutige Command-ID
- Ziel-Tag und angeforderter Wert
- Serverseitig ermittelte Benutzeridentität
- Erstellungszeit und Ablaufzeit
- Version des Nachrichtenschemas

Unterscheide:

- Empfang
- Annahme oder Ablehnung mit Grund
- Ausführungsergebnis
- Tatsächliche Zustandsrückmeldung

Zeige einen Befehl erst nach der passenden Bestätigung als erfolgreich an. Eine Annahme bedeutet noch nicht, dass der physische Zielzustand erreicht wurde.

Implementiere:

- Timeouts und abgelaufene Befehle
- Duplikaterkennung und idempotente Verarbeitung
- Dokumentierte MQTT-QoS- und Retain-Regeln
- Verbindungsüberwachung und Wiederverbindung
- Datenalter und Qualitätskennzeichnung
- Behandlung konkurrierender Schreibzugriffe

Bedienbefehle dürfen nicht retained veröffentlicht werden. Nach Wiederverbindung dürfen alte Befehle nicht automatisch erneut ausgeführt werden.

Die Echtzeitverbindung zum Browser erfolgt über WebSocket mit einem initialen Zustandssnapshot und anschließenden Aktualisierungen.

### 8. Benutzer und Sicherheit

Implementiere:

- Viewer: Lesen und Trends anzeigen
- Operator: freigegebene Anlagenbedienung
- Administrator: Benutzer und Systemeinstellungen verwalten

Prüfe Berechtigungen serverseitig für jeden Schreibzugriff. Vertraue keiner vom Browser übermittelten Rollen- oder Benutzerangabe.

Protokolliere Bedienhandlungen mit Benutzer, Zeit, Ziel, altem und neuem Wert, Command-ID und Ergebnis.

Passwörter, Tokens und Zugangsdaten dürfen nicht im Quellcode oder in Logs stehen. Liefere eine `.env.example` ohne echte Geheimnisse.

Der Browser erhält keine PLC-, Broker- oder Datenbank-Zugangsdaten.

Begrenze die lokale Demo auf die erforderlichen Zugänge. Bereite HTTPS und einen Reverse Proxy für die spätere Bereitstellung vor. Veröffentliche das System nicht eigenständig im Internet.

Brandschutz, Frostschutz, Motorschutz und erforderliche Sicherheitsfunktionen bleiben bei einer realen Anlage in der dafür vorgesehenen SPS beziehungsweise unabhängigen Schutzeinrichtung. Die Demo stellt keinen Nachweis einer sicherheitsgerichteten Funktion dar.

Im Simulationsmodus dürfen keine Befehle an reale Anlagen gesendet werden. Die reale SPS-Anbindung bleibt standardmäßig deaktiviert und erfordert einen gesonderten ausdrücklichen Auftrag.

### 9. InfluxDB und Grafana

Zeichne mindestens folgende Daten auf:

- Zulufttemperatur: Istwert und akzeptierter Sollwert
- Abluft- und Außentemperatur
- Ventilatordrehzahlen
- Klappenstellungen
- Heiz- und Kühlventilstellungen
- Druckwerte
- Betriebszustände

Definiere konfigurierbare Abtastrate, Aufbewahrungsdauer und den Umgang mit Datenlücken. Veraltete Messwerte dürfen nicht als neue gültige Messungen gespeichert werden.

Erstelle automatisch bereitgestellte Grafana-Dashboards mit:

- Gemeinsamer Auswahl von mindestens drei Datenpunkten
- Zeitbereichen 1 h, 6 h, 24 h und 7 Tage
- Einheiten und sinnvoller Achsenzuordnung
- Darstellung von Datenlücken und Betriebszuständen

Ein Klick auf einen Messwert im Web-HMI öffnet den passenden Grafana-Trend.

Die erste Version verwendet einen geschützten Link zu Grafana. Eine iframe-Einbettung ist nicht erforderlich.

### 10. Docker und spätere Zielplattform

Das Simulationssystem muss über Docker Compose startbar sein.

Implementiere:

- Persistente Volumes
- Healthchecks und Bereitschaftsprüfungen
- Restart-Policies
- Konfiguration über Umgebungsvariablen
- Dokumentierte Ports
- Kontrolliertes Starten und Stoppen
- Sicherung und Wiederherstellung der relevanten Daten

Entwicklungsziel ist ein Windows-PC mit Docker Desktop.

Der spätere Zielserver ist ein WAGO Edge Computer 752-9401 oder ein freigegebener anderer Edge Server. Prüfe vor einem Deployment die tatsächliche CPU-Architektur, das Betriebssystem, die Container-Unterstützung und verfügbare Ressourcen. Behaupte keine ungeprüfte Hardwarekompatibilität.

### 11. Tests und Abnahme

Erstelle nachvollziehbare automatisierte Tests für Datenverträge, Befehlsverarbeitung, Berechtigungen und wesentliche Anlagenlogik sowie manuelle Tests der Bedienoberfläche.

Definiere vor der Abnahme konkrete Testbedingungen, erwartete Ergebnisse und Durchfallkriterien.

Zentrale End-to-End-Abnahme:

1. System mit dokumentiertem Ablauf starten.
2. Als Operator anmelden.
3. Zulufttemperatur-Sollwert von 20 °C auf 22 °C ändern.
4. Befehlsannahme und Ergebnis anhand der Command-ID verfolgen.
5. Dynamische Reaktion der simulierten Regelung beobachten.
6. Istwert und akzeptierten Sollwert in Grafana gemeinsam anzeigen.
7. Bedienhandlung im Audit-Protokoll nachweisen.

Zusätzlich prüfen:

- Viewer kann keine Schreibbefehle ausführen.
- Ungültige Werte werden abgelehnt.
- Verriegelungen verhindern unzulässige Bedienung.
- Doppelte Befehle verursachen keine doppelte Ausführung.
- Fehlende Bestätigung führt zu Timeout, nicht zu Erfolg.
- Kommunikationsausfall kennzeichnet Daten als veraltet.
- Wiederverbindung aktualisiert den Zustand ohne alte Befehle auszuführen.
- Alarmaktivierung, Quittierung und Rückkehr zum Normalzustand sind unterscheidbar.
- Historische Daten bleiben nach Container-Neustart erhalten.
- Mindestens drei Datenpunkte sind gemeinsam vergleichbar.
- Bedienung funktioniert auf Desktop, Tablet und Smartphone.

Dokumentiere ausschließlich tatsächlich durchgeführte Tests. Kennzeichne nicht durchgeführte Prüfungen und Einschränkungen ausdrücklich.

### 12. Lieferumfang

Liefere:

1. Vollständigen Projektquellcode
2. Startbare Docker-Compose-Konfiguration
3. Interaktives deutschsprachiges Web-HMI
4. Funktionierende RLT-Simulation über MQTT
5. Grafana-Dashboards und InfluxDB-Aufzeichnung
6. Versionierte Tag-Liste und MQTT-Nachrichtenschemas
7. API-Dokumentation
8. Dokumentierte Schnittstelle zur späteren CODESYS-Anbindung
9. Installations- und Bedienungsanleitung
10. Testprotokoll mit tatsächlichen Ergebnissen
11. Liste offener technischer Klärungen und Grenzen der Simulation

Liefere eine ausführbare Gesamtanwendung, nicht nur eine Konzeptbeschreibung oder statische Oberfläche.

Starte keine reale PLC-Kommunikation und führe kein Edge-Deployment aus. Diese Schritte benötigen einen separaten Auftrag.