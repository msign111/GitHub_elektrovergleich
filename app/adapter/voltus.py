# voltus.py – Echter Shop-Adapter für www.voltus.de
#
# Voltus ist ein OXID-Shop (wie Elektro-Wandelt) mit FactFinder-Suche.
# - Suche über index.php?cl=search&searchparam=... (findet Herstellernummer und EAN).
# - Bei einem eindeutigen Treffer leitet die Suche direkt auf die Produktseite um;
#   dann lesen wir Preis/Verfügbarkeit dort (meta[itemprop=price]).
# - Bei mehreren Treffern kommt eine Liste; dann nehmen wir den passenden Treffer
#   aus der ersten productBox.
# - Warenkorb-Befüllung wie bei OXID üblich (aproducts-Link).

import re
import threading

import requests
from bs4 import BeautifulSoup

from app.modelle import Position, Angebot
from app.adapter.basis import ShopAdapter


def _preis_text_zu_float(text: str) -> float | None:
    """Deutscher Preistext -> Zahl.  '1.234,56 €' -> 1234.56"""
    treffer = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", text or "")
    if not treffer:
        return None
    try:
        return float(treffer.group(0).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _content_zu_float(wert) -> float | None:
    if wert is None or wert == "":
        return None
    try:
        return float(str(wert))
    except ValueError:
        return None


def _sauber(text: str) -> str:
    return " ".join((text or "").split())


def _nur_ziffern(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _nur_alnum(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


class VoltusAdapter(ShopAdapter):
    """Adapter, der echte Preise von voltus.de abruft."""

    name = "Voltus"
    website = "https://www.voltus.de"
    SHOP = "https://www.voltus.de"

    # OXID-Shop: Warenkorb per Link befüllbar (wie Elektro-Wandelt)
    warenkorb_typ = "oxid"
    warenkorb_endpunkt = "https://www.voltus.de/index.php"

    # Versandkosten Deutschland (Quelle: voltus.de/versandkosten/)
    versand_paket = 6.90
    versand_sperrgut = 29.90
    versand_spedition = 77.00      # Spedition unter 99 kg
    versandfrei_ab = 0.0           # keine offiziell belegte Gratis-Versand-Grenze

    def __init__(self, max_parallel: int = 8):
        super().__init__(max_parallel)
        self._lokal = threading.local()

    @property
    def session(self) -> requests.Session:
        s = getattr(self._lokal, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9",
            })
            self._lokal.session = s
        return s

    # ------- Hilfen zum Auslesen -------

    def _verfuegbarkeit(self, text: str):
        low = (text or "").lower()
        if "auf lager" in low:
            return "Auf Lager", True
        if "bestellt" in low:
            return "Wird bestellt", False
        sauber = _sauber(text)
        return (sauber[:40] or "unbekannt"), ("lieferbar" in low)

    def _aus_box(self, box) -> Angebot:
        """Liest ein Angebot aus einer productBox (Trefferliste)."""
        a = box.select_one("a[href*='.html']")
        titel = ""
        link = ""
        if a:
            titel = _sauber(a.get("title") or a.get("data-product-title") or a.get_text(" ", strip=True))
            link = a.get("href", "")

        preis_el = box.select_one(".c4s-gross-price")
        preis = _preis_text_zu_float(preis_el.get_text(" ", strip=True)) if preis_el else None

        lager_el = box.select_one(".stock-delivery")
        verfuegbarkeit, lieferbar = self._verfuegbarkeit(
            lager_el.get_text(" ", strip=True) if lager_el else ""
        )

        ean_el = box.select_one(".product-eannum")
        ean = _nur_ziffern(ean_el.get_text(" ", strip=True)) if ean_el else ""

        aid_el = box.select_one("input[name='aid'], input[name='anid']")
        aid = aid_el.get("value", "") if aid_el else ""

        bild_el = box.select_one("img.product-img, img[src*='/product/']")
        bild = bild_el.get("src", "") if bild_el else ""

        return Angebot(
            shop=self.name, gefunden=preis is not None, preis=preis,
            verfuegbarkeit=verfuegbarkeit, lieferbar=lieferbar,
            titel=titel, produktlink=link, bild=bild, shop_produkt_id=aid,
            hinweis="", ), ean

    def _aus_detailseite(self, antwort) -> Angebot:
        """Liest ein Angebot von einer Produktseite (nach Redirect)."""
        soup = BeautifulSoup(antwort.text, "lxml")

        h1 = soup.select_one("h1")
        titel = _sauber(h1.get_text(" ", strip=True)) if h1 else ""

        preis = None
        preis_el = soup.select_one("meta[itemprop='price'], [itemprop='price']")
        if preis_el is not None:
            preis = _content_zu_float(preis_el.get("content")) or _preis_text_zu_float(preis_el.get_text(" ", strip=True))
        if preis is None:
            gp = soup.select_one(".c4s-gross-price")
            preis = _preis_text_zu_float(gp.get_text(" ", strip=True)) if gp else None

        lager_el = soup.select_one(".stock-delivery")
        verfuegbarkeit, lieferbar = self._verfuegbarkeit(
            lager_el.get_text(" ", strip=True) if lager_el else ""
        )

        m = re.search(r"EAN[:\s]*?(\d{8,14})", antwort.text)
        ean = m.group(1) if m else ""

        aid_el = soup.select_one("input[name='aid'], input[name='anid']")
        aid = aid_el.get("value", "") if aid_el else ""

        bild_el = soup.select_one("meta[property='og:image']")
        bild = bild_el.get("content", "") if bild_el else ""

        angebot = Angebot(
            shop=self.name, gefunden=preis is not None, preis=preis,
            verfuegbarkeit=verfuegbarkeit, lieferbar=lieferbar,
            titel=titel, produktlink=antwort.url, bild=bild, shop_produkt_id=aid,
        )
        return angebot, ean

    def _suche(self, begriff: str):
        """Führt eine Suche aus. Gibt (typ, objekt) zurück:
        ('liste', soup) oder ('detail', antwort)."""
        antwort = self.session.get(
            self.SHOP + "/index.php",
            params={"cl": "search", "searchparam": begriff},
            timeout=20,
        )
        antwort.encoding = "utf-8"
        if "cl=search" in antwort.url:
            return "liste", BeautifulSoup(antwort.text, "lxml")
        return "detail", antwort

    # ------- Hauptmethode -------

    def angebot_fuer(self, position: Position) -> Angebot:
        # 1) Über die EAN (eindeutig) – nur akzeptieren, wenn die EAN wirklich passt
        if position.ean:
            typ, obj = self._suche(position.ean)
            if typ == "detail":
                angebot, ean = self._aus_detailseite(obj)
                if angebot.gefunden and _nur_ziffern(ean) == _nur_ziffern(position.ean):
                    return angebot
            else:
                for box in obj.select(".productBox"):
                    angebot, ean = self._aus_box(box)
                    if angebot.gefunden and _nur_ziffern(ean) == _nur_ziffern(position.ean):
                        return angebot

        # 2) Über die Herstellernummer – Treffer nur, wenn die Nummer im Titel vorkommt
        #    (verhindert falsche Zuordnungen bei unbekannten Nummern)
        if position.artikelnummer:
            gesucht = _nur_alnum(position.artikelnummer)
            typ, obj = self._suche(position.artikelnummer.strip())
            if typ == "detail":
                angebot, _ = self._aus_detailseite(obj)
                if angebot.gefunden and gesucht and gesucht in _nur_alnum(angebot.titel):
                    return angebot
            else:
                for box in obj.select(".productBox"):
                    angebot, _ = self._aus_box(box)
                    if angebot.gefunden and gesucht and gesucht in _nur_alnum(angebot.titel):
                        return angebot

        # 3) Nur über die Beschreibung suchen, wenn WEDER EAN NOCH Artikelnummer
        #    vorhanden ist (sonst riskieren wir falsche Treffer)
        if position.beschreibung and not position.ean and not position.artikelnummer:
            typ, obj = self._suche(position.beschreibung.strip())
            if typ == "detail":
                angebot, _ = self._aus_detailseite(obj)
                if angebot.gefunden:
                    return angebot
            else:
                box = obj.select_one(".productBox")
                if box is not None:
                    angebot, _ = self._aus_box(box)
                    if angebot.gefunden:
                        return angebot

        begriff = position.ean or position.artikelnummer or position.beschreibung
        return Angebot(shop=self.name, hinweis=f"Kein Treffer für „{begriff}“")
