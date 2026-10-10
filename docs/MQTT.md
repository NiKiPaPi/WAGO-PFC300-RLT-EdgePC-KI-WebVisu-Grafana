# MQTT-Vertrag 1.0

| Topic unter rlt/simulation/v1 | Publisher | QoS | Retain |
|---|---|---|---|
| commands | Backend | 0 | nein |
| results | Simulation | 1 | nein |
| telemetry | Simulation | 1 | nein |
| alarms | Simulation | 1 | nein |
| status | Simulation | 1 | ja (inklusive Last Will offline) |

Befehle verwenden bewusst QoS 0: keine Paho-QoS-1-Wiederholung alter unbestätigter Befehle nach Reconnect. Anwendungsbestätigungen sind maßgeblich. Verlust führt nach 10 Sekunden zum Timeout, nie zum Erfolg; Benutzer prüft Istzustand und sendet ggf. eine neue bewusste Änderung. Backend hält keine Offline-Queue und sendet nach Neustart keine alten Journal-Einträge. Beide Clients verwenden Clean Session. Simulation lehnt retained Befehle ab; UTC-Ablauf wird vor jeder neuen Ausführung geprüft.

`received` bedeutet Eingang, `accepted` bedeutet validiert, `executed` bedeutet Sollwert-/Logiktransaktion übernommen. Aktuatorbewegung und thermischer Zielzustand folgen später über Rückmeldung. `rejected` enthält Grund. Jeder Zustand bleibt per Command-ID im Audit nachvollziehbar. UI kann bei schneller Verarbeitung direkt das Endergebnis sehen.

Simulation speichert Ergebnis, akzeptierte Werte und Anforderungen atomar mit der Command-ID im persistenten Journal. Duplikate liefern dasselbe Ergebnis ohne neue Ausführung, auch nach Neustart. Das Journal wächst in dieser lokalen Demo; eine produktive Archivierungsstrategie ist offen. Gleichzeitige Zugriffe auf dasselbe Tag: Backend sperrt laufenden Befehl, anschließend Compare-and-set anhand `expected`; Simulation prüft Ausgangswert erneut. Übergreifende Konflikte (Heizen/Kühlen, Verriegelung) prüft das Modell.

WebSocket `/api/ws`: HttpOnly-Sitzungscookie, Origin-Prüfung, vollständiger initialer Zustand, danach aktualisierter Zustand jede Sekunde. Browser reconnect nach 2 Sekunden; kein Befehlsreplay. Jede Aktualisierung enthält Zustand, Datenalter, Qualität und Befehlsresultate. Telemetrie ist nur bei `good`, aktuellem Zeitstempel und beiden Verbindungen frisch. Uhrensynchronisation ist Voraussetzung. Status-Retain allein beweist keine frischen Messwerte.

Broker intern, ohne Host-Port, Passwortdatei und getrennte ACL für Backend/Simulation. Benutzeridentität kommt aus der Backend-Sitzung, nicht vom Browser. Die feste ACL erwartet die Namen `api` und `simulation`; diese Benutzernamen in .env nicht verändern, ohne ACL anzupassen. Kein realer Namensraum ist freigegeben.
