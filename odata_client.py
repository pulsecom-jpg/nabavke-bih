"""
Generički klijent za javni OData API Agencije za javne nabavke BiH.

Portal: https://open.ejn.gov.ba
Dokumentacija (Swagger): https://open.ejn.gov.ba/docs
Metadata (šema svih entiteta): https://open.ejn.gov.ba/$metadata

Ovaj klijent:
  1. Prvo učita "service document" (koren API-ja) da otkrije STVARNA imena
     kolekcija (entity set-ova) - jer se ime kolekcije u OData ne mora
     poklapati sa imenom tipa iz $metadata (npr. tip "AwardExtendedListDto"
     može biti izložen kao kolekcija "Awards" ili "AwardExtendedListDto" -
     ne pretpostavljamo, nego provjerimo).
  2. Nudi generičku funkciju za paginirano dohvatanje podataka uz $filter.

Zbog toga je isti klijent upotrebljiv za BILO KOJU kategoriju nabavki -
mijenja se samo filter (ključne riječi / CPV), ne kod.
"""
import requests
import time
import sys

BASE_URL = "https://open.ejn.gov.ba"
TIMEOUT = 30
MAX_RETRIES = 3


class ODataClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._entity_sets = None  # cache: {"Award...": "url"}

    # ------------------------------------------------------------------
    def discover_entity_sets(self) -> dict:
        """Vraća mapu {ime_entity_seta: relativni_url} čitajući service document."""
        if self._entity_sets is not None:
            return self._entity_sets

        resp = self._get(self.base_url, headers={"Accept": "application/json"})
        data = resp.json()
        result = {}
        for item in data.get("value", []):
            # standardni OData service document format: {"name": "...", "url": "..."}
            name = item.get("name") or item.get("url")
            url = item.get("url", name)
            result[name] = url
        self._entity_sets = result
        return result

    def find_entity_set(self, *name_fragments: str) -> str:
        """
        Pronalazi ime prave kolekcije koje sadrži sve zadane fragmente
        (case-insensitive). Baca grešku sa listom dostupnih opcija ako ne nađe
        ništa ili nađe više kandidata, da bi se lako moglo ručno ispraviti.
        """
        sets = self.discover_entity_sets()
        fragments_lower = [f.lower() for f in name_fragments]
        candidates = [
            name for name in sets
            if all(frag in name.lower() for frag in fragments_lower)
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise ValueError(
                f"Nije pronađen entity set za fragmente {name_fragments}.\n"
                f"Dostupni entity setovi ({len(sets)}):\n  " + "\n  ".join(sorted(sets))
            )
        # Ako ima više kandidata, uzmi najkraći naziv (obično je to "glavna" lista,
        # a duži nazivi su varijante tipa "...Extended...")
        candidates.sort(key=len)
        print(
            f"[upozorenje] više kandidata za {name_fragments}: {candidates} "
            f"-> koristim '{candidates[0]}'",
            file=sys.stderr,
        )
        return candidates[0]

    # ------------------------------------------------------------------
    def query(
        self,
        entity_set: str,
        filter_expr: str | None = None,
        select: list[str] | None = None,
        orderby: str | None = None,
        top: int = 500,
        max_pages: int = 200,
    ):
        """
        Generator koji vraća sve redove (dict) iz zadate kolekcije,
        prateći @odata.nextLink dok ima stranica ili dok se ne dosegne max_pages.
        """
        params = {"$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        if select:
            params["$select"] = ",".join(select)
        if orderby:
            params["$orderby"] = orderby

        url = f"{self.base_url}/{entity_set}"
        page = 0
        while url and page < max_pages:
            resp = self._get(url, params=params if page == 0 else None,
                              headers={"Accept": "application/json"})
            data = resp.json()
            for row in data.get("value", []):
                yield row
            url = data.get("@odata.nextLink")
            page += 1

    # ------------------------------------------------------------------
    def _get(self, url, params=None, headers=None):
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Neuspješan GET na {url}: {last_exc}")


def build_contains_filter(field: str, keywords: list[str], op: str = "or") -> str:
    """
    Gradi OData $filter izraz tipa:
      contains(tolower(ContractSubcategoryName),'vozil') or contains(...,'guma')
    """
    parts = [f"contains(tolower({field}),'{kw.lower()}')" for kw in keywords]
    return f" {op} ".join(parts)
