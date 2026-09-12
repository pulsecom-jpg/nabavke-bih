import csv, io, os, sqlite3
from flask import Flask, request, Response, render_template_string, redirect
app=Flask(__name__); DB=os.getenv('DB','nabavke.db')

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
 c=db(); c.executescript('''
 CREATE TABLE IF NOT EXISTS ugovori(
 id INTEGER PRIMARY KEY, datum TEXT, godina INTEGER, mjesec INTEGER,
 ustanova TEXT, tip_ustanove TEXT, grad TEXT, kanton_regija TEXT,
 predmet TEXT, opis TEXT, kategorija TEXT, podkategorija TEXT, cpv TEXT,
 lot TEXT, kolicina TEXT, jedinica TEXT, dobavljac TEXT, proizvodjac TEXT, brend TEXT,
 vrijednost REAL, procijenjena_vrijednost REAL, valuta TEXT DEFAULT 'KM', broj_ponuda INTEGER,
 postupak TEXT, okvirni_sporazum TEXT, trajanje TEXT, broj_obavjestenja TEXT, status TEXT,
 izvor TEXT DEFAULT 'EJN', ejn_url TEXT, datum_uvoza TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(broj_obavjestenja,lot,dobavljac,predmet,datum));
 CREATE TABLE IF NOT EXISTS kategorije(id INTEGER PRIMARY KEY,naziv TEXT UNIQUE,cpv_prefiksi TEXT,kljucne_rijeci TEXT);
 CREATE INDEX IF NOT EXISTS idx_datum ON ugovori(datum); CREATE INDEX IF NOT EXISTS idx_ustanova ON ugovori(ustanova);
 CREATE INDEX IF NOT EXISTS idx_dobavljac ON ugovori(dobavljac); CREATE INDEX IF NOT EXISTS idx_cpv ON ugovori(cpv);
 CREATE INDEX IF NOT EXISTS idx_kategorija ON ugovori(kategorija); CREATE INDEX IF NOT EXISTS idx_grad ON ugovori(grad);
 '''); c.commit(); c.close()
init()

def query(sql,args=()):
 c=db(); r=c.execute(sql,args).fetchall(); c.close(); return r

def F():
 g=request.args.get; vals={k:g(k,'') for k in ['s','kategorija','podkategorija','ustanova','tip','grad','dobavljac','cpv','postupak','od','do','min','max','godina','ponude']}
 w=[]; a=[]
 if vals['s']:
  cols=['ustanova','grad','predmet','opis','dobavljac','proizvodjac','brend','lot','cpv','broj_obavjestenja']; w.append('('+' OR '.join(f'{x} LIKE ?' for x in cols)+')'); a += ['%'+vals['s']+'%']*len(cols)
 for key,col in [('kategorija','kategorija'),('podkategorija','podkategorija'),('ustanova','ustanova'),('tip','tip_ustanove'),('grad','grad'),('dobavljac','dobavljac'),('cpv','cpv'),('postupak','postupak')]:
  if vals[key]: w.append(f'{col} LIKE ?'); a.append('%'+vals[key]+'%')
 if vals['od']: w.append('datum>=?'); a.append(vals['od'])
 if vals['do']: w.append('datum<=?'); a.append(vals['do'])
 if vals['min']: w.append('vrijednost>=?'); a.append(float(vals['min']))
 if vals['max']: w.append('vrijednost<=?'); a.append(float(vals['max']))
 if vals['godina']: w.append('godina=?'); a.append(int(vals['godina']))
 if vals['ponude']=='1': w.append('broj_ponuda=1')
 return (' WHERE '+' AND '.join(w) if w else ''),a,vals

TPL='''<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Nabavke BiH</title><style>
*{box-sizing:border-box}body{font-family:Arial,sans-serif;margin:0;background:#f5f6f8;color:#3d424b}.wrap{max-width:1500px;margin:auto;padding:26px}h1{font-size:42px;margin:10px 0}.muted{color:#7b8189}.cards,.rank{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.box,form{background:#fff;border:1px solid #dfe2e6;border-radius:14px;padding:18px}.big{font-size:28px;font-weight:700;margin-top:8px}.filters{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}.filters input,.filters select{padding:11px;border:1px solid #ccd1d7;border-radius:9px;min-width:150px}.filters .search{min-width:330px}.btn{padding:11px 15px;border:0;border-radius:9px;background:#1976d2;color:white;text-decoration:none;cursor:pointer}.secondary{background:#fff;color:#1767aa;border:1px solid #9fc4e5}.chips a{display:inline-block;padding:9px 14px;margin:3px;border:1px solid #ccd1d7;border-radius:20px;text-decoration:none;color:#3d424b;background:#fff}.rank{grid-template-columns:repeat(3,1fr);margin:18px 0}.box h3{margin-top:0}.box table{font-size:13px}.scroll{overflow:auto;background:#fff;border:1px solid #dfe2e6;border-radius:14px}table{width:100%;border-collapse:collapse}th,td{padding:11px;border-bottom:1px solid #eceef0;text-align:left;vertical-align:top}th{background:#eef3f8;position:sticky;top:0;z-index:1}.money{text-align:right;font-weight:700;white-space:nowrap}.tag{font-size:11px;background:#edf1f5;padding:4px 7px;border-radius:6px;display:inline-block}.warn{background:#fdebea;color:#a33}a{color:#1767aa}.upload{margin-top:18px}@media(max-width:900px){.cards,.rank{grid-template-columns:1fr 1fr}.wrap{padding:14px}h1{font-size:30px}}@media(max-width:600px){.cards,.rank{grid-template-columns:1fr}.filters .search{min-width:100%}}
</style></head><body><div class=wrap><div class=muted>JAVNE NABAVKE BIH / UNIVERZALNI ANALITIČKI SISTEM</div><h1>Nabavke BiH</h1><p>Jedna baza za zdravstvo i druge kategorije. Filteri, rang-liste, detalji i CSV izvoz.</p>
<div class=cards><div class=card><b>UGOVORA</b><div class=big>{{stats.n}}</div></div><div class=card><b>VRIJEDNOST</b><div class=big>{{fmt(stats.total)}} KM</div></div><div class=card><b>USTANOVA</b><div class=big>{{stats.inst}}</div></div><div class=card><b>DOBAVLJAČA</b><div class=big>{{stats.sup}}</div></div></div>
<div class=chips><a href="/?{{keep('kategorija','')}}">Sve</a>{% for x in cats %}<a href="/?{{keep('kategorija',x[0])}}">{{x[0]}}</a>{% endfor %}<a href="/?{{keep('ponude','1')}}">Samo 1 ponuda</a></div>
<form class=filters><input class=search name=s value="{{v.s}}" placeholder="Traži: ustanova, grad, predmet, lijek, dobavljač, CPV..."><input name=ustanova value="{{v.ustanova}}" placeholder="Ustanova"><input name=grad value="{{v.grad}}" placeholder="Grad"><input name=dobavljac value="{{v.dobavljac}}" placeholder="Dobavljač"><input name=cpv value="{{v.cpv}}" placeholder="CPV/JRJN"><input name=postupak value="{{v.postupak}}" placeholder="Postupak"><select name=godina><option value="">Sve godine</option>{% for y in years %}<option {{'selected' if v.godina==y|string else ''}}>{{y}}</option>{% endfor %}</select><input type=date name=od value="{{v.od}}"><input type=date name=do value="{{v.do}}"><input type=number step=.01 name=min value="{{v.min}}" placeholder="min KM"><input type=number step=.01 name=max value="{{v.max}}" placeholder="max KM"><button class=btn>Filtriraj</button><a class="btn secondary" href="/">Reset</a><a class=btn href="/export?{{qs}}">CSV</a></form>
<div class=rank><div class=box><h3>Ustanove</h3><table>{% for r in topi %}<tr><td><a href="/?ustanova={{r.name|urlencode}}">{{r.name}}</a></td><td>{{r.n}}</td><td class=money>{{fmt(r.total)}}</td></tr>{% endfor %}</table></div><div class=box><h3>Dobavljači</h3><table>{% for r in tops %}<tr><td><a href="/?dobavljac={{r.name|urlencode}}">{{r.name}}</a></td><td>{{r.n}}</td><td class=money>{{fmt(r.total)}}</td></tr>{% endfor %}</table></div><div class=box><h3>Gradovi</h3><table>{% for r in topg %}<tr><td><a href="/?grad={{r.name|urlencode}}">{{r.name}}</a></td><td>{{r.n}}</td><td class=money>{{fmt(r.total)}}</td></tr>{% endfor %}</table></div></div>
<div class=scroll><table><tr><th>Ugovoreno</th><th>Ustanova / grad</th><th>Predmet / dobavljač</th><th>Kategorija / CPV / LOT</th><th>Vrijednost</th><th>Ponude</th><th>Postupak</th><th>Izvor</th></tr>{% for r in rows %}<tr><td>{{r.datum or ''}}</td><td><b>{{r.ustanova or ''}}</b><br><span class=muted>{{r.tip_ustanove or ''}} · {{r.grad or ''}}</span></td><td><b>{{r.predmet or ''}}</b>{% if r.opis %}<br><span class=muted>{{r.opis[:160]}}</span>{% endif %}<br>Dobavljač: <b>{{r.dobavljac or ''}}</b>{% if r.proizvodjac %}<br>Proizvođač: {{r.proizvodjac}}{% endif %}</td><td><span class=tag>{{r.kategorija or 'Nerazvrstano'}}</span>{% if r.podkategorija %} <span class=tag>{{r.podkategorija}}</span>{% endif %}<br>{{r.cpv or ''}}{% if r.lot %}<br>LOT: {{r.lot}}{% endif %}</td><td class=money>{{fmt(r.vrijednost)}} KM{% if r.procijenjena_vrijednost %}<br><small>procj. {{fmt(r.procijenjena_vrijednost)}}</small>{% endif %}</td><td>{% if r.broj_ponuda==1 %}<span class="tag warn">1 ponuda</span>{% else %}{{r.broj_ponuda or ''}}{% endif %}</td><td>{{r.postupak or ''}}</td><td>{% if r.ejn_url %}<a target=_blank href="{{r.ejn_url}}">EJN</a>{% endif %}<br><small>{{r.broj_obavjestenja or ''}}</small></td></tr>{% endfor %}</table></div>
<div class="box upload"><h3>Uvoz podataka</h3><p>CSV može sadržati bilo koji podskup kolona iz baze. Sistem je generički: kategorije nisu hardkodirane.</p><form action=/import method=post enctype=multipart/form-data><input type=file name=file accept=.csv required><button class=btn>Uvezi CSV</button> <a href=/template.csv>Preuzmi CSV šablon</a></form></div></div></body></html>'''

def fmt(x):
 try:return f'{float(x or 0):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
 except:return '0,00'

def keep(k,val):
 d=request.args.to_dict(); d[k]=val
 from urllib.parse import urlencode
 return urlencode({a:b for a,b in d.items() if b!=''})
@app.template_filter('urlencode')
def ue(s):
 from urllib.parse import quote_plus
 return quote_plus(str(s))

@app.route('/')
def home():
 w,a,v=F(); stats=query('SELECT count(*) n,coalesce(sum(vrijednost),0) total,count(distinct ustanova) inst,count(distinct dobavljac) sup FROM ugovori'+w,a)[0]
 rows=query('SELECT * FROM ugovori'+w+' ORDER BY datum DESC,id DESC LIMIT 5000',a)
 def top(col): return query(f"SELECT {col} name,count(*) n,coalesce(sum(vrijednost),0) total FROM ugovori{w + (' AND ' if w else ' WHERE ')}{col} IS NOT NULL AND {col}<>'' GROUP BY {col} ORDER BY total DESC LIMIT 12",a)
 cats=query("SELECT kategorija,count(*) FROM ugovori WHERE kategorija IS NOT NULL AND kategorija<>'' GROUP BY kategorija ORDER BY 2 DESC")
 years=[r[0] for r in query('SELECT DISTINCT godina FROM ugovori WHERE godina IS NOT NULL ORDER BY godina DESC')]
 return render_template_string(TPL,stats=stats,rows=rows,topi=top('ustanova'),tops=top('dobavljac'),topg=top('grad'),cats=cats,years=years,v=v,fmt=fmt,keep=keep,qs=request.query_string.decode())

COLS=['datum','godina','mjesec','ustanova','tip_ustanove','grad','kanton_regija','predmet','opis','kategorija','podkategorija','cpv','lot','kolicina','jedinica','dobavljac','proizvodjac','brend','vrijednost','procijenjena_vrijednost','valuta','broj_ponuda','postupak','okvirni_sporazum','trajanje','broj_obavjestenja','status','izvor','ejn_url']
@app.route('/template.csv')
def template(): return Response(','.join(COLS)+'\n',mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=nabavke_template.csv'})
@app.post('/import')
def imp():
 f=request.files['file']; text=io.TextIOWrapper(f.stream,encoding='utf-8-sig'); rd=csv.DictReader(text); c=db(); n=0
 for r in rd:
  data={k:(r.get(k) or '').strip() for k in COLS}
  if data['datum'] and not data['godina']:
   try:data['godina']=int(data['datum'][:4]); data['mjesec']=int(data['datum'][5:7])
   except:pass
  for k in ['vrijednost','procijenjena_vrijednost']:
   try:data[k]=float(str(data[k]).replace('.','').replace(',','.')) if data[k] else None
   except:data[k]=None
  for k in ['godina','mjesec','broj_ponuda']:
   try:data[k]=int(data[k]) if data[k] else None
   except:data[k]=None
  cols=[k for k in COLS if data[k] not in ('',None)]; vals=[data[k] for k in cols]
  if cols:
   c.execute('INSERT OR IGNORE INTO ugovori('+','.join(cols)+') VALUES('+','.join('?'*len(cols))+')',vals); n+=1
 c.commit(); c.close(); return redirect('/?s=')
@app.route('/export')
def export():
 w,a,_=F(); rows=query('SELECT '+','.join(COLS)+' FROM ugovori'+w+' ORDER BY datum DESC',a); out=io.StringIO(); wr=csv.writer(out); wr.writerow(COLS); [wr.writerow(tuple(r)) for r in rows]; return Response('\ufeff'+out.getvalue(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=nabavke_filtrirano.csv'})
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','8099')),debug=False)
