# basis.py – Die gemeinsame Schnittstelle für ALLE Shop-Adapter.
#
# Idee: Jeder Shop wird durch eine eigene Klasse dargestellt, die von
# ShopAdapter erbt und die Methode `angebot_fuer(position)` ausfüllt.
# Der Rest der App spricht nur mit `get_offers(positionen)` und muss
# nichts über den einzelnen Shop wissen. So kommen neue Shops dazu,
# ohne dass der Kern geändert werden muss.
#
# Tempo:
# - Die Artikel eines Shops werden PARALLEL abgefragt (kleiner Pool,
#   damit der Shop nicht überlastet wird).
# - Ergebnisse werden einige Minuten ZWISCHENGESPEICHERT (Cache), damit
#   wiederholte Vergleiche nicht erneut beim Shop anfragen müssen.

import time
import threading
from concurrent.futures import ThreadPoolExecutor

from app.modelle import Position, Angebot

# Wie lange ein Ergebnis im Zwischenspeicher gültig bleibt (Sekunden)
CACHE_DAUER = 10 * 60  # 10 Minuten


class ShopAdapter:
    """Basisklasse für alle Shop-Adapter."""

    name = "Basis"          # wird in den Unterklassen überschrieben
    website = ""            # Startseite des Shops (für den Warenkorb-Link)
    warenkorb_typ = ""      # "oxid" (Link) oder "shopware" (Formular) – leer = nicht unterstützt
    warenkorb_endpunkt = "" # URL, an die der Warenkorb-Aufruf geht

    # Versandkosten-Pauschalen (Deutschland) je Versandart, in Euro
    versand_paket = 0.0
    versand_sperrgut = 0.0
    versand_spedition = 0.0
    # Gratis-Versand ab diesem Bestellwert (0 = kein Gratis-Versand). Gilt nur für Paketversand.
    versandfrei_ab = 0.0

    def __init__(self, max_parallel: int = 8):
        # Wie viele Artikel gleichzeitig bei diesem Shop abgefragt werden.
        # 8 ist ein guter Mittelweg: deutlich schneller für den Kunden,
        # aber immer noch moderat für den Shop-Server (kurze, einfache Abrufe).
        self.max_parallel = max_parallel
        # Zwischenspeicher: Suchschlüssel -> (Angebot, Zeitpunkt)
        self._cache: dict = {}
        self._cache_schloss = threading.Lock()

    def angebot_fuer(self, position: Position) -> Angebot:
        """
        Sucht EIN Angebot für EINE Position.
        Muss von jeder Shop-Klasse selbst umgesetzt werden.
        """
        raise NotImplementedError("Diese Methode muss der jeweilige Shop-Adapter umsetzen.")

    def _schluessel(self, position: Position) -> tuple:
        """Cache-Schlüssel: gleiche Suchdaten = gleiches Ergebnis."""
        return (position.ean or "", position.artikelnummer or "", position.beschreibung or "")

    def _angebot_mit_cache(self, position: Position) -> Angebot:
        """Holt ein Angebot – aus dem Zwischenspeicher, falls noch frisch."""
        schluessel = self._schluessel(position)
        jetzt = time.time()

        with self._cache_schloss:
            eintrag = self._cache.get(schluessel)
            if eintrag and (jetzt - eintrag[1]) < CACHE_DAUER:
                return eintrag[0]

        try:
            angebot = self.angebot_fuer(position)
        except Exception as fehler:
            # Fehler nicht zwischenspeichern – nächster Versuch darf neu anfragen
            return Angebot(shop=self.name, hinweis=f"Fehler beim Abruf: {fehler}")

        with self._cache_schloss:
            self._cache[schluessel] = (angebot, jetzt)
        return angebot

    def get_offers(self, positionen: list[Position]) -> list[Angebot]:
        """
        Holt für jede Position ein Angebot – parallel, mit Zwischenspeicher.
        Gibt eine Liste in derselben Reihenfolge wie die Positionen zurück.
        """
        if not positionen:
            return []
        with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
            return list(pool.map(self._angebot_mit_cache, positionen))
