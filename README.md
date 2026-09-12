# Nabavke BiH - univerzalni analiticki sistem

Web aplikacija za objedinjavanje, filtriranje i analizu dodijeljenih ugovora. Pocetna konfiguracija je namijenjena zdravstvenim nabavkama, ali model podataka nije vezan za zdravstvo: ista aplikacija moze koristiti kategorije Vozila, IT, Gradjevina, Ciscenje, Energenti, Osiguranje itd.

## Funkcije
- detaljna pretraga: ustanova, grad, predmet/opis, dobavljac, proizvodjac/brend, CPV/JRJN, LOT i broj obavjestenja
- filteri: kategorija/podkategorija, period/godina, vrijednost, postupak, broj ponuda
- rang-liste ustanova, dobavljaca i gradova
- broj ugovora, ukupna vrijednost, broj ustanova i dobavljaca
- link na originalni EJN zapis
- CSV uvoz, CSV sablon i izvoz trenutno filtriranih rezultata
- SQLite baza sa indeksima i zastitom od tipicnih duplikata
- kategorije su podaci, a ne programska logika: dodavanje novih oblasti ne zahtijeva novu aplikaciju

## Pokretanje
```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python app.py
```
Otvoriti `http://SERVER:8099/`.

## Predlozene zdravstvene kategorije
Lijekovi; Medicinska oprema; Medicinska pomagala; Medicinski potrosni materijal; Laboratorija i reagensi; Stomatologija; Servis i odrzavanje medicinske opreme; Ostalo zdravstvo.

## EJN ETL
Ova verzija namjerno odvaja **aplikaciju/bazu** od **ETL konektora**. Konektor treba koristiti javni/Open Data izvor ili ovlasteni pristup EJN-u, bez zaobilazenja CAPTCHA, prijave ili drugih kontrola. Nakon sto utvrdimo tacan format izvora, ETL puni istu tabelu `ugovori`, pa UI ostaje isti za svaku kategoriju.

Za produkciju: staviti iza nginx/Caddy, ukljuciti autentikaciju za `/import`, redovan backup SQLite baze (ili preci na PostgreSQL za veci obim) i dnevni ETL preko cron/systemd timera.
