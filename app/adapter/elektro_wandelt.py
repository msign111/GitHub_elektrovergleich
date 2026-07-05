# elektro_wandelt.py – Echter Shop-Adapter für www.elektro-wandelt.de
#
# Der Shop nutzt "Doofinder" als Suchdienst (dasselbe, was hinter dem
# Suchfeld der Webseite steckt). Über dessen API finden wir Artikel sowohl
# per EAN als auch per Herstellernummer und bekommen Preis und
# Verfügbarkeit direkt als saubere Daten (JSON) zurück – das ist deutlich
# stabiler, als HTML-Seiten auszulesen.
#
# Wichtig: Die Doofinder-API verlangt den HTTP-Header
#   Origin: https://www.elektro-wandelt.de
# sonst antwortet sie mit "403 request not authenticated".

import re
import threading

import requests

from app.modelle import Position, Angebot
from app.adapter.basis import ShopAdapter


def _zu_float(wert) -> float | None:
    """Wandelt einen Wert (Zahl oder Text wie '3,68') in eine Kommazahl um."""
    if wert is None or wert == "":
        return None
    if isinstance(wert, (int, float)):
        return float(wert)
    try:
        return float(str(wert).replace(",", "."))
    except ValueError:
        return None


def _normalisiere(text: str) -> str:
    """Vereinheitlicht eine Nummer zum Vergleichen: Großschreibung, ohne Leerzeichen."""
    return re.sub(r"\s+", "", (text or "").upper())


def _nur_alnum(text: str) -> str:
    """Nur Buchstaben/Ziffern – für einen toleranten Vergleich (ignoriert z. B. Bindestriche)."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


class ElektroWandeltAdapter(ShopAdapter):
    """Adapter, der echte Preise von elektro-wandelt.de über die Doofinder-Suche abruft."""

    name = "Elektro-Wandelt"
    website = "https://www.elektro-wandelt.de"
    # OXID-Shop: Warenkorb lässt sich per Link befüllen (index.php?cl=basket&fnc=tobasket&aproducts[...])
    warenkorb_typ = "oxid"
    warenkorb_endpunkt = "https://www.elektro-wandelt.de/index.php"
    # Versandkosten Deutschland (Quelle: elektro-wandelt.de/Versand-und-Zahlung/)
    versand_paket = 4.90
    versand_sperrgut = 29.90
    versand_spedition = 99.00
    versandfrei_ab = 0.0  # kein Gratis-Versand (Shop berechnet immer 4,90 €)

    HASHID = "e9a8fe4a75da30167409e3d88115c2fc"
    SUCH_URL = f"https://eu1-search.doofinder.com/6/{HASHID}/_search"
    SHOP = "https://www.elektro-wandelt.de"

    def __init__(self, max_parallel: int = 3):
        super().__init__(max_parallel)
        # Jeder Arbeits-Thread bekommt seine eigene Verbindung (thread-sicher).
        self._lokal = threading.local()

    @property
    def session(self) -> requests.Session:
        s = getattr(self._lokal, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
                ),
                "Accept-Language": "de-DE,de;q=0.9",
                # Ohne diesen Origin-Header lehnt die Doofinder-API die Anfrage ab (403).
                "Origin": self.SHOP,
                "Referer": self.SHOP + "/",
            })
            self._lokal.session = s
        return s

    def _suche(self, begriff: str, rpp: int = 5) -> list[dict]:
        """Fragt die Doofinder-Suche ab und gibt die Trefferliste (als Liste von dicts) zurück."""
        antwort = self.session.get(
            self.SUCH_URL,
            params={"query": begriff, "rpp": rpp},
            timeout=20,
        )
        if antwort.status_code != 200:
            return []
        try:
            return antwort.json().get("results", [])
        except ValueError:
            return []

    def produktliste(self, begriff: str, anzahl: int = 24) -> list[dict]:
        """
        Liefert eine Liste von Produkten zu einem Suchbegriff (für Stöbern/Suche).
        Jeder Eintrag: titel, artikelnummer, ean, preis, bild, link, verfuegbarkeit.
        Nutzt denselben schnellen Such-Dienst wie die Preisabfrage.
        """
        liste = []
        for t in self._suche(begriff.strip(), rpp=anzahl):
            preis = _zu_float(t.get("sale_price"))
            if preis is None:
                preis = _zu_float(t.get("best_price"))
            if preis is None:
                preis = _zu_float(t.get("price"))
            liste.append({
                "titel": (t.get("title") or "").strip(),
                "artikelnummer": (t.get("mpn") or "").strip(),
                "ean": (t.get("gtin") or "").strip(),
                "preis": preis,
                "bild": (t.get("image_link") or "").strip(),
                "link": (t.get("link") or "").strip(),
                "verfuegbarkeit": (t.get("availability") or "").strip(),
            })
        return liste

    def _passt_genau(self, treffer: dict, position: Position) -> bool:
        """Prüft, ob ein Treffer sicher zur Position passt (EAN oder Herstellernummer identisch)."""
        # Zuerst über die EAN (eindeutig)
        if position.ean and treffer.get("gtin"):
            if _normalisiere(position.ean) == _normalisiere(treffer["gtin"]):
                return True
        # Dann über die Herstellernummer (auch tolerant ohne Bindestriche/Leerzeichen)
        if position.artikelnummer and treffer.get("mpn"):
            gesucht = position.artikelnummer
            gefunden = treffer["mpn"]
            if _normalisiere(gesucht) == _normalisiere(gefunden):
                return True
            if _nur_alnum(gesucht) == _nur_alnum(gefunden):
                return True
        return False

    def _finde_treffer(self, position: Position) -> dict | None:
        """
        Sucht den passenden Treffer. Reihenfolge laut Plan: erst EAN, dann
        Herstellernummer, dann Beschreibung. Bevorzugt einen exakten Treffer;
        wenn eine Suche genau EIN Ergebnis liefert, wird dieses akzeptiert.
        """
        begriffe = []
        if position.ean:
            begriffe.append(position.ean)
        if position.artikelnummer:
            begriffe.append(position.artikelnummer)
        if position.beschreibung:
            begriffe.append(position.beschreibung)

        erster_einzeltreffer = None
        for begriff in begriffe:
            treffer = self._suche(begriff.strip())
            if not treffer:
                continue
            # 1) Exakter Treffer (EAN oder Herstellernummer identisch)
            for t in treffer:
                if self._passt_genau(t, position):
                    return t
            # 2) Genau ein Ergebnis? Merken als guten Rückfall.
            if erster_einzeltreffer is None and len(treffer) == 1:
                erster_einzeltreffer = treffer[0]

        return erster_einzeltreffer

    def angebot_fuer(self, position: Position) -> Angebot:
        # Es muss mindestens ein Suchbegriff vorhanden sein
        if not (position.ean or position.artikelnummer or position.beschreibung):
            return Angebot(shop=self.name, hinweis="Keine Artikelnummer/EAN vorhanden")

        treffer = self._finde_treffer(position)
        if treffer is None:
            begriff = position.ean or position.artikelnummer or position.beschreibung
            return Angebot(shop=self.name, hinweis=f"Kein Treffer für „{begriff}“")

        # Verkaufspreis: sale_price / best_price ist der aktuelle Preis, price die UVP
        preis = _zu_float(treffer.get("sale_price"))
        if preis is None:
            preis = _zu_float(treffer.get("best_price"))
        if preis is None:
            preis = _zu_float(treffer.get("price"))

        # Verfügbarkeit
        verfuegbarkeit = (treffer.get("availability") or "").strip()
        lieferbar = (
            str(treffer.get("zslagerartikel", "")).strip() == "1"
            or ("lager" in verfuegbarkeit.lower() and "nicht" not in verfuegbarkeit.lower())
        )

        # "auf lager" schöner schreiben
        if verfuegbarkeit:
            verfuegbarkeit = verfuegbarkeit[0].upper() + verfuegbarkeit[1:]

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
            titel=(treffer.get("title") or "").strip(),
            produktlink=(treffer.get("link") or "").strip(),
            bild=(treffer.get("image_link") or "").strip(),
            # Interne OXID-Artikel-ID – wird für den Warenkorb-Link gebraucht
            shop_produkt_id=(treffer.get("oxid") or "").strip(),
        )
