Vendiqo unterscheidet drei Rollen. Ihre Sichtbarkeit in der Navigation hängt von Ihrer Rolle ab.

## Plattform-Admin

Vendiqo-Betreiber mit Zugriff auf alle Verleiher.

- Verleiher anlegen und verwalten (**Verleiher**)
- **Aktiven Verleiher** in der Seitenleiste wählen — API-Anfragen senden den Header `X-Hire-Company-Id`
- Voller Zugriff innerhalb des gewählten Verleihers

## Organisations-Admin

Mitarbeiter eines Verleihers mit Verwaltungsrechten.

- Organisationen, Geräte und Benutzer verwalten
- Ausleihen planen, Events und Katalog pflegen
- Stripe-Onboarding für Organisationen

## Mitglied

Benutzer einer Kundenorganisation.

- Zugewiesene Organisationen und deren Events, Artikel, Kellner
- Geräteausleihen einsehen (lesend)
- Kein Zugriff auf Benutzerverwaltung oder Verleiher-Einstellungen

## Navigation

| Bereich | Plattform-Admin | Org-Admin | Mitglied |
|---------|-----------------|-----------|----------|
| Dashboard, Events, Katalog | ja | ja | ja (eigene Orgs) |
| Verleiher | ja | nein | nein |
| Organisationen, Geräte, Benutzer | ja | ja | nein |
| Einstellungen (Passwort) | ja | ja | ja |

Bei fehlendem Zugriff leitet die Anwendung auf eine Hinweisseite um.
