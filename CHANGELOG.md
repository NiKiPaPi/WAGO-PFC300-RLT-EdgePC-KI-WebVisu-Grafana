# Änderungsprotokoll

## 1.1.0 – 2026-10-10

### Wettervorhersage und Anlagenstandort

- Deutschsprachiges Wetterpanel unter dem RLT-WAGO-PFC300-Anlagenbild: sieben lokale Kalendertage einschließlich heute, minimale/maximale Temperatur und mittlere relative Feuchte.
- Stündliche Temperatur- und Feuchtigkeitskurven mit getrennten Einheiten sowie prüfbare Stundenwerte und Qualitätskennzeichnung.
- Stadt-/Landsuche mit Auswahl eindeutiger Orte einschließlich Region, Land, Koordinaten und Zeitzone. Kein fest vorgegebener Anlagenstandort.
- Operator und Administrator dürfen den Standort speichern; Viewer besitzt Leserechte. Standortänderungen werden protokolliert und bleiben nach Neustart erhalten.
- Quellenangabe, letzte erfolgreiche Aktualisierung, Offline-/Veraltet-/Teilwerte-Anzeige und Archivierungsstatus. Responsive Anzeige für Desktop, Tablet und Smartphone.

### Dienste, Netzwerk und Speicherung

- Eigenständiger Open-Meteo-Wetterdienst im Docker-Stack; für spätere Migration auf den EdgePC vorbereitet. Wetterdienst ohne SPS-/MQTT-Steuerausgaben.
- Separates ausgehendes Wetter-Netz; Backend und Simulation bleiben im internen plant-Netz. Keine neuen Hostports, öffentlichen Eingänge oder Router-Portweiterleitungen.
- Standardabruf alle 30 Minuten, konfigurierbare Intervalle, begrenzte Wiederholungen, API-Timeout, Behandlung von Aufruflimits, optionaler Unternehmensproxy und serverseitige API-Schlüsselverwaltung.
- Unterstützung öffentlicher nichtkommerzieller und kommerzieller Kunden-Endpunkte. Kein kostenpflichtiger Dienst gebucht; kommerzieller Einsatz benötigt passende Lizenz.
- SQLite-Cache und eigener InfluxDB-Bucket weather. Unveränderliche Versionen je Abruf mit Standort, UTC-Abrufzeit, Prognosegültigkeit, Temperatur, Feuchte und Datenvalidität.
- Historische Abfrage der zum Entscheidungszeitpunkt bereits bekannten Vorhersage als Vorbereitung für spätere KI-Datensätze. Prognoseversionen überschreiben sich nicht.
- Konfigurierbare Aufbewahrung, lokale Nachlieferung bei Archivierungsfehlern und Aufnahme des weather_data-Volumes in Backup-/Restore-Skripte.
- Zustandsprüfung auf sieben laufende Dienste aktualisiert. Details zu Netzwerk, Speicherschätzung, Wiederherstellung und EdgePC-Migration in docs/WEATHER.md.

### Prüfung

- 34 Python-Tests bestanden: vorhandene Regelungs-/API-Tests plus Wetterrechte, Audit, Teilwerte, UTC/Sommerzeit, Vorhersageversionen, Cache, Timeout, Limitantwort und neue Bucket-Erstellung.
- 20 bestehende Browserchecks und 4 Wetter-Browserchecks bestanden. Screenshots für Desktop, Tablet und Smartphone enthalten.
- Echter Open-Meteo-Test mit Berlin: sieben Tage und 168 gültige Stunden; Influx-Schreibbestätigung und Rücklesen, historische Versionsabfrage und Standortpersistenz nach Neustart geprüft.
- RLT-Sollwert während der Tests unverändert bei 23 °C. Alle sieben Dienste zuletzt healthy.
- Vorübergehenden Teststandort zurückgesetzt. Historische Testversion in docs/WEATHER.md gekennzeichnet; für spätere Trainingsdaten ausschließen.

### Grenzen dieses Releases

- Ausschließlich PC-/Docker-Simulation: keine Migration auf einen realen EdgePC, kein SPS-Download und keine Änderung des PFC300-Programms.
- Wetterwerte beeinflussen weder Sollwerte noch bestehende RLT-Regelung. KI-Regelung bleibt eine spätere Entwicklungsphase.
- Netzfehler und API-Limits wurden simuliert; der echte Abruf und die Datenbankprüfung sind getrennt dokumentiert.
- Ältere Backups ohne Wettervolume benötigen eine bewusste Versions-/Migrationsentscheidung. Bestehende Bucket-Aufbewahrung ändert sich nicht automatisch durch .env-Anpassung.

## 1.0.2 – vorheriger GitHub-Stand

Anlagenbild mit Außenluft unten links, Fortluft oben links und Luftarten-Farbkennzeichnung. Bestehende Wärmerückgewinnung erhalten; Anlagenbild in RLT-WAGO-PFC300-Anlagenbild umbenannt. Frontend und Validierungsnachweise aktualisiert.
