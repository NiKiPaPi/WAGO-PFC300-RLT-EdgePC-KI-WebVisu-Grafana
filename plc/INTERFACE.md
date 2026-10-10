# Spätere CODESYS-Schnittstelle — deaktiviert

Kein ausführbares CODESYS-Projekt und keine WebVisu. RUN_MODE außerhalb `simulation` bricht beim Import ab. Es gibt keine PLC-IP, keine I/O-Adresse und keinen realen MQTT-Namensraum in aktiver Konfiguration.

Späterer Gateway muss die Verträge aus `/contracts` übernehmen: Befehls-ID, erwarteter Ausgangswert, Benutzeridentität des Backend, UTC-Erstellung/Ablauf, Version, Empfang/Annahme/Ablehnung/Logikergebnis. Istwert und Rückmeldung bleiben unabhängig. Realbetrieb benötigt einen getrennten Broker bzw. ACL und `rlt/real/v1`, nicht lediglich eine Änderung des Simulationspräfixes.

TBD – technische Klärung erforderlich: PFC300 Gerät/Firmware/CODESYS-Bibliotheken, Signalzuordnung, Messbereiche, reale Sollwertgrenzen, Brandschutz, Frostschutz, Motorschutz, unabhängige Schutzketten, Fail-safe-Zustände, Prioritäten lokaler Bedienung, Netzwerk/TLS, Uhrensynchronisation, PLC-seitige persistente Idempotenz und Wiederanfahrfreigabe. Ein gesonderter Auftrag und Abnahme sind erforderlich.
