#!/usr/bin/env python3
"""
Dnevno dohvatanje dodijeljenih ugovora sa open.ejn.gov.ba za SVE kategorije
definisane u config/categories.json.

Pokretanje:
    python fetch.py                # dohvati sve kategorije (inkrementalno)
    python fetch.py --full vozila  # potpuno re-dohvatanje jedne kategorije

Kako dodati novu kategoriju:
    Samo dodaj novi objekat u config/categories.json - ovaj fajl se NE mijenja.

Podaci se čuvaju u data/<kategorija>.json kao mapa {id: red}, tako da je
svaki naredni pokret samo "upsert" novih/izmijenjenih ugovora (po polju
LastUpdated), a ne ponovno preuzimanje svega.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from odata_client import ODataClient, build_contains_filter

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config", "categories.json")
DATA_DIR = os.path.join(HERE, "data")
STATE_PATH = os.path.join(DATA_DIR, "_state.json")

# Od kada uzimamo podatke pri prvom (punom) dohvatanju - isto kao referentni dashboard
FULL_SYNC_FROM = "2024-01-01T00:00:00Z"

AWARD_FIELDS = [
    "Id", "Number", "NoticeNumber", "Value", "AnnualValue", "ContractDate",
    "Announced", "ContractingAuthorityName", "ContractingAuthorityCityName",
    "ContractingAuthorityType", "ProcedureName", "ProcedureNumber",
    "ProcedureType", "ContractType", "ContractCategoryName",
    "ContractSubcategoryName", "LotName", "AwardCriterion",
    "NumberOfReceivedOffers", "IsContractConcluded", "LastUpdated",
]


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def fetch_category(client: ODataClient, key: str, cfg: dict, since_iso: str) -> int:
    """Dohvata i upserta ugovore za jednu kategoriju. Vraća broj obrađenih redova."""
    entity_set = client.find_entity_set("Award", "Extended")

    keyword_filter = build_contains_filter(
        "ContractSubcategoryName", cfg["subcategory_keywords"]
    )
    category_filter = build_contains_filter(
        "ContractCategoryName", cfg["subcategory_keywords"]
    )
    date_filter = f"LastUpdated gt {since_iso}"

    full_filter = f"({keyword_filter} or {category_filter}) and {date_filter}"

    print(f"[{key}] entity set = {entity_set}")
    print(f"[{key}] filter = {full_filter}")

    data_path = os.path.join(DATA_DIR, f"{key}.json")
    store = load_json(data_path, {})

    count = 0
    for row in client.query(entity_set, filter_expr=full_filter, select=AWARD_FIELDS):
        store[str(row["Id"])] = row
        count += 1
        if count % 200 == 0:
            print(f"[{key}] ... {count} redova obrađeno")

    save_json(data_path, store)
    print(f"[{key}] gotovo: {count} novih/izmijenjenih, ukupno u bazi: {len(store)}")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full", metavar="KATEGORIJA",
        help="Potpuno re-dohvatanje jedne kategorije od 1.1.2024.",
    )
    args = parser.parse_args()

    categories = load_json(CONFIG_PATH, {})
    if not categories:
        print("Nema definisanih kategorija u config/categories.json", file=sys.stderr)
        sys.exit(1)

    state = load_json(STATE_PATH, {})
    client = ODataClient()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    keys_to_run = [args.full] if args.full else list(categories.keys())

    for key in keys_to_run:
        if key not in categories:
            print(f"Nepoznata kategorija: {key}", file=sys.stderr)
            continue

        since = FULL_SYNC_FROM if (args.full or key not in state) else state[key]
        try:
            fetch_category(client, key, categories[key], since)
            state[key] = now_iso
        except Exception as exc:
            print(f"[{key}] GREŠKA: {exc}", file=sys.stderr)

    save_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
