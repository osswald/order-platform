Diese Datenschutzerklärung beschreibt, wie die **Vendiqo GmbH** («wir», «uns») Personendaten bearbeitet, wenn Sie die **Vendiqo Waiter** Android-App, die Vendiqo Cloud-Verwaltung unter [admin.vendiqo.ch](https://admin.vendiqo.ch) oder verbundene Dienste nutzen.

## 1. Verantwortliche Stelle

**Vendiqo GmbH**  
[Adresse]  
E-Mail: [Kontakt-E-Mail]

## 2. Geltungsbereich

Diese Erklärung gilt insbesondere für:

- die Android-App **Vendiqo Waiter** (`ch.vendiqo.app`)
- die Web-Verwaltung unter [admin.vendiqo.ch](https://admin.vendiqo.ch)
- die Cloud-API unter [api.vendiqo.ch](https://api.vendiqo.ch)
- die Kommunikation zwischen Android-Gerät, Vendiqo Raspberry Pi im lokalen Netzwerk und der Cloud

Betriebspersonal von Veranstaltern und Gastronomiebetrieben nutzt die App in der Regel im Auftrag ihres Arbeitgebers bzw. Veranstalters. Für betriebsinterne Bestell- und Zahlungsdaten kann zusätzlich der jeweilige Veranstalter datenschutzrechtlich verantwortlich sein.

## 3. Zweck der Bearbeitung

Wir bearbeiten Personendaten, um:

- Bestellungen und Zahlungen an Veranstaltungen zu erfassen und abzuwickeln
- Kellner- und Kassensysteme mit dem Vendiqo Pi zu verbinden
- bei aktivierter Cloud-Anbindung Daten zwischen Pi und Cloud zu synchronisieren
- Kartenzahlungen über Stripe Tap to Pay zu ermöglichen
- Belege auf Bluetooth-Druckern auszudrucken
- Benutzerkonten für die Cloud-Verwaltung bereitzustellen

## 4. Welche Daten wir bearbeiten

### 4.1 Android-App Vendiqo Waiter

| Datenkategorie | Beispiele | Wo gespeichert |
|---|---|---|
| Bestell- und Zahlungsdaten | Artikel, Mengen, Beträge, Zahlungsart, Zeitstempel | Vendiqo Pi; bei Cloud-Sync auch Cloud |
| Bedienperson / Kellner | Kellnercode, Bedienungszuordnung | Vendiqo Pi; bei Cloud-Sync auch Cloud |
| Bluetooth-Drucker | Name und Adresse des gekoppelten ESC/POS-Druckers | lokal auf dem Android-Gerät |
| Geräte- und Sitzungsdaten | UI-Einstellungen, lokale App-Zustände | lokal im WebView-Speicher des Geräts |
| Standortdaten | ungefährer/genauer Standort | nur bei Kartenzahlung über Stripe Tap to Pay, zur Erfüllung regulatorischer Anforderungen |
| Zahlungsdaten | Zahlungsstatus, Stripe-Referenzen | Stripe und Vendiqo Cloud/Pi; **keine Speicherung vollständiger Kartendaten durch Vendiqo** |

Die App kommuniziert im lokalen Netzwerk mit dem Vendiqo Pi (standardmässig unter `http://192.168.192.10`) und bei aktivierter Anbindung verschlüsselt mit der Cloud unter `https://api.vendiqo.ch`.

### 4.2 Cloud-Verwaltung admin.vendiqo.ch

| Datenkategorie | Beispiele |
|---|---|
| Kontodaten | E-Mail-Adresse, Passwort-Hash, Rolle, Zuordnung zu Organisation/Verleiher |
| Organisations- und Eventdaten | Veranstaltungen, Artikel, Kategorien, Bedienpersonen |
| Gerätedaten | Appliance-Registrierung, Pairing-Informationen |
| Zahlungs- und Abrechnungsdaten | Stripe Connect-Status, Zahlungsreferenzen |

### 4.3 Daten, die wir nicht erheben

Die Vendiqo Waiter App enthält **keine** Analyse-, Tracking- oder Werbe-SDKs (z. B. Firebase Analytics, Google Analytics, Sentry o. ä.).

## 5. Berechtigungen der Android-App

Die App kann folgende Geräteberechtigungen anfordern:

- **Internet** — Kommunikation mit Pi und Cloud
- **Bluetooth** — Verbindung zu gekoppelten Belegdruckern
- **Standort** — erforderlich für Stripe Tap to Pay; nicht für Profilbildung oder Standorttracking
- **NFC** — für kontaktlose Kartenzahlungen über Stripe Terminal

## 6. Rechtsgrundlagen

Je nach Kontext stützen wir die Bearbeitung auf:

- **Vertragserfüllung** — Bereitstellung des POS- und Verwaltungsdienstes
- **Berechtigtes Interesse** — sicherer Betrieb, Fehlerbehebung, Missbrauchsprävention
- **Gesetzliche Pflichten** — insbesondere im Zusammenhang mit Zahlungs- und Aufzeichnungspflichten
- **Einwilligung** — soweit für einzelne Funktionen erforderlich (z. B. Standortfreigabe durch das Betriebssystem)

## 7. Empfänger und Auftragsbearbeiter

Personendaten können weitergegeben werden an:

| Empfänger | Zweck |
|---|---|
| **Stripe Payments Europe Ltd.** | Kartenzahlungen, Stripe Connect, Tap to Pay |
| **Google / Google Play Services** | technische Abhängigkeit des Stripe Terminal SDK auf Android |
| **Hosting-Infrastruktur** | Betrieb von `vendiqo.ch`, `admin.vendiqo.ch` und `api.vendiqo.ch` |

Stripe verarbeitet Zahlungsdaten als eigenständiger Verantwortlicher bzw. Auftragsbearbeiter gemäss eigenen Datenschutzinformationen.

## 8. Übermittlung ins Ausland

Je nach Dienstleister kann eine Bearbeitung ausserhalb der Schweiz/des EWR stattfinden, insbesondere bei Stripe und Cloud-Infrastruktur. In solchen Fällen setzen wir geeignete Garantien ein, soweit gesetzlich erforderlich.

## 9. Speicherdauer

Wir speichern Personendaten nur so lange, wie es für die genannten Zwecke erforderlich ist:

- **Bestell- und Zahlungsdaten** — gemäss den Vorgaben des jeweiligen Veranstalters und gesetzlichen Aufbewahrungsfristen
- **Cloud-Kontodaten** — für die Dauer des Nutzungsverhältnisses und darüber hinaus gemäss gesetzlichen Pflichten
- **Lokale App-Daten auf dem Gerät** — bis zur Deinstallation der App, Zurücksetzung des Geräts oder manuellen Entfernung

## 10. Sicherheit

Wir treffen angemessene technische und organisatorische Massnahmen, um Personendaten zu schützen, darunter verschlüsselte Cloud-Kommunikation (HTTPS), Zugriffskontrollen in der Verwaltung und rollenbasierte Berechtigungen.

## 11. Ihre Rechte

Sie haben nach dem Schweizer Datenschutzgesetz (DSG) und — soweit anwendbar — der DSGVO insbesondere folgende Rechte:

- Auskunft über bearbeitete Personendaten
- Berichtigung unrichtiger Daten
- Löschung, soweit keine Aufbewahrungspflichten entgegenstehen
- Einschränkung der Bearbeitung
- Datenherausgabe in einem gängigen Format, soweit anwendbar
- Widerspruch gegen bestimmte Bearbeitungen
- Beschwerde bei einer Aufsichtsbehörde

Anfragen richten Sie bitte an [Kontakt-E-Mail]. Wir können zur Identitätsprüfung zusätzliche Informationen verlangen.

## 12. Kinder

Die Dienste richten sich an Unternehmen und deren Personal. Sie sind nicht für Kinder unter 16 Jahren bestimmt.

## 13. Änderungen

Wir können diese Datenschutzerklärung bei Bedarf anpassen. Die jeweils aktuelle Fassung ist unter [vendiqo.ch/datenschutz](https://www.vendiqo.ch/datenschutz) abrufbar. Bei wesentlichen Änderungen informieren wir angemessen, soweit erforderlich.
