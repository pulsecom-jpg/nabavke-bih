#!/usr/bin/env python3
"""
Generiše statične HTML izvještaje (jedan po kategoriji + zajednički index)
iz podataka prikupljenih pomoću fetch.py.

Pokretanje:
    python report.py

Izlaz:
    output/index.html
    output/<kategorija>.html
    output/<kategorija>.csv
"""
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config", "categories.json")
DATA_DIR = os.path.join(HERE, "data")
OUTPUT_DIR = os.path.join(HERE, "output")

MJESECI = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "avg",
           "sep", "okt", "nov", "dec"]


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def fmt_money(value: float) -> str:
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_stats(rows: list[dict]) -> dict:
    by_year = defaultdict(lambda: {"count": 0, "value": 0.0})
    by_month = defaultdict(int)  # "2024-11" -> count

    for r in rows:
        dt = parse_dt(r.get("ContractDate") or r.get("Announced"))
        if not dt:
            continue
        year = dt.year
        value = r.get("Value") or 0
        by_year[year]["count"] += 1
        by_year[year]["value"] += value
        by_month[f"{year}-{dt.month:02d}"] += 1

    top_months = sorted(by_month.items(), key=lambda kv: kv[1], reverse=True)[:2]

    return {
        "by_year": dict(sorted(by_year.items())),
        "top_months": top_months,
        "total_count": len(rows),
        "total_value": sum((r.get("Value") or 0) for r in rows),
    }


CARD_CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       background:#f5f6f8; color:#111; margin:0; padding:24px; }
.wrap { max-width: 980px; margin: 0 auto; }
.nav { margin-bottom: 20px; }
.nav a { display:inline-block; padding:8px 16px; margin-right:8px;
         border-radius:20px; background:#fff; border:1px solid #ddd;
         text-decoration:none; color:#333; font-weight:600; font-size:14px;}
.nav a.active { background:#2563eb; color:#fff; border-color:#2563eb; }
h1 { font-size: 30px; margin: 8px 0 12px; }
.lead { color:#444; font-size:15px; line-height:1.5; max-width: 760px;}
.updated { color:#666; font-size:13px; margin: 16px 0 24px; }
.updated a { color:#2563eb; text-decoration:none; font-weight:600; }
.cards { display:flex; gap:16px; flex-wrap:wrap; }
.card { background:#fff; border-radius:12px; padding:18px 20px; flex:1;
        min-width: 220px; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
.card .label { font-size:12px; letter-spacing:.06em; color:#888; font-weight:700;
               text-transform:uppercase; }
.card .big { font-size:34px; font-weight:800; margin:8px 0 4px; }
.card .sub { font-size:13px; color:#555; }
table { width:100%; border-collapse:collapse; margin-top: 24px; background:#fff;
        border-radius:12px; overflow:hidden; }
th, td { padding:10px 12px; text-align:left; font-size:13px; border-bottom:1px solid #eee; }
th { background:#fafafa; color:#555; text-transform:uppercase; font-size:11px; }
"""


def render_category_html(key: str, cfg: dict, stats: dict, categories: dict) -> str:
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y. u %H:%M")

    nav_links = "".join(
        f'<a href="{k}.html" class="{"active" if k == key else ""}">{c["title"].split(",")[0]}</a>'
        for k, c in categories.items()
    )

    year_cards = ""
    years = sorted(stats["by_year"].keys(), reverse=True)
    for y in years[:2]:
        d = stats["by_year"][y]
        year_cards += f"""
        <div class="card">
          <div class="label">{y} / UGOVORA</div>
          <div class="big">{d['count']}</div>
          <div class="sub">ukupno {fmt_money(d['value'])} KM bez PDV</div>
        </div>"""

    top_months_str = " i ".join(m.split("-")[1] for m, _ in stats["top_months"])
    top_months_detail = "<br>".join(
        f"{MJESECI[int(m.split('-')[1]) - 1]} {m.split('-')[0]}: {c} ugovora"
        for m, c in stats["top_months"]
    )

    return f"""<!doctype html>
<html lang="bs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['title']}</title>
<style>{CARD_CSS}</style>
</head><body><div class="wrap">
  <div class="nav">{nav_links}</div>
  <h1>{cfg['title']}</h1>
  <p class="lead">{cfg['description']} Objavljeni na Portalu javnih nabavki BiH
     (ejn.gov.ba, open data API) od 1.1.2024. do danas. Vrijednosti su bez PDV-a, u KM.</p>
  <div class="updated">
    Osvježeno {now_str} · automatski svaki dan ·
    <a href="{key}.csv">preuzmi CSV</a>
  </div>
  <div class="cards">
    {year_cards}
    <div class="card">
      <div class="label">UKUPNO (SVI PODACI)</div>
      <div class="big">{stats['total_count']}</div>
      <div class="sub">ukupno {fmt_money(stats['total_value'])} KM bez PDV</div>
    </div>
    <div class="card">
      <div class="label">NAJJAČI MJESECI</div>
      <div class="big" style="font-size:22px">{top_months_str}</div>
      <div class="sub">{top_months_detail}</div>
    </div>
  </div>
</div></body></html>"""


def render_index_html(categories: dict) -> str:
    links = "".join(
        f'<div class="card"><div class="label">{c["title"]}</div>'
        f'<div class="sub"><a href="{k}.html">Otvori izvještaj →</a></div></div>'
        for k, c in categories.items()
    )
    return f"""<!doctype html>
<html lang="bs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Javne nabavke BiH - izvještaji</title>
<style>{CARD_CSS}</style>
</head><body><div class="wrap">
  <h1>Izvještaji o javnim nabavkama BiH</h1>
  <div class="cards" style="flex-direction:column">{links}</div>
</div></body></html>"""


def write_csv(path: str, rows: list[dict]):
    if not rows:
        return
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    categories = load_json(CONFIG_PATH, {})

    for key, cfg in categories.items():
        rows = list(load_json(os.path.join(DATA_DIR, f"{key}.json"), {}).values())
        stats = compute_stats(rows)
        html = render_category_html(key, cfg, stats, categories)
        with open(os.path.join(OUTPUT_DIR, f"{key}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        write_csv(os.path.join(OUTPUT_DIR, f"{key}.csv"), rows)
        print(f"[{key}] izvještaj generisan ({stats['total_count']} ugovora)")

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_index_html(categories))
    print("index.html generisan")


if __name__ == "__main__":
    main()
