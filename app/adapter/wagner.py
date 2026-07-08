# wagner.py – Echter Shop-Adapter für www.elektroshopwagner.de
#
# Besonderheit: Der Shop schützt seine Webseite gegen automatisierte
# Zugriffe (Akamai). Seine SUCHE läuft aber über den externen Dienst
# "Algolia" – dieselbe Quelle, die auch das Suchfeld der Webseite nutzt.
# Darüber bekommen wir Preis, Verfügbarkeit, Bild und Produktlink als
# saubere Daten (JSON), ohne die Shop-Seiten selbst aufzurufen.
#
# Wichtig: Die Algolia-Abfrage braucht den HTTP-Header
#   Origin: https://www.elektroshopwagner.de
# sonst wird sie abgelehnt. Der verwendete Schlüssel ist der öffentliche
# Nur-Suchen-Schlüssel, den die Webseite selbst an jeden Browser ausliefert.
#
# Stolperstein: Wagner führt bei Sammel-Artikeln mehrere EANs bzw.
# Herstellernummern als LISTE in einem Feld – beim Vergleichen also immer
# "ist meine Nummer in der Liste enthalten?" prüfen.

import re
import threading

import requests

from app.modelle import Position, Angebot
from app.adapter.basis import ShopAdapter


def _zu_float(wert) -> float | None:
    """Wandelt einen Wert (Zahl oder Text wie '3,63') in eine Kommazahl um."""
    if wert is None or wert == "":
        return None
    if isinstance(wert, (int, float)):
        return float(wert)
    try:
        return float(str(wert).replace(",", "."))
    except ValueError:
        return None


def _als_liste(wert) -> list:
    """Macht aus Einzelwert oder Liste immer eine Liste (Wagner mischt beides)."""
    if wert is None:
        return []
    if isinstance(wert, list):
        return wert
    return [wert]


def _nur_alnum(text: str) -> str:
    """Nur Buchstaben/Ziffern – für einen toleranten Nummern-Vergleich."""
    return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())


class ElektroshopWagnerAdapter(ShopAdapter):
    """Adapter, der echte Preise von elektroshopwagner.de über die Algolia-Suche abruft."""

    name = "Elektroshop Wagner"
    website = "https://www.elektroshopwagner.de"
    # Kein Vorbefüllen des Warenkorbs möglich – die Vergleichsseite zeigt
    # stattdessen den Link zum Shop bzw. zum Produkt.
    warenkorb_typ = ""
    warenkorb_endpunkt = ""
    # Versandkosten Deutschland (Quelle: elektroshopwagner.de, Seite
    # "Liefer- und Versandbedingungen", Stand 07/2026: Paketdienst 4,95 €,
    # Spedition "nach Volumengewicht ab 39,95 €")
    versand_paket = 4.95
    versand_sperrgut = 39.95
    versand_spedition = 39.95
    versandfrei_ab = 0.0

    APP_ID = "BG4OWNWGAL"
    SUCH_SCHLUESSEL = "2e0f5361a1ff26d0b0660d57eb25a103"  # öffentlicher Such-Schlüssel der Webseite
    INDEX = "prod_products_de"
    SUCH_URL = "https://bg4ownwgal-dsn.algolia.net/1/indexes/*/queries"
    FELDER = "ean,model,name,preis-eur,rrp,availability_text,availability_state,slug,product_id,image_url"

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
                "Content-Type": "application/json",
                "X-Algolia-Application-Id": self.APP_ID,
                "X-Algolia-API-Key": self.SUCH_SCHLUESSEL,
                # Ohne diesen Origin-Header lehnt Algolia die Anfrage ab.
                "Origin": self.website,
                "Referer": self.website + "/",
            })
            self._lokal.session = s
        return s

    def _suche(self, begriff: str, anzahl: int = 5) -> list[dict]:
        """Fragt die Algolia-Suche ab und gibt die Trefferliste zurück."""
        from urllib.parse import urlencode
        params = urlencode({
            "query": begriff,
            "hitsPerPage": anzahl,
            "attributesToRetrieve": self.FELDER,
        })
        antwort = self.session.post(
            self.SUCH_URL,
            json={"requests": [{"indexName": self.INDEX, "params": params}]},
            timeout=20,
        )
        if antwort.status_code != 200:
            return []
        try:
            ergebnisse = antwort.json().get("results", [])
            return ergebnisse[0].get("hits", []) if ergebnisse else []
        except (ValueError, IndexError):
            return []

    def _passt_genau(self, treffer: dict, position: Position) -> bool:
        """Prüft, ob ein Treffer sicher zur Position passt (EAN oder Herstellernummer)."""
        if position.ean:
            eans = [str(e).strip() for e in _als_liste(treffer.get("ean"))]
            if str(position.ean).strip() in eans:
                return True
        if position.artikelnummer:
            gesucht = _nur_alnum(position.artikelnummer)
            modelle = [_nur_alnum(m) for m in _als_liste(treffer.get("model"))]
            if gesucht and gesucht in modelle:
                return True
        return False

    def _finde_treffer(self, position: Position) -> dict | None:
        """Sucht den passenden Treffer: erst EAN, dann Herstellernummer, dann Beschreibung."""
        begriffe = []
        if position.ean:
            begriffe.append(position.ean)
        if position.artikelnummer:
            begriffe.append(position.artikelnummer)
        if position.beschreibung:
            begriffe.append(position.beschreibung)

        erster_einzeltreffer = None
        for begriff in begriffe:
            treffer = self._suche(str(begriff).strip())
            if not treffer:
                continue
            for t in treffer:
                if self._passt_genau(t, position):
                    return t
            if erster_einzeltreffer is None and len(treffer) == 1:
                erster_einzeltreffer = treffer[0]

        return erster_einzeltreffer

    def angebot_fuer(self, position: Position) -> Angebot:
        if not (position.ean or position.artikelnummer or position.beschreibung):
            return Angebot(shop=self.name, hinweis="Keine Artikelnummer/EAN vorhanden")

        treffer = self._finde_treffer(position)
        if treffer is None:
            begriff = position.ean or position.artikelnummer or position.beschreibung
            return Angebot(shop=self.name, hinweis=f"Kein Treffer für „{begriff}“")

        # "preis-eur" ist der Brutto-Verkaufspreis (teils mit 4 Nachkommastellen)
        preis = _zu_float(treffer.get("preis-eur"))
        if preis is not None:
            preis = round(preis, 2)

        verfuegbarkeit = str(treffer.get("availability_text") or "").strip()
        lieferbar = (
            str(treffer.get("availability_state", "")).strip() == "1"
            or ("lager" in verfuegbarkeit.lower() and "nicht" not in verfuegbarkeit.lower())
        )

        # Produktlink aus Kurzname (slug) und Produkt-ID zusammensetzen,
        # z. B. .../de/p/merten-meg2301-0319-..._169784
        # Bei Sammel-Artikeln sind slug/product_id Listen -> ersten Eintrag nehmen.
        produktlink = ""
        slugs = _als_liste(treffer.get("slug"))
        ids = _als_liste(treffer.get("product_id"))
        slug = str(slugs[0] if slugs else "").strip()
        produkt_id = str(ids[0] if ids else "").strip()
        if slug and produkt_id:
            produktlink = f"{self.website}/de/p/{slug}_{produkt_id}"

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
            titel=str(treffer.get("name") or "").strip(),
            produktlink=produktlink,
            bild=str(treffer.get("image_url") or "").strip(),
            shop_produkt_id=produkt_id,
        )
