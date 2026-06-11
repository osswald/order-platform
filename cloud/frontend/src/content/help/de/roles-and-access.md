Vendiqo unterscheidet vier Rollen. Ihre Sichtbarkeit in der Navigation hängt von Ihrer Rolle ab.

## Plattform-Admin (Superuser)

Vendiqo-Betreiber mit Zugriff auf alle Verleiher.

- Verleiher anlegen und verwalten (**Verleiher**)
- **Aktiven Verleiher** in der Seitenleiste wählen — API-Anfragen senden den Header `X-Hire-Company-Id`
- Voller Zugriff innerhalb des gewählten Verleihers

## Verleiher-Admin

Mitarbeiter eines Verleihers mit Verwaltungsrechten auf Mandantenebene.

- Eigene Verleiher-Stammdaten bearbeiten (**Verleiher-Einstellungen**)
- Organisationen anlegen und verwalten
- Geräte und Benutzer im gesamten Verleiher verwalten
- Ausleihen planen, Events und Katalog pflegen
- Stripe-Onboarding für Organisationen

## Organisations-Admin

Administrator einer oder mehrerer Kundenorganisationen.

- Zugewiesene Organisationen bearbeiten (kein Anlegen/Löschen)
- Benutzer nur innerhalb der eigenen Organisation(en) verwalten
- Events, Artikel, Kellner usw. in den zugewiesenen Organisationen

## Mitglied

Benutzer einer Kundenorganisation.

- Zugewiesene Organisationen und deren Events, Artikel, Kellner
- Geräteausleihen einsehen (lesend)
- Kein Zugriff auf Organisations-Stammdaten oder Benutzerverwaltung

## Navigation

| Bereich | Plattform-Admin | Verleiher-Admin | Organisations-Admin | Mitglied |
|---------|-----------------|-----------------|---------------------|----------|
| Dashboard, Events, Katalog | ja | ja | ja | ja (eigene Orgs) |
| Verleiher (Liste) | ja | nein | nein | nein |
| Verleiher-Einstellungen | ja | ja | nein | nein |
| Organisationen | ja | ja | ja (bearbeiten) | nein |
| Geräte, Benutzer | ja | ja | Benutzer (eigene Orgs) | nein |
| Einstellungen (Passwort) | ja | ja | ja | ja |

Bei fehlendem Zugriff leitet die Anwendung auf eine Hinweisseite um.
