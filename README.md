# Bella Vista Preiswächter (Cloud)

Sucht 3× täglich (7, 15 und 20 Uhr Wiener Zeit) den besten Preis für das Bella Vista Resort
in Hurghada ab Graz – als Pauschalreise (CHECK24) und als Flug + Hotel einzeln
(Google Flüge + Google Hotels). Läuft kostenlos auf GitHub, auch wenn kein Computer an ist.

- **Ergebnis-Seite:** `https://<benutzername>.github.io/<repo-name>/`
- **Preisalarm:** Nachricht aufs Handy über die kostenlose App **ntfy**

## Einstellungen ändern

Datei **`config.json`** auf GitHub öffnen → Stift-Symbol (Bearbeiten) → ändern → „Commit changes“.

```json
{
  "zeitraum": { "von": "2026-11-26", "bis": "2027-06-30" },
  "alarm": { "woche": 760, "zehn": 1050 }
}
```

- `zeitraum.von` / `zeitraum.bis`: frühester Abflug, späteste Rückkehr (Jahr-Monat-Tag)
- `alarm.woche`: Nachricht, wenn 1 Woche (6–7 Nächte) unter diesem Preis liegt
- `alarm.zehn`: Nachricht, wenn 10 Tage (8–9 Nächte) unter diesem Preis liegen
- Alarm ausschalten: Zahl durch `null` ersetzen

## Sofort suchen

Reiter **Actions** → links **Preissuche** → rechts **Run workflow** → grüner Knopf **Run workflow**.
Nach ca. 5 Minuten steht das Ergebnis auf der Seite.

## Handy-Nachricht (ntfy)

1. App **ntfy** installieren (Android: Play Store, iPhone: App Store).
2. In der App auf **+** tippen und als Thema (Topic) den geheimen Namen eintragen,
   der in GitHub unter *Settings → Secrets and variables → Actions* als `NTFY_TOPIC` hinterlegt ist.

## Gut zu wissen

- GitHub startet geplante Läufe manchmal 10–30 Minuten später als angegeben.
- Hat ein Repository 60 Tage lang keine Änderung, pausiert GitHub die geplanten Läufe.
  Weil jede Suche das Ergebnis speichert, passiert das hier nicht.
- Wenn CHECK24 oder Google Abfragen aus dem GitHub-Rechenzentrum sperren oder ihre Seiten
  umbauen, schlägt der Lauf fehl (rotes Kreuz unter *Actions*). GitHub schickt dann eine E-Mail.
