# main.py – Startpunkt der App.
# Hier wird FastAPI gestartet und die Seiten werden ausgeliefert.

import re
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.csv_import import csv_einlesen
from app.eingabe import positionen_aus_text
from app.adapter.elektro_wandelt import ElektroWandeltAdapter
from app.adapter.elektroland24 import ElektroLand24Adapter

# Die App anlegen – der Titel erscheint z. B. in der automatischen Doku
app = FastAPI(title="Vergleichsplattform für Elektromaterial")

# Ordner, in dem die HTML-Vorlagen (Templates) liegen
TEMPLATE_ORDNER = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_ORDNER))

# Liste der Shops, die abgefragt werden. Neue Shops kommen hier einfach dazu.
SHOPS = [
    ElektroWandeltAdapter(pause=0.5),
    ElektroLand24Adapter(pause=0.5),
]


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

    # Für jeden Shop: Liste von Angeboten (gleiche Reihenfolge wie die Positionen)
    angebote_je_shop = {_slug(s.name): s.get_offers(positionen) for s in SHOPS}

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
    for shop in shops:
        slug = shop["slug"]
        total = 0.0
        alle_da = True
        for zeile in zeilen:
            a = zeile["angebote"][slug]
            gp = a.gesamtpreis(zeile["position"].menge)
            if a.gefunden and gp is not None:
                total += gp
            else:
                alle_da = False
        # Anfangs mit Paketversand rechnen (der Umschalter ändert das später im Browser)
        v = _versand_betrag(shop, total, art="paket")
        artikel_summen[slug] = round(total, 2)
        versand[slug] = round(v, 2)
        gesamt_summen[slug] = round(total + v, 2)
        vollstaendig[slug] = alle_da

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


@app.post("/warenkorb", response_class=HTMLResponse)
async def warenkorb_hochladen(request: Request, datei: UploadFile = File(...)):
    """Nimmt die hochgeladene CSV-Datei entgegen und zeigt den Preisvergleich."""
    inhalt = await datei.read()
    positionen = csv_einlesen(inhalt)
    return _vergleich_anzeigen(request, positionen, quelle=f"CSV-Datei: {datei.filename}")


@app.post("/warenkorb-manuell", response_class=HTMLResponse)
async def warenkorb_manuell(request: Request, eingabe: str = Form("")):
    """Nimmt direkt eingetippte Artikel/EANs entgegen und zeigt den Preisvergleich."""
    positionen = positionen_aus_text(eingabe)
    return _vergleich_anzeigen(request, positionen, quelle="Direkteingabe")
