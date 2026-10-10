# RLT-WAGO-PFC300-Anlagenbild — Änderung 1.0.2

Benutzerauftrag: Außenluft-Eintritt unten links, Fortluft-Austritt oben links; vorhandene einfache Wärmerückgewinnung beibehalten. Name des Anlagenbildes und Browser-Titel: `RLT-WAGO-PFC300-Anlagenbild`.

Obere Ebene: Abluft von rechts → Abluftfilter → Abluftventilator → bestehende WRG → Fortluftklappe → Fortluft links.

Untere Ebene: Außenluft links → Außenluftklappe → Filter → bestehende WRG → Heiz-/Kühlregister mit Ventilrückmeldungen → Zuluftventilator → Zuluft rechts.

Luftarten werden durch Text, Kürzel, Richtungspfeile und Farbe unterschieden. Die Farbkategorien folgen [DGUV Information 209-200, Tabelle 3.6.1 und Abbildung 3.6.1, gedruckte Seite 53](https://publikationen.dguv.de/widgets/pdf/download/article/3596), dort mit Bezug auf DIN EN 16798-3: Außenluft grün, Zuluft blau, Abluft gelb, Fortluft braun. Die gewählten RGB-Hexwerte sind Bildschirmfarben dieses Projekts, keine behaupteten normativen RGB-/RAL-Vorgaben. Die Farbwechsel liegen an der vorhandenen WRG; dadurch bleiben die beiden Luftwege getrennt erkennbar.

Normativer Bezug und Grenze: [DIN EN 12792:2004-01](https://www.dinmedia.de/de/norm/din-en-12792/66713775) behandelt Begriffe und grafische Symbole der Lüftung. [VDI 3814 Blatt 2.3](https://www.vdi.de/en/home/vdi-standards/details/vdi-3814-blatt-23-building-automation-and-control-systems-bacs-planning-concept-of-operation-and-user-interfaces) betrifft Bedienkonzepte/Benutzeroberflächen; [VDI 3814 Blatt 4.3](https://www.dinmedia.de/de/technische-regel/vdi-3814-blatt-4-3/343766851) beschreibt GA-Automationsschemen und zugehörige Arbeitsmittel. Öffentlich zugängliche Primärquellen wurden geprüft; die vollständigen lizenzpflichtigen Regeltexte liegen nicht vor. Diese Änderung ist eine schematische HMI-Darstellung in Anlehnung an die benannten Konventionen, kein vollständiges freigegebenes GA-Automationsschema oder Normkonformitätsnachweis. Die konkrete Lage der Ports folgt dem Benutzerauftrag, nicht einer behaupteten verpflichtenden Anordnung.

Umfang: Frontend-Geometrie, Farb-/Textlegende, Komponentenbeschriftung und Anlagenbildname. Vorhandene WRG-SVG unverändert und weiterhin genau einmal vorhanden. Datenvertrag, MQTT, Backend, Simulationsmodell und Schutzlogik bleiben auf dem bisherigen Stand. Der Frontend-Container verwendet Image `rlt-simulation-frontend:1.0.2`; andere Services werden nicht neu erstellt.

Versionssicherung: bisheriger Quellstand in `data/versions/anlagenbild-1.0.1` und vollständiges vorheriges ZIP 1.0.1 im release-Verzeichnis. Die Browserprüfung erfolgt mit `RLT_UI_READ_ONLY=true`: Anmeldung, Komponentenfenster, abbrechbarer Bestätigungsdialog, Viewports und Grafana. Es werden keine Sollwerte geändert.

Tatsächliche Prüfung am 10.10.2026: TypeScript/Produktionsbuild erfolgreich, Frontend-Deployment Exitcode 0, 20 Browserprüfungen bestanden. Screenshots für 1440×1000, 820×1180 und 390×844 visuell geprüft; keine Seitenüberläufe, kleinere Viewports mit horizontal verschiebbarem SVG und Hinweis. Das vorhandene WRG-SVG wurde gegen die gesicherte Version verglichen: identisch und genau einmal vorhanden. Aktueller In-app-Browser wurde neu geladen; neuer Browser-Titel/Anlagenbildname, Luftartlegende und frische Messwerte sichtbar. Der vorhandene 23-°C-Sollwert blieb erhalten. Nachweis: docker-ui-results.json und docker-hmi-desktop/tablet/phone.png.
