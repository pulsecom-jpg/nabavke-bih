# Izvještaji o javnim nabavkama BiH (generička podloga)

Automatski dnevni izvještaji o dodijeljenim ugovorima sa Portala javnih
nabavki BiH, po kategorijama. Trenutno podešeno za:

- **vozila** – putnička/teretna/specijalna vozila, gume, servis, najam
- **medicinska_oprema** – medicinska oprema, medicinska pomagala, lijekovi

Podaci dolaze direktno sa zvaničnog javnog **OData API-ja** Agencije za
javne nabavke BiH: `https://open.ejn.gov.ba` (bez potrebe za API ključem).
Ovo je isti izvor podataka koji vjerovatno koristi i dashboard koji si
dobio na mail za vozila.

## Kako je organizovano

```
config/categories.json   <- OVDJE se dodaju nove kategorije (samo JSON, bez koda)
odata_client.py          <- generički klijent za OData API (ne dira se)
fetch.py                 <- dnevno dohvatanje i inkrementalni upsert u data/*.json
report.py                <- generisanje output/*.html + output/*.csv
data/                     <- "baza" - jedan JSON fajl po kategoriji
output/                   <- gotovi HTML izvještaji + CSV, ovo se objavljuje
.github/workflows/daily.yml <- GitHub Action koja ovo pokreće SVAKI DAN automatski
```

## Prvo pokretanje (VAŽNO - jednokratna provjera)

OData naziv kolekcije (npr. da li se zove `AwardExtendedListDto`,
`Awards`, `AwardsExtended`...) se ne vidi iz šeme nego se otkriva sa
servera u trenutku pokretanja. Prvi put kad pokreneš `fetch.py`, ako
naziv ne bude tačno pogođen, skripta će ispisati grešku sa **kompletnom
listom stvarnih naziva** dostupnih na serveru - tada samo prilagodiš
poziv `client.find_entity_set("Award", "Extended")` u `fetch.py` prema
tačnom nazivu sa te liste. Nakon toga radi trajno bez izmjena.

```bash
pip install -r requirements.txt
python fetch.py --full vozila          # prvi test na jednoj kategoriji
python report.py
open output/vozila.html                 # ili otvori u browseru
```

Ako sve prođe, pokreni potpuno dohvatanje za sve kategorije:

```bash
python fetch.py --full vozila
python fetch.py --full medicinska_oprema
python report.py
```

## Dodavanje nove kategorije (npr. "hrana i catering")

Otvori `config/categories.json` i dodaj:

```json
"hrana": {
  "title": "Hrana i catering u javnim nabavkama BiH",
  "description": "Svi dodijeljeni ugovori za nabavku hrane, pića i usluga cateringa.",
  "subcategory_keywords": ["hrana", "prehrambeni", "catering", "namirnice"],
  "text_fallback_keywords": ["hrana", "catering"]
}
```

Zatim:

```bash
python fetch.py --full hrana
python report.py
```

Novi izvještaj se automatski pojavljuje u navigaciji na svim stranicama
i uključuje se u dnevni GitHub Actions posao bez ikakve dodatne izmjene
workflow fajla.

## Automatsko dnevno pokretanje

`.github/workflows/daily.yml` pokreće `fetch.py` + `report.py` svaki dan
u 06:00 UTC i commituje promjene u `data/` i `output/`. Da bi izvještaji
bili vidljivi kao web stranica:

- **Najjednostavnije:** uključi GitHub Pages za ovaj repo, source = `/output`
  na `main` grani. Dobićeš `https://<korisnik>.github.io/<repo>/`.
- **Alternativa (Render):** poveži repo na Render kao Static Site sa
  Publish directory = `output`, i dodaj Render Cron Job koji poziva
  `python fetch.py && python report.py` (Render redeploy-uje static site
  automatski nakon svakog push-a sa GitHub Actions-a, ili možeš pustiti
  cron direktno na Renderu umjesto GitHub Actions-a - obje opcije rade).

## Napomena o preciznosti filtriranja

Filtriranje trenutno ide po `ContractCategoryName` / `ContractSubcategoryName`
(tekstualna kategorizacija koju sam ugovorni organi biraju pri unosu
ugovora), uz listu ključnih riječi po kategoriji. Ovo je isti princip po
kojem izgleda da radi i originalni "Vozila" dashboard. Ako ti pravi podaci
pokažu da neki relevantni ugovori promiču ispod radara (npr. drugačiji
naziv podkategorije), samo dodaj tu riječ u `subcategory_keywords` u
`config/categories.json` - ne treba mijenjati kod.
