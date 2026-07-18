# Haarpflege-App

Persönliche Haarpflege-App für Nicole — Routinen, INCI-geprüfte Produkte und Frisuren, zugeschnitten auf feines welliges Haar (2a–2b, hohe Dichte, aufgehellte Längen).

**Live:** https://nicolehahn2890.github.io/Hair/

## Design

„Journal de Beauté" — editorialer Papier-Look statt typischer App-Optik: Ecru-Grund, feine Linien, Cormorant-Garamond-Serifen mit Nº-Nummerierung, Stempel-Labels, Karla für Fließtext. Navigation über gezeichnete Linien-Icons (Tropfen, Flakon, Kamm).

## Aufbau — 3 Tabs

| Tab | Unterreiter | Inhalt |
|---|---|---|
| **Routinen** | Waschtag · Zwischendurch · Wissen | 6 abhakbare Guides (Wäsche schnell/intensiv, Styling Wellen/Glatt, Refresh, Klärungs-Reset) + Haarprofil, Silikon/Protein-Wissen, Dejan-Garz-Check |
| **Produkte** | — (eine Liste) | Alle 63 Produkte mit INCI-Check und Original-Packshot: eigene Produkte, Nachkauf-Empfehlungen, Dejans Post vom 17. Juli 2026 und der Rossmann-Regal-Check (Spanien). Nach Kategorie gruppiert, pro Kategorie gerankt — Nº 1 = beste Wahl, absteigend |
| **Frisuren** | Schlafen · Alltag · Sport · Anlass | 30 Looks mit Anleitung |

Kein fester Waschtag-Kalender — die Guides sind bewusst flexibel.

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Die komplette App (Standalone-HTML, kein Build nötig) |
| `apple-touch-icon.png`, `favicon-32.png` | App-Icon (drei Haarwellen mit Gold-Sparkles, gerahmt) |
| `img/` | 63 Produktfotos (Original-Packshots, max. 300px) |
| `scripts/fetch_packshots.py` + `.github/workflows/fetch-packshots.yml` | Holt Produktfotos über GitHub Actions (manuell startbar) |
| `hair-app.skill` | Skill-Paket für Claude (Design-System, Datenstrukturen, Regeln) |
| `Haarberatung_Nicole_v4.pdf` | Ursprüngliche Beratung (Mai 2026) — inhaltlich durch die App abgelöst |
| `Haarberatung_Mama_v2.pdf` | Beratung für Mama |

## Aktualisieren

`index.html` auf GitHub bearbeiten (Stift-Symbol), Inhalt ersetzen, committen — nach ~2 Minuten ist die Änderung live.

Auf dem iPhone: Safari → Teilen → „Zum Home-Bildschirm".

## Hinweis zu den Produktbewertungen

Alle INCI-Bewertungen wurden im Juli 2026 recherchiert (Quellen u.a. INCIdecoder, INCI Beauty, Hautschutzengel). Hersteller ändern Rezepturen — im Zweifel zählt immer das Etikett auf der Packung. Der localStorage-Schlüssel `haarpflege_v1` speichert die Tages-Häkchen lokal auf dem Gerät.
