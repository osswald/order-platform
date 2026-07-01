Organisationen sind die Kundenmandate Ihres Verleihers. Hier pflegen Sie Stammdaten, Buchhaltung, Geräteausleihen und Zahlungsanbindungen.

## Stammdaten

Unter **Organisationen** → Organisation auswählen → **Stammdaten**:

- Name, Adresse, PLZ, Ort
- **Land** und **Währung** (Pflichtfelder)
- **Benutzer** — welche Cloud-Benutzer Zugriff auf diese Organisation haben

Die Währung gilt für Artikelpreise und Event-Berichte dieser Organisation.

## Buchhaltung

Im Abschnitt **Buchhaltung** (nur sichtbar, wenn aktiviert):

- **MWST-pflichtig** — Schalter für umsatzsteuerliche Behandlung
- **Standard-Steuercode** — bei aktivierter MWST-Pflicht
- **Konten aktivieren** — Schalter für doppelte Buchführung
- **Kontenplan** — Konten anlegen, bearbeiten und Standardkonten für Kategorien setzen

Ist Buchhaltung aktiv, erscheint im laufenden Event ein Tab **Buchhaltung** mit Exportdaten.

## Geräte

Im Tab **Geräte** sehen und planen Sie Ausleihen für diese Organisation:

- Aktuelle und geplante Ausleihen
- Button **Geräte ausleihen** für neue Reservierungen (Verleiher-Admin)

Details zur lesenden Ansicht für Mitglieder: siehe **Geräteausleihen**.

## Kartenzahlung (Stripe)

Stripe Connect wird pro Organisation eingerichtet. Auszahlungen gehen an die Organisation.

Siehe Hilfeartikel **Stripe Connect** für Onboarding, Event-Aktivierung und Fehlerbehebung.

## Farbpalette (App Layout)

Im Tab **Farbpalette (App Layout)** definieren Sie wiederverwendbare Farben für Buttons in den Kellner-App-Layouts:

- Jede Farbe hat eine **Bezeichnung** (z. B. «Bar», «Food», «VIP») und einen **Farbwert** (Hex)
- Farben hinzufügen, bearbeiten oder entfernen und mit **Speichern** übernehmen
- Bis zu 32 Farben pro Organisation; doppelte Farbwerte sind nicht erlaubt

In der **Event-Konfiguration** unter **App-Layouts** erscheinen diese Farben beim Bearbeiten einer Layout-Zelle als Schnellauswahl — zusätzlich zum freien Farbwähler. Ist keine Farbpalette definiert, bleibt nur der manuelle Farbwähler sichtbar.

Die Zelle speichert weiterhin den Hex-Farbwert; die Palette dient nur der einheitlichen Auswahl in der Cloud.

## Wer darf was?

- **Verleiher-Admin** — Organisationen anlegen, löschen und vollständig verwalten
- **Organisations-Admin** — zugewiesene Organisationen bearbeiten (kein Anlegen/Löschen)
- **Mitglied** — kein Zugriff auf Organisations-Stammdaten

Rollen im Detail: **Rollen und Zugriff**.
