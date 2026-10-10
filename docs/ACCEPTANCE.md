# Abnahmebedingungen

Alle folgenden Live-Prüfungen setzen eine gestartete Compose-Anwendung voraus. Durchfall: Erfolg ohne passende Command-ID, Änderung eines echten Geräts, unberechtigter Schreibzugriff, unbekannte/ungültige Werte akzeptiert, Istwert direkt auf Sollwert gesetzt, aufgefüllte Historienlücken, Zugangsdaten im Browser/Quellcode.

| ID | Bedingung / Aktion | Erwartung / Durchfallkriterium | Status |
|---|---|---|---|
| E01 | Compose auf Docker Desktop, frische Volumes | Alle Healthchecks grün, HMI/API/Simulation/Historie bereit | Docker-Start bestanden, 6 gesunde Services; broker-init Exitcode 0 |
| E02 | Operator, Auto, Sollwert 20 → 22 °C | Command-ID: Empfang/Annahme/Logikergebnis; akzeptiert 22; Ist dynamisch | Tatsächliche Compose-Kette bestanden; e2e-results.json |
| E03 | Audit E02 | Benutzer, UTC, Ziel, Alt/Neu, ID, Ergebnis vorhanden | In realem Backend bestanden |
| E04 | Grafana Ist/Soll/Außenluft gemeinsam | Drei Kurven, Einheiten, 1h/6h/24h/7d, Lücken sichtbar | Drei reale Kurven/Einheiten/Lücken visuell geprüft; Zeitbereiche konfiguriert, längere Laufhistorie noch nicht vorhanden |
| E05 | Viewer versucht POST command | HTTP 403, kein MQTT publish | Automatisiert geprüft |
| E06 | Sollwert 31 °C oder String/NaN | Ablehnung ohne Ausführung | Automatisiert geprüft |
| E07 | Hand, fault.inject=true, Fanstart | Rejected, Verriegelung wirkt; Quittierung entriegelt nicht | Automatisiert geprüft |
| E08 | Gleiche Command-ID wiederholen/neustarten | Einmalige Verarbeitung, gleiches Resultat | Automatisiert geprüft |
| E09 | Ergebnis verspätet / Prozessneustart | Timeout/Ergebnis unbekannt, nie Erfolg und kein Replay | Automatisiert und mit realem pausiertem Gateway geprüft |
| E10 | MQTT/Simulation unterbrechen | Spätestens stale_seconds Daten ungültig, Bedienung gesperrt | Tatsächlich pausierte Simulation: API stale/Timeout; frühere UI-Warnprüfung bestanden; Broker-Abschaltung nicht separat ausgeführt |
| E11 | Wiederverbindung | Frischer Snapshot, kein automatisches Wiederholen alter Befehle | Resume: Daten frisch, abgelaufener 24-°C-Befehl nicht ausgeführt |
| E12 | Fehler aktivieren, quittieren, zurücksetzen | Aktiv/quittiert/zurückgekehrt separat | Automatisiert und in realer Compose-Kette bestanden |
| E13 | Influx/Grafana Container-Neustart | Vorherige Historie weiterhin abfragbar | Bestanden: identischer festgelegter UTC-Bereich vor/nach Neustart |
| E14 | Desktop 1440×1000, Tablet 820×1180, Smartphone 390×844 | Login, Navigation, Component-Dialog, Bestätigung verwendbar; SVG darf horizontal scrollen | Reales Docker-HMI/Grafana in Headless Edge geprüft; Viewports, keine physischen LAN-Geräte |
| E15 | settings/user als Operator, fremder Origin | HTTP 403, keine Änderung | Automatisiert geprüft |
| E16 | Backup/Restore | Benutzer/Audit/Sollwerte/Historie erhalten | 6 Prüfungen bestanden: 7 Archive und separate Recovery-Volumes; Quelle nicht überschrieben |

`scripts/e2e.py` prüft den Kernablauf nach realem Compose-Start und speichert `docs/e2e-results.json`. Es ersetzt die manuelle Prüfung der Grafana-Achsenzuordnung und Bedienbarkeit nicht. Für Historienpersistenz vor/nach Neustart denselben UTC-Bereich abfragen, Datenpunktanzahl vergleichen und Ergebnis dokumentieren. Ergebnisse nur nach tatsächlicher Durchführung auf „bestanden“ ändern.
