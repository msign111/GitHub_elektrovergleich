# elektroland24.py – Echter Shop-Adapter für www.elektroland24.de
#
# elektroland24 ist ein Shopware-6-Shop. Zwei Schritte:
#  1) Über den Such-Vorschlag (/suggest?search=...) den Produktlink finden.
#     Diese Suche findet Artikel per Herstellernummer UND per EAN.
#  2) Die Produktseite laden und dort Preis und Verfügbarkeit sauber auslesen
#     (strukturierte Daten: meta[itemprop=price] und die Lieferinformation).

import re

import requests
from bs4 import BeautifulSoup

from app.modelle import Position, Angebot
from app.adapter.basis import ShopAdapter


def _zu_float(wert) -> float | None:
    """Wandelt einen Wert (Zahl oder Text wie '3,46') in eine Kommazahl um."""
    if wert is None or wert == "":
        return None
    if isinstance(wert, (int, float)):
        return float(wert)
    try:
        return float(str(wert).replace(",", "."))
    except ValueError:
        return None


class ElektroLand24Adapter(ShopAdapter):
    """Adapter, der echte Preise von elektroland24.de abruft."""

    name = "elektroland24"
    website = "https://www.elektroland24.de"
    SHOP = "https://www.elektroland24.de"
    # Shopware-Shop: Warenkorb wird per Formular (POST) befüllt
    warenkorb_typ = "shopware"
    warenkorb_endpunkt = "https://www.elektroland24.de/checkout/line-item/add"
    # Versandkosten Deutschland (Quelle: Versandkosten-Seite von elektroland24)
    versand_paket = 5.90
    versand_sperrgut = 26.90
    versand_spedition = 99.00
    versandfrei_ab = 0.0  # keine offiziell belegte Gratis-Versand-Grenze

    def __init__(self, pause: float = 0.5):
        super().__init__(pause)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept-Language": "de-DE,de;q=0.9",
        })

    def _produkt_url(self, begriff: str) -> str | None:
        """Fragt den Such-Vorschlag ab und gibt den ersten echten Produktlink zurück."""
        antwort = self.session.get(
            self.SHOP + "/suggest",
            params={"search": begriff},
            timeout=20,
        )
        if antwort.status_code != 200:
            return None
        antwort.encoding = "utf-8"
        soup = BeautifulSoup(antwort.text, "lxml")
        # Der erste Link, der auf eine Produktseite (.html) zeigt, ist der beste Treffer.
        for a in soup.select("a.search-suggest-product-link, a[href]"):
            href = a.get("href", "")
            if href.startswith("http") and href.endswith(".html"):
                return href
        return None

    def angebot_fuer(self, position: Position) -> Angebot:
        # Suchbegriffe der Reihe nach: erst EAN, dann Herstellernummer, dann Beschreibung
        begriffe = [b for b in (position.ean, position.artikelnummer, position.beschreibung) if b]
        if not begriffe:
            return Angebot(shop=self.name, hinweis="Keine Artikelnummer/EAN vorhanden")

        url = None
        for begriff in begriffe:
            url = self._produkt_url(begriff.strip())
            if url:
                break

        if not url:
            return Angebot(shop=self.name, hinweis=f"Kein Treffer für „{begriffe[0]}“")

        # Produktseite laden und Daten auslesen
        antwort = self.session.get(url, timeout=20)
        antwort.encoding = "utf-8"
        soup = BeautifulSoup(antwort.text, "lxml")

        # Name aus der Überschrift
        h1 = soup.select_one("h1")
        titel = " ".join(h1.get_text(" ", strip=True).split()) if h1 else ""

        # Hauptpreis aus den strukturierten Daten (eindeutig, ohne Zubehör)
        preis_el = soup.select_one("meta[itemprop='price']")
        preis = _zu_float(preis_el.get("content")) if preis_el else None

        # Verfügbarkeit / Lieferinformation
        liefer_el = soup.select_one(".delivery-information")
        verfuegbarkeit = " ".join(liefer_el.get_text(" ", strip=True).split()) if liefer_el else ""
        klassen = liefer_el.get("class", []) if liefer_el else []
        lieferbar = ("delivery-available" in klassen) or (
            bool(verfuegbarkeit) and "nicht" not in verfuegbarkeit.lower()
        )

        # Produktbild (für die Anzeige)
        bild_el = soup.select_one("meta[property='og:image']")
        bild = bild_el.get("content", "") if bild_el else ""

        # Interne Produkt-ID (UUID) aus dem "In den Warenkorb"-Formular –
        # wird gebraucht, um den Warenkorb per Formular zu befüllen.
        produkt_id = ""
        ref = soup.select_one("form[action*='line-item/add'] input[name$='[referencedId]']")
        if ref:
            produkt_id = ref.get("value", "")

        preis_text = ""
        if preis is not None:
            preis_text = f"{preis:.2f}".replace(".", ",") + " €"

        return Angebot(
            shop=self.name,
            gefunden=preis is not None,
            preis=preis,
            preis_text=preis_text,
            verfuegbarkeit=verfuegbarkeit,
            lieferbar=lieferbar,
            titel=titel,
            produktlink=url,
            bild=bild,
            shop_produkt_id=produkt_id,
        )
