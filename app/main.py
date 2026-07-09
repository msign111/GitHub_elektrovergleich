# main.py – Startpunkt der App.
# Hier wird FastAPI gestartet und die Seiten werden ausgeliefert.

import os
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.csv_import import csv_einlesen
from app.eingabe import positionen_aus_text
from app.katalog import KATEGORIEN
from app.adapter.elektro_wandelt import ElektroWandeltAdapter
from app.adapter.elektroland24 import ElektroLand24Adapter
from app.adapter.voltus import VoltusAdapter
from app.adapter.wagner import ElektroshopWagnerAdapter

# Die App anlegen – der Titel erscheint z. B. in der automatischen Doku
app = FastAPI(title="Vergleichsplattform für Elektromaterial")

# Ordner, in dem die HTML-Vorlagen (Templates) liegen
TEMPLATE_ORDNER = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_ORDNER))

# Liste der Shops, die abgefragt werden. Neue Shops kommen hier einfach dazu.
SHOPS = [
    ElektroWandeltAdapter(),
    ElektroLand24Adapter(),
    VoltusAdapter(),
    ElektroshopWagnerAdapter(),
]

# Schnelle Datenquelle fürs Stöbern/Suchen (liefert ganze Produktlisten).
KATALOG_QUELLE = next((s for s in SHOPS if hasattr(s, "produktliste")), SHOPS[0])


# ---- Passwortschutz (einfache Vorschau-Sperre) ----
# Passwort kommt aus der Umgebungsvariable SEITEN_PASSWORT; sonst Standard.
SEITEN_PASSWORT = os.environ.get("SEITEN_PASSWORT", "elektrohase")
FREIE_PFADE = {"/login"}


def _zugangstoken() -> str:
    """Erzeugt aus dem Passwort einen Cookie-Wert (nicht das Passwort selbst)."""
    return hashlib.sha256(("elektrovergleich::" + SEITEN_PASSWORT).encode("utf-8")).hexdigest()


@app.middleware("http")
async def passwortschutz(request: Request, call_next):
    """Lässt nur eingeloggte Besucher durch; sonst zur Login-Seite."""
    pfad = request.url.path
    if pfad in FREIE_PFADE or pfad == "/favicon.ico":
        return await call_next(request)
    if request.cookies.get("zugang") == _zugangstoken():
        return await call_next(request)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_seite(request: Request, fehler: int = 0):
    return templates.TemplateResponse(request, "login.html", {"fehler": bool(fehler)})


@app.post("/login")
async def login_pruefen(passwort: str = Form("")):
    if passwort == SEITEN_PASSWORT:
        antwort = RedirectResponse("/", status_code=303)
        antwort.set_cookie("zugang", _zugangstoken(), max_age=60 * 60 * 24 * 30,
                           httponly=True, samesite="lax")
        return antwort
    return RedirectResponse("/login?fehler=1", status_code=303)


def _slug(text: str) -> str:
    """Macht aus einem Shop-Namen eine einfache Kennung (z. B. 'Elektro-Wandelt' -> 'elektro-wandelt')."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _versand_betrag(shop: dict, artikel_summe: float, art: str = "paket") -> float:
    """
    Berechnet die Versandkosten eines Shops für die gewählte Versandart.
    Bei Paketversand entfällt der Versand, wenn die Gratis-Versand-Grenze
    erreicht ist (versandfrei_ab > 0 und Artikelsumme >= Grenze).
    """
    if artikel_summe <= 0:
        return 0.0
    if art == "sperrgut":
        return shop["versand_sperrgut"]
    if art == "spedition":
        return shop["versand_spedition"]
    # Standard: Paketversand
    grenze = shop["versandfrei_ab"]
    if grenze and artikel_summe >= grenze:
        return 0.0
    return shop["versand_paket"]


def _vergleich_anzeigen(request: Request, positionen, quelle: str) -> HTMLResponse:
    """
    Ruft für alle Positionen die Angebote aller Shops ab, berechnet je Shop
    den Gesamtpreis und ermittelt den günstigsten. Zeigt die Vergleichsseite.
    """
    # Shop-Infos für die Anzeige (inkl. Warenkorb-Fähigkeiten und Versandkosten)
    shops = [
        {
            "slug": _slug(s.name),
            "name": s.name,
            "website": s.website,
            "warenkorb_typ": s.warenkorb_typ,
            "warenkorb_endpunkt": s.warenkorb_endpunkt,
            "versand_paket": s.versand_paket,
            "versand_sperrgut": s.versand_sperrgut,
            "versand_spedition": s.versand_spedition,
            "versandfrei_ab": s.versandfrei_ab,
        }
        for s in SHOPS
    ]

    # Für jeden Shop: Liste von Angeboten (gleiche Reihenfolge wie die Positionen).
    # Die Shops werden PARALLEL abgefragt – die Wartezeit ist dadurch nur so lang
    # wie der langsamste Shop, nicht die Summe aller Shops.
    with ThreadPoolExecutor(max_workers=max(len(SHOPS), 1)) as pool:
        ergebnisse = pool.map(lambda s: (_slug(s.name), s.get_offers(positionen)), SHOPS)
        angebote_je_shop = dict(ergebnisse)

    # Tabellenzeilen: Position + Angebote + Bild + Anzeigename
    zeilen = []
    for i, position in enumerate(positionen):
        angebote = {slug: liste[i] for slug, liste in angebote_je_shop.items()}

        bild = ""
        anzeige_name = ""
        for slug in angebote:
            a = angebote[slug]
            if not bild and a.bild:
                bild = a.bild
            if not anzeige_name and a.titel:
                anzeige_name = a.titel
        if not anzeige_name:
            anzeige_name = f"{position.hersteller} {position.artikelnummer}".strip() or position.ean

        zeilen.append({
            "position": position,
            "angebote": angebote,
            "bild": bild,
            "anzeige_name": anzeige_name,
        })

    # Preise je Shop: Artikelsumme, Versand und Gesamt (inkl. Versand);
    # außerdem, ob der Shop alle Positionen liefern kann.
    artikel_summen = {}
    versand = {}
    gesamt_summen = {}
    vollstaendig = {}
    lieferbar_alle = {}
    for shop in shops:
        slug = shop["slug"]
        total = 0.0
        alle_da = True
        alle_lieferbar = True
        for zeile in zeilen:
            a = zeile["angebote"][slug]
            gp = a.gesamtpreis(zeile["position"].menge)
            if a.gefunden and gp is not None:
                total += gp
                if not a.lieferbar:
                    alle_lieferbar = False
            else:
                alle_da = False
                alle_lieferbar = False
        # Anfangs mit Paketversand rechnen (der Umschalter ändert das später im Browser)
        v = _versand_betrag(shop, total, art="paket")
        artikel_summen[slug] = round(total, 2)
        versand[slug] = round(v, 2)
        gesamt_summen[slug] = round(total + v, 2)
        vollstaendig[slug] = alle_da
        lieferbar_alle[slug] = alle_lieferbar

    # Shops von links nach rechts RANKEN: Prio 1 = alle Artikel sofort
    # lieferbar, Prio 2 = alle Artikel gefunden, Prio 3 = Gesamtpreis.
    # Die beste Wahl steht damit immer direkt neben der Artikel-Spalte.
    def _rang(shop: dict):
        slug = shop["slug"]
        preis = gesamt_summen[slug] if artikel_summen[slug] > 0 else float("inf")
        return (
            0 if (vollstaendig[slug] and lieferbar_alle[slug]) else 1,
            0 if vollstaendig[slug] else 1,
            preis,
        )
    shops.sort(key=_rang)

    # Günstigsten Shop bestimmen (inkl. Versand): bevorzugt einen, der ALLE Artikel hat
    kandidaten = [s["slug"] for s in shops if vollstaendig[s["slug"]] and artikel_summen[s["slug"]] > 0]
    if not kandidaten:
        kandidaten = [s["slug"] for s in shops if artikel_summen[s["slug"]] > 0]
    best_slug = min(kandidaten, key=lambda k: gesamt_summen[k]) if kandidaten else None

    return templates.TemplateResponse(
        request,
        "vergleich.html",
        {
            "zeilen": zeilen,
            "shops": shops,
            "artikel_summen": artikel_summen,
            "versand": versand,
            "gesamt_summen": gesamt_summen,
            "vollstaendig": vollstaendig,
            "best_slug": best_slug,
            "quelle": quelle,
            "anzahl": len(positionen),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def startseite(request: Request):
    """Liefert die Startseite mit CSV-Upload und Direkteingabe aus."""
    return templates.TemplateResponse(request, "start.html")


@app.get("/entdecken", response_class=HTMLResponse)
async def entdecken(request: Request):
    """Stöber-Seite: eigener Kategoriebaum + Live-Suche."""
    return templates.TemplateResponse(request, "entdecken.html", {"kategorien": KATEGORIEN})


@app.get("/api/suche")
async def api_suche(q: str = ""):
    """Liefert eine Produktliste (JSON) zu einem Suchbegriff – für Stöbern und Autovervollständigung."""
    begriff = (q or "").strip()
    if len(begriff) < 2:
        return JSONResponse([])
    return JSONResponse(KATALOG_QUELLE.produktliste(begriff, anzahl=24))


def _ean_ergaenzen(positionen) -> None:
    """
    Macht die Suche EINDEUTIG: Fehlt einer Position die EAN, wird sie über
    die Katalog-Suche anhand der Artikelnummer nachgeschlagen. Alle Shops
    suchen dann mit der EAN (weltweit eindeutig) statt mit der mehrdeutigen
    Artikelnummer - das verhindert falsche Treffer, z. B. die falsche
    Variante bei Elektroshop Wagner (dort teilen sich ganze Varianten-
    Familien eine Nummer). Die Artikelnummer bleibt als Notnagel erhalten.
    """
    for p in positionen:
        if p.ean or not p.artikelnummer:
            continue
        try:
            treffer = KATALOG_QUELLE.produktliste(p.artikelnummer, anzahl=5)
        except Exception:
            continue  # Katalog nicht erreichbar -> einfach ohne EAN weitersuchen
        gesucht = re.sub(r"[^a-z0-9]", "", p.artikelnummer.lower())
        for t in treffer:
            t_nr = re.sub(r"[^a-z0-9]", "", str(t.get("artikelnummer") or "").lower())
            if t_nr == gesucht and t.get("ean"):
                p.ean = str(t["ean"])
                break


@app.get("/vergleich")
async def vergleich_neuladen():
    """
    Der Vergleich wird im Browser im Hintergrund geladen und eingesetzt
    (die Adresse zeigt dann /vergleich). Lädt jemand diese Adresse direkt
    oder aktualisiert die Seite, gibt es keine Momentaufnahme mehr –
    dann geht es zurück zur Startseite für einen neuen Vergleich.
    """
    return RedirectResponse("/", status_code=303)


# Hinweis: Diese beiden Funktionen sind bewusst NICHT "async". FastAPI führt
# normale Funktionen in einem Neben-Thread aus – so bleibt der Server für
# andere Besucher ansprechbar, während er auf die Shop-Antworten wartet.

@app.post("/warenkorb", response_class=HTMLResponse)
def warenkorb_hochladen(request: Request, datei: UploadFile = File(...)):
    """Nimmt die hochgeladene CSV-Datei entgegen und zeigt den Preisvergleich."""
    inhalt = datei.file.read()
    positionen = csv_einlesen(inhalt)
    _ean_ergaenzen(positionen)
    return _vergleich_anzeigen(request, positionen, quelle=f"CSV-Datei: {datei.filename}")


@app.post("/warenkorb-manuell", response_class=HTMLResponse)
def warenkorb_manuell(request: Request, eingabe: str = Form("")):
    """Nimmt direkt eingetippte Artikel/EANs entgegen und zeigt den Preisvergleich."""
    positionen = positionen_aus_text(eingabe)
    _ean_ergaenzen(positionen)
    return _vergleich_anzeigen(request, positionen, quelle="Direkteingabe")
