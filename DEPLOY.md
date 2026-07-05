# Die App online stellen (Render + IONOS-Domain)

Kurzanleitung, um `macherelektro.de` mit der App zu verbinden. In einfachen Schritten.

## Überblick
Die App braucht einen Server, der Python ausführt. Wir nutzen **Render** (einfach, HTTPS inklusive).
Danach zeigt die IONOS-Domain per **DNS** auf diesen Server.

---

## Schritt 1 – Code zu GitHub
Render holt sich den Code aus einem GitHub-Konto.
1. Kostenloses Konto anlegen auf https://github.com
2. Dort ein neues, leeres Repository anlegen, z. B. `elektrovergleich` (Sichtbarkeit: **Private** ist ok).
3. Den Code dieses Projekts hochladen (dabei hilft Claude Code – siehe unten).

## Schritt 2 – Web-Service bei Render
1. Kostenloses Konto anlegen auf https://render.com (mit GitHub anmelden ist am einfachsten).
2. **New → Web Service** → das GitHub-Repository auswählen.
3. Render erkennt Python automatisch. Falls nicht, diese Werte eintragen:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free (für den Anfang)
4. **Create Web Service** klicken. Nach ein paar Minuten läuft die App unter einer Adresse
   wie `https://elektrovergleich.onrender.com` – dort erst einmal testen.

## Schritt 3 – Domain macherelektro.de verbinden
1. In Render beim Service: **Settings → Custom Domains → Add** → `macherelektro.de` (und `www.macherelektro.de`).
   Render zeigt dir dann die nötigen DNS-Einträge an (ein **CNAME** bzw. eine **A**-Adresse).
2. Bei **IONOS** die Domain öffnen → **„DNS"** (der Punkt aus deinem Screenshot) → die von Render
   angezeigten Einträge eintragen.
3. Nach kurzer Wartezeit (DNS-Verteilung) ist die App unter `https://macherelektro.de` erreichbar,
   HTTPS-Zertifikat stellt Render automatisch aus.

---

## Gut zu wissen
- **Kostenlos-Tarif:** Der Server „schläft" nach ~15 Min ohne Besucher; der erste Aufruf danach
  dauert dann ~1 Minute. Für „immer wach" gibt es einen günstigen bezahlten Tarif.
- **Vorschau statt öffentlich:** Auf Wunsch bauen wir einen **Passwortschutz** ein, damit die Seite
  zunächst nur für dich/Testpersonen sichtbar ist.
- **Vor echtem Publikumsstart:** Abfragen der Shops sollten noch beschleunigt (parallel/zwischengespeichert)
  und die rechtliche Seite (Bildnutzung, Datenquellen) geklärt werden.
