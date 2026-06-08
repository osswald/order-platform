Kartenzahlungen laufen über **Stripe Connect**: Jede Organisation verbindet ein eigenes Stripe-Konto. Auszahlungen gehen an die Organisation, nicht an den Verleiher.

## Stripe-Konto verbinden

1. Öffnen Sie **Organisationen** und wählen Sie die Organisation
2. Im Abschnitt **Kartenzahlung (Stripe)** auf **Mit Stripe verbinden** klicken
3. Stripe-Onboarding im neuen Fenster abschliessen
4. Nach der Rückkehr **Status aktualisieren** — Zahlungen und Auszahlungen sollten aktiv sein

## Event aktivieren

In der Veranstaltungskonfiguration unter Stammdaten die Zahlungsart **Karte (Stripe Terminal)** aktivieren.

## Voraussetzungen am Verkauf

Kartenzahlung ist nur verfügbar, wenn:

- die Android-App mit Stripe Terminal Bridge genutzt wird
- der Pi eine Verbindung zur Cloud hat (Internet)
- das Event die Zahlungsart aktiviert hat

Ohne diese Bedingungen ist die Karte-Schaltfläche in der Kellner-App deaktiviert.

## Ablauf an der Kasse

1. Kellner wählt **Karte**
2. Pi erstellt über die Cloud einen Payment Intent
3. Android-App sammelt die Karte per Tap to Pay
4. Bestellung wird als bezahlt erfasst

## Probleme

- **Onboarding unvollständig** — Onboarding in Stripe fortsetzen und Status aktualisieren
- **Zahlungen ausstehend** — Stripe-Konto prüfen; Angaben und Verifizierung vervollständigen
- **Karte deaktiviert am Pi** — Cloud-Erreichbarkeit und Android-App prüfen
