Raspberry-Pi-Server verbinden sich über ein Pairing mit der Cloud. So synchronisieren Events, Artikel und Bestellungen.

## Voraussetzungen

1. Unter **Geräte** ein Gerät vom Typ **Server** anlegen
2. Im Gerätedetail einen **Pairing-Code** erzeugen
3. Pi mit Netzwerk starten und die lokale Setup-Seite öffnen (z. B. `http://192.168.192.10`)

## Pairing durchführen

1. Pairing-Code auf der Pi-Setup-Seite eingeben
2. Der Pi ruft die Cloud-API auf und erhält Zugangsdaten
3. Nach erfolgreicher Kopplung lädt der Pi Event-Bundles und synchronisiert Bestellungen

Der **Edge-Secret** wird nur einmal bei der Kopplung angezeigt und auf dem Pi gespeichert.

## Mehrere SD-Karten

Ein Server-Gerät kann mehrere gekoppelte SD-Karten haben (Haupt- und Backup-Karten). Jede Karte erhält eigene Zugangsdaten und kann einzeln widerrufen werden.

**Wichtig:** Nur eine SD-Karte desselben Servers sollte gleichzeitig eingeschaltet sein.

## Backup-Karte nutzen

Fällt die aktive SD-Karte aus, booten Sie eine bereits gekoppelte Backup-Karte. Der Pi synchronisiert weiter als dasselbe Server-Gerät.

## Pairing aufheben

Auf dem Pi ist ein Entkoppeln nur mit dem konfigurierten `unpair_secret` möglich. In der Cloud können einzelne SD-Karten im Gerätedetail widerrufen werden.
