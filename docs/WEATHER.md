# Wettervorhersage – Version 1.1.0

## Betrieb

HMI: http://localhost:8080. Unter dem Anlagenbild als Operator oder Administrator Stadt/Land eingeben, suchen, eindeutigen Treffer auswählen und Standort speichern. Viewer besitzen Leserechte. Kein Standardstandort ist vorgegeben. Sieben lokale Kalendertage einschließlich heute werden angezeigt. Erstabruf erfolgt normalerweise innerhalb von zehn Sekunden; bei Netzproblemen kann er länger dauern.

Die unabhängige Wetterkomponente läuft zunächst auf dem PC und später auf dem EdgePC. Keine Änderung des PFC300-Programms, keine reale SPS-Kommunikation und keine Wetterwerte in der Regelung. Bestehender Sollwert blieb während der Tests bei 23 °C.

## Konfiguration und Netzwerk

Optionale .env-Werte: WEATHER_INTERVAL_SECONDS=1800 (Minimum 300), WEATHER_RETENTION_DAYS=365 (Minimum 1), WEATHER_API_KEY, WEATHER_HTTPS_PROXY. Nach Änderung Wettercontainer neu erstellen. Ohne Schlüssel wird der nichtkommerzielle öffentliche Open-Meteo-Endpunkt verwendet. Kommerzieller Betrieb benötigt eine geeignete Lizenz und einen Kundenschlüssel; es wurde kein kostenpflichtiger Dienst gebucht.

Nur weather hängt zusätzlich am Netz weather_outbound. Backend und Simulation bleiben im internen plant-Netz. Keine Hostports des Wetterdienstes; Browser spricht mit dem angemeldeten Backend. Fest verwendete externe HTTPS-Endpunkte: geocoding-api.open-meteo.com und api.open-meteo.com; bei Schlüssel customer-geocoding-api.open-meteo.com und customer-api.open-meteo.com. DNS und ausgehendes TCP 443 erforderlich, Unternehmensproxy optional. Zeit des Hosts per bestehender Betriebssystem-Zeitsynchronisation aktuell halten. Keine eingehenden Internetports oder Router-Portweiterleitung erforderlich.

Docker-Netztrennung ist keine Firewall-Domainfreigabe: strikte Zielbeschränkungen sind bei der EdgePC-Migration zusätzlich in Firewall/Proxy einzurichten. Das Image selbst braucht zum ersten Download Internetzugriff; anschließend reicht periodische Erreichbarkeit der Wetter-API. Offline funktioniert die vorhandene RLT-Regelung weiter.

## Daten und Fehler

Wetterdienst hält Standort, Suchtreffer und unveränderliche Vorhersageversionen in weather_data/weather.sqlite (WAL). Standortauswahl nur aus kürzlich serverseitig gefundenen Treffern. Änderungen werden im Backend-Audit erfasst. Orte sind nach ID getrennt; Standortwechsel löscht keine alten Prognosen.

Vorhersage: stündliche temperature_2m und relative_humidity_2m, Best-Match-Modellwahl des Anbieters. Keine individuelle Modell- oder Veröffentlichungszeit erfunden. UTC-Zeitpunkte werden als Unixzeit übernommen, Anzeige nach Standortzeitzone. Temperaturminimum/-maximum und arithmetische mittlere relative Feuchte aus verfügbaren Stundenwerten; gültige/gesamte Stunden pro Tag sichtbar. Fehlende/ungültige Werte bleiben leer, Kurven zeigen Lücken. Relative Feuchte ist kein absoluter Wassergehalt.

Abruf: 12 Sekunden Timeout, höchstens drei Versuche; bei HTTP 429 keine unmittelbaren Wiederholungen. Nach Fehler frühestens nach fünf Minuten erneuter Versuch. Letzte erfolgreiche Prognose bleibt erhalten; Fehler und Alter werden angezeigt. Veraltet nach dem größeren Wert aus doppeltem Abrufintervall und einer Stunde. Bei Verlust der HMI-Verbindung zeigt die Wetteranzeige Offline und behält die zuletzt gelesenen Daten.

Eigener Influx-Bucket weather mit Standardaufbewahrung 365 Tage, getrennt von rlt. Die Frist wird bei erstmaliger Bucket-Erstellung gesetzt; Änderungen eines bereits vorhandenen Buckets sind ausdrücklich über die Influx-Verwaltung vorzunehmen. SQLite löscht erfolgreich archivierte Versionen nach der konfigurierten Frist; nicht archivierte Versionen bleiben zur späteren Nachlieferung erhalten und brauchen Speicherüberwachung bei langem Archivierungsausfall.

Measurement weather_forecast: Tags location_id, provider, version; Zeitachse = Prognosegültigkeit. Felder temperature, humidity, valid, acquired_at, latitude, longitude. UUID je Abruf verhindert Überschreiben von Vorhersagerevisionen. Influx-Schreibbestätigung wird angezeigt; bei Fehler bleiben die lokalen Versionen zur Wiederholung erhalten.

GET /api/weather/history?location_id=...&as_of=... liefert die zuletzt bis zum angegebenen Zeitpunkt erworbene Version, innerhalb der lokalen Aufbewahrungsfrist. Für KI jeweils acquired_at <= Entscheidungszeit prüfen und anschließend die benötigte Prognosegültigkeit auswählen. Historische Standort- und Zeitzuordnung nicht mit späterem Standort vermischen. Datensätze nicht als Sensormessung behandeln.

48 Abrufe/Tag × ungefähr 168 Stunden = ungefähr 8.064 Prognosepunkte pro Tag und Standort, circa 2,94 Millionen/Jahr. Sommerzeit kann die Stundenzahl verändern. SQLite-Roh-JSON grob 1–2 GB/Jahr; Influx-Speicherbedarf ist zusätzlich abhängig von Kompression, Index und Versions-Tags. Dies ist eine Planungsschätzung, keine gemessene Jahreslast. Freien Speicher überwachen; Frist nach Bedarf wählen.

Backup/Restore berücksichtigt weather_data. Alte Sicherungen ohne weather_data benötigen eine Wiederherstellung als alte Version oder eine bewusste separate Migration; nicht automatisch mit neuem Wetterzustand vermischen. PFC300 benötigt für diese Erweiterung keinen Internetzugang.

## Nachweise

34 Python-Tests bestanden einschließlich Rechte, Audit, Teilwerte, UTC/Sommerzeit, Versionsabfrage, gecachter Prognose bei Ausfall und Limitantwort. Netzwerkfehler und HTTP 429 sind simulierte Tests, keine absichtlich herbeigeführten Anbieterausfälle.

Echter Open-Meteo-Test mit vorübergehendem Berlin-Standort: 7 lokale Tage, 168 gültige Stunden, Influx-Schreibbestätigung und Rücklesen der 168 Werte je Feld, historische Versionsabfrage, Audit, unveränderter Regelungssollwert. Ergebnisse: weather-live-results.json. Teststandort wird anschließend zurückgesetzt; Testprognose bleibt als historische Testdaten erhalten und ist für spätere Trainingsdaten auszuschließen.

20 bestehende Browserchecks und 4 Wetter-Browserchecks bestanden. Desktop/Tablet/Smartphone ohne Seitenüberlauf; Wetterkarten und Stundenansicht sichtbar; Viewer ohne Standortänderung. Screenshots weather-desktop.png, weather-tablet.png, weather-phone.png zeigen den temporären Teststandort.

## Quellen

- https://open-meteo.com/en/docs
- https://open-meteo.com/en/docs/geocoding-api
- https://open-meteo.com/en/pricing
- https://open-meteo.com/en/terms

## Migration auf EdgePC

Docker-/CPU-Kompatibilität prüfen, Images dort bauen oder passende Architektur bereitstellen. .env sicher übertragen, lokale HMI-Adresse/PUBLIC_ORIGIN anpassen, persistente Volumes inklusive weather_data und Influx sichern/übertragen. DNS, Zeitsynchronisation, HTTPS-Ziele und Proxy live prüfen. Kundenstandort auswählen und Abruf/Archiv/Rücklesen erneut nachweisen. Keine Übertragung oder Aktivierung auf einem realen EdgePC in dieser Lieferung erfolgt.

Persistenz des Standorts, der Vorhersage und des Archivierungsstatus nach Wettercontainer-Neustart ebenfalls live bestätigt. Testversion: 63d1f40c-7a8b-43b9-b183-474012e48448; nicht für spätere Trainingsdaten verwenden.
