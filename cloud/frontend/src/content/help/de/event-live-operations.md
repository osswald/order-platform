Sobald ein Event den Status **Test**, **Live** oder **Abgeschlossen** hat, erscheinen zusätzliche Betriebs-Tabs in der Event-Konfiguration. Diese dienen der Auswertung — Änderungen erfolgen weiterhin in den Konfigurationsabschnitten.

## Wann Tabs sichtbar sind

| Tab | Voraussetzung |
|-----|---------------|
| Umsatz, Sammelrechnungen | Status ≠ Konfiguration |
| Transaktionen | Status Test, Live oder Abgeschlossen |
| Schichten | Wie Transaktionen + Kassen/Schichtabschluss aktiviert |
| Buchhaltung | Wie Umsatz + Konten in der Organisation aktiviert |

Im Status **Konfiguration** sind nur Setup-Abschnitte (Stationen, Layouts usw.) verfügbar.

## Umsatz

Übersicht über den Verkaufsstand:

- Anzahl Bestellungen, Positionswert, bezahlt, offen
- Aufschlüsselung nach Kellner und Station
- **Aktualisieren** lädt die neuesten Daten vom Server

## Sammelrechnungen

Liste und Status von Sammelrechnungen für das Event. Nützlich für Abrechnungen mit Festkunden oder internen Konten.

## Transaktionen

Chronologisches Protokoll aller Zahlungen und relevanten Vorgänge. Hilft bei der Nachverfolgung einzelner Zahlungen oder Stornos.

## Schichten (Kassensitzungen)

Bei aktivierten Kassen und Schichtabschlüssen:

- Offene und abgeschlossene Kassensitzungen
- Anfangsbestand, Umsatz und Differenzen pro Schicht

## Buchhaltung

Wenn die Organisation Konten aktiviert hat:

- Zusammenfassung und Detailbuchungen
- Soll/Haben, Steuercodes, Netto/MWST/Brutto
- Bezug zu Sammelrechnungen wo vorhanden

## Hinweise

- Betriebs-Tabs sind **read-only** — Konfiguration bleibt in den Setup-Abschnitten
- Daten kommen vom Pi-Sync; bei Verzögerungen **Aktualisieren** nutzen
- Für Event-Setup siehe **Event einrichten**
