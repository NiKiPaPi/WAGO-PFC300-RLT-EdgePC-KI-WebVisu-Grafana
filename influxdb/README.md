# Historie

InfluxDB 2.7.11, Organisation/Bucket `rlt`, Measurement `rlt` für numerische Werte (Float) und `rlt_state` für Zustände (String), Tags `tag` und `quality`, Field `value`. Getrennte Measurements vermeiden Field-Type-Konflikte. Zeitstempel der MQTT-Messung in UTC Nanosekunden. Abtastrate standardmäßig 2 s, über .env und Administratoroberfläche konfigurierbar. Aufbewahrung initial 30 Tage; `INFLUX_RETENTION` wirkt bei Erstinitialisierung. Bestehende Buckets über die Influx-Verwaltung anpassen.

Nur frische, bestätigte Telemetrie wird gespeichert. Fehlende/veraltete Messungen erzeugen Lücken; kein Vorwärtsfüllen. Bei Influx-Ausfall werden Messungen nicht nachträglich erfunden oder gepuffert. API meldet die Aufzeichnung als gestört. Grafana bekommt das Token ausschließlich serverseitig im Datenquellen-Provisioning; Browser erhalten kein Datenbanktoken.

Das Initial-Token ist für die lokale isolierte Demo ein Admin-Token. Vor späterer Bereitstellung separate minimal berechtigte Schreib-/Lesetokens, TLS und Zugangskonzept klären.
