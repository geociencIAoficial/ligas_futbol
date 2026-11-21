#!/usr/bin/env python3
"""Selecciones nacionales masculinas: ranking, ficha y cara a cara.

    python selecciones.py nacionales      # crea docs/sel/ (un JSON por selección + agregado.json)

Fuente: github.com/martj42/international_results (licencia CC0): resultados de selecciones
desde 1872 (Mundiales, eliminatorias, copas, Nations League, amistosos y otros torneos).
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata

import requests

import selecciones as S

BASE = "https://raw.githubusercontent.com/martj42/international_results/master/"
GRUPOS = ["Mundial", "Eliminatorias mundialistas", "Copas continentales", "Eliminatorias continentales",
          "Nations League", "Amistosos", "Otros torneos"]
CONT = re.compile(r"^(UEFA Euro|Copa América|African Cup of Nations|AFC Asian Cup|CONCACAF Championship"
                  r"|Gold Cup|Oceania Nations Cup|Confederations Cup)$")
# Torneos que solo juegan los miembros de la confederación (los invitados a copas no cuentan)
MARCAS = [("UEFA Euro", "UEFA"), ("UEFA Nations League", "UEFA"), ("African Cup of Nations", "CAF"),
          ("AFC Asian Cup", "AFC"), ("CONCACAF", "CONCACAF"), ("Gold Cup", "CONCACAF"),
          ("CFU Caribbean Cup", "CONCACAF"), ("Oceania Nations Cup", "OFC")]


def conf_de(t: str):
    if not (t.endswith(" qualification") or "Nations League" in t or t.startswith("Oceania Nations Cup")):
        return None
    return next((conf for clave, conf in MARCAS if clave in t), None)


ES = """Mexico=México;United States=Estados Unidos;Spain=España;Germany=Alemania;France=Francia;Brazil=Brasil;
England=Inglaterra;Netherlands=Países Bajos;Belgium=Bélgica;Croatia=Croacia;Switzerland=Suiza;Denmark=Dinamarca;
Japan=Japón;South Korea=Corea del Sur;North Korea=Corea del Norte;Saudi Arabia=Arabia Saudita;Iran=Irán;Iraq=Irak;
Qatar=Catar;Morocco=Marruecos;Egypt=Egipto;Tunisia=Túnez;Algeria=Argelia;South Africa=Sudáfrica;
Ivory Coast=Costa de Marfil;Cameroon=Camerún;Canada=Canadá;Panama=Panamá;Haiti=Haití;Curaçao=Curazao;Peru=Perú;
Czech Republic=Chequia;Poland=Polonia;Sweden=Suecia;Norway=Noruega;Finland=Finlandia;Greece=Grecia;Turkey=Turquía;
Scotland=Escocia;Wales=Gales;Northern Ireland=Irlanda del Norte;Republic of Ireland=Irlanda;Hungary=Hungría;
Romania=Rumania;Slovakia=Eslovaquia;Slovenia=Eslovenia;Ukraine=Ucrania;Russia=Rusia;Italy=Italia;Iceland=Islandia;
Bosnia and Herzegovina=Bosnia y Herzegovina;North Macedonia=Macedonia del Norte;Azerbaijan=Azerbaiyán;
Kazakhstan=Kazajistán;Uzbekistan=Uzbekistán;Jordan=Jordania;Syria=Siria;Lebanon=Líbano;China PR=China;
New Zealand=Nueva Zelanda;Cape Verde=Cabo Verde;DR Congo=RD del Congo;Gabon=Gabón;Mali=Malí;Ethiopia=Etiopía;
Sudan=Sudán;Libya=Libia;Dominican Republic=República Dominicana;Trinidad and Tobago=Trinidad y Tobago;
Suriname=Surinam;Thailand=Tailandia;Palestine=Palestina;Oman=Omán;Bahrain=Baréin;
United Arab Emirates=Emiratos Árabes Unidos;Philippines=Filipinas;Malaysia=Malasia;Singapore=Singapur;
Luxembourg=Luxemburgo;Cyprus=Chipre;Latvia=Letonia;Lithuania=Lituania;Belarus=Bielorrusia;Faroe Islands=Islas Feroe;
Belize=Belice;Germany DR=Alemania Oriental;German DR=Alemania Oriental;Yugoslavia=Yugoslavia;Czechoslovakia=Checoslovaquia;
Eswatini=Esuatini;Equatorial Guinea=Guinea Ecuatorial;Ghana=Ghana;Jamaica=Jamaica;Kenya=Kenia;Tanzania=Tanzania"""
ESD = dict(x.strip().split("=", 1) for x in ES.replace("\n", "").split(";") if "=" in x)


# nombre del archivo de resultados -> nombre en el mapa base (Natural Earth, vía world-atlas)
ALIAS = dict(x.split("=") for x in """United States=United States of America;Ivory Coast=Côte d'Ivoire;Republic of Ireland=Ireland;
Éire=Ireland;Czech Republic=Czechia;Czechoslovakia=Czechia;DR Congo=Dem. Rep. Congo;Zaïre=Dem. Rep. Congo;
Congo-Kinshasa=Dem. Rep. Congo;North Macedonia=Macedonia;Yugoslavia=Serbia;FR Yugoslavia=Serbia;German DR=Germany;
Soviet Union=Russia;Faroe Islands=Faeroe Is.;Saint Kitts and Nevis=St. Kitts and Nevis;Bosnia and Herzegovina=Bosnia and Herz.;
Antigua and Barbuda=Antigua and Barb.;Saint Vincent and the Grenadines=St. Vin. and Gren.;Solomon Islands=Solomon Is.;
Cape Verde=Cabo Verde;Equatorial Guinea=Eq. Guinea;Dominican Republic=Dominican Rep.;Eswatini=eSwatini;Swaziland=eSwatini;
Cayman Islands=Cayman Is.;Macau=Macao;Central African Republic=Central African Rep.;British Virgin Islands=British Virgin Is.;
United States Virgin Islands=U.S. Virgin Is.;South Sudan=S. Sudan;São Tomé and Príncipe=São Tomé and Principe;
Northern Cyprus=N. Cyprus;Turks and Caicos Islands=Turks and Caicos Is.;Cook Islands=Cook Is.;Burma=Myanmar;
Western Samoa=Samoa;Tanganyika=Tanzania;Åland Islands=Åland;Upper Volta=Burkina Faso;Dahomey=Benin;
Southern Rhodesia=Zimbabwe;Northern Rhodesia=Zambia;Malaya=Malaysia;Dutch Guyana=Suriname;British Guiana=Guyana;
Vietnam Republic=Vietnam;North Vietnam=Vietnam;Yemen DPR=Yemen;United Arab Republic=Egypt;
Northern Mariana Islands=N. Mariana Is.;Falkland Islands=Falkland Is.;Wallis Islands and Futuna=Wallis and Futuna Is.;
Saint Martin=St-Martin;Saint Barthélemy=St-Barthélemy;Tahiti=Fr. Polynesia;Saint Pierre and Miquelon=St. Pierre and Miquelon;
East Timor=Timor-Leste;Western Sahara=W. Sahara;Marshall Islands=Marshall Is.;Vatican City=Vatican;
Serbia and Montenegro=Serbia;Gold Coast=Ghana;Belgian Congo=Dem. Rep. Congo;Ceylon=Sri Lanka;Yemen AR=Yemen;South Yemen=Yemen;
New Hebrides=Vanuatu;Nyasaland=Malawi;Portuguese Guinea=Guinea-Bissau;French Somaliland=Djibouti;Irish Free State=Ireland;
Mandatory Palestine=Palestine;Bohemia and Moravia=Czechia;Bohemia=Czechia;Ellan Vannin=Isle of Man;Parishes of Jersey=Jersey""".replace("\n", "").split(";"))
# entidades que no están en el mapa base: [lon, lat]
EXTRA = {"England": [-1.5, 52.8], "Scotland": [-4.2, 56.9], "Wales": [-3.7, 52.3], "Northern Ireland": [-6.7, 54.6],
         "Martinique": [-61, 14.65], "Guadeloupe": [-61.55, 16.25], "French Guiana": [-53.1, 3.9],
         "Réunion": [55.5, -21.1], "Mayotte": [45.15, -12.8], "Bonaire": [-68.25, 12.2], "Zanzibar": [39.2, -6.1],
         "Gibraltar": [-5.35, 36.14], "Alderney": [-2.2, 49.7], "Shetland": [-1.3, 60.3], "Orkney": [-3, 59],
         "Western Isles": [-7, 57.8], "Isle of Wight": [-1.3, 50.7], "Ynys Môn": [-4.4, 53.3],
         "Basque Country": [-2.2, 43], "Catalonia": [1.5, 41.8], "Occitania": [2, 43.5], "Padania": [10, 45],
         "Raetia": [9.5, 46.7], "Sápmi": [24, 68.5], "Gotland": [18.5, 57.5], "Frøya": [8.7, 63.7],
         "Saare County": [22.5, 58.4], "Menorca": [4.1, 39.95], "Abkhazia": [41, 43], "Tamil Eelam": [80.5, 9],
         "Iraqi Kurdistan": [44, 36], "Székely Land": [25.5, 46.3], "Western Australia": [122, -26],
         "Tuvalu": [179.2, -8.5], "Chagos Islands": [72.4, -7.3], "Canary Islands": [-15.6, 28.3], "Corsica": [9.1, 42.1],
         "Gozo": [14.25, 36.05], "Rhodes": [28, 36.2], "Sark": [-2.37, 49.43], "Tibet": [88, 31.5], "Yorkshire": [-1.3, 54],
         "Kernow": [-4.9, 50.3], "Madrid": [-3.7, 40.4], "Galicia": [-8, 42.8], "Asturias": [-5.9, 43.3],
         "Andalusia": [-4.5, 37.4], "Saarland": [6.95, 49.4], "Silesia": [17.5, 50.9], "Provence": [6, 43.9],
         "Brittany": [-3, 48.2], "Franconia": [10.5, 49.7], "Surrey": [-0.4, 51.3], "Quebec": [-72, 52]}


def grupo(t: str) -> int:
    if t == "FIFA World Cup":
        return 0
    if t == "FIFA World Cup qualification":
        return 1
    if "Nations League" in t:
        return 4
    if CONT.match(t):
        return 2
    if t.endswith(" qualification") and CONT.match(t[:-len(" qualification")]):
        return 3
    return 5 if t == "Friendly" else 6


def k_de(t: str) -> int:
    """Factor K del Elo de selecciones (eloratings.net)."""
    if t == "FIFA World Cup":
        return 60
    if CONT.match(t):
        return 50
    if t == "Friendly":
        return 20
    return 40 if (t.endswith("qualification") or "Nations League" in t) else 30


def _csv(nombre: str) -> list[dict]:
    r = requests.get(BASE + nombre, headers={"User-Agent": "SeleccionesDB/0.3"}, timeout=120)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def _slug(n: str, usados: dict) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()).strip("-")
    s = s or "x"
    base, k = s, 2
    while s in usados and usados[s] != n:
        s, k = f"{base}-{k}", k + 1
    usados[s] = n
    return s


def cmd_nacionales(args):
    res = _csv("results.csv")
    pen = {(r["date"], r["home_team"], r["away_team"]): r["winner"] for r in _csv("shootouts.csv")}
    ya = int(max(r["date"] for r in res)[:4])
    reciente = (ya - 3) * 10000 + 101
    gs, gr = {}, {}
    for r in _csv("goalscorers.csv"):
        if r["own_goal"] == "TRUE" or not r["scorer"]:
            continue
        d = int(r["date"].replace("-", ""))
        for dic in ([gs, gr] if d >= reciente else [gs]):
            v = dic.setdefault(r["team"], {}).setdefault(r["scorer"], [0, 0, d // 10000, d // 10000])
            v[0] += 1
            v[1] += r["penalty"] == "TRUE"
            v[2], v[3] = min(v[2], d // 10000), max(v[3], d // 10000)

    def top(dic, n):
        return [[k] + v for k, v in sorted(dic.items(), key=lambda kv: -kv[1][0])[:n]]
    elo: dict = {}
    paises: dict = {}
    usados: dict = {}
    eq: dict = {}
    res.sort(key=lambda r: r["date"])
    for r in res:
        if not r["home_score"] or not r["away_score"]:
            continue
        t, f = r["tournament"], r["date"]
        g, neutral = grupo(t), r["neutral"] == "TRUE"
        gl, gv = int(r["home_score"]), int(r["away_score"])
        ganador = pen.get((f, r["home_team"], r["away_team"]))
        h, a_ = r["home_team"], r["away_team"]
        dif = elo.get(h, 1500) - elo.get(a_, 1500) + (0 if neutral else 100)
        d = abs(gl - gv)
        delta = k_de(t) * (1 if d <= 1 else 1.5 if d == 2 else (11 + d) / 8) * (
            (1 if gl > gv else .5 if gl == gv else 0) - 1 / (10 ** (-dif / 400) + 1))
        elo[h], elo[a_] = elo.get(h, 1500) + delta, elo.get(a_, 1500) - delta
        for yo, rival, a, b, sede in ((r["home_team"], r["away_team"], gl, gv, 2 if neutral else 0),
                                      (r["away_team"], r["home_team"], gv, gl, 2 if neutral else 1)):
            e = eq.setdefault(yo, {"m": [], "y": {}, "t": {}, "mk": {}, "copa": False, "mx": [0, 0], "last": 0})
            ti = e["t"].setdefault(t, len(e["t"]))
            p = -1 if not ganador else int(ganador == yo)
            fi = int(f.replace("-", ""))
            e["m"].append([fi, _slug(rival, usados), a, b, ti, sede, r["city"], p, round(elo[yo]), paises.setdefault(r["country"], len(paises))])
            if elo[yo] > e["mx"][0]:
                e["mx"] = [round(elo[yo]), fi]
            e["last"] = fi
            v = e["y"].setdefault(f[:4], {}).setdefault(str(g), [0] * 6)
            v[0] += 1
            v[1 if a > b else 3 if a < b else 2] += 1
            v[4] += a
            v[5] += b
            conf = conf_de(t)
            if conf:
                e["mk"][conf] = max(e["mk"].get(conf, ""), f)
            e["copa"] = e["copa"] or t == "Copa América"
    out = S.BASE_DIR / "docs" / "sel"
    out.mkdir(parents=True, exist_ok=True)
    agg = {}
    for n, e in eq.items():
        s = _slug(n, usados)
        conf = max(e["mk"], key=e["mk"].get) if e["mk"] else ("CONMEBOL" if e["copa"] else "Otros")
        agg[s] = [n, ESD.get(n, ""), conf, e["y"], round(elo[n]), e["mx"], e["last"]]
        tn = [[nom, grupo(nom)] for nom in e["t"]]
        e["m"].sort()
        (out / f"{s}.json").write_text(json.dumps({"n": n, "t": tn, "m": e["m"], "g": top(gs.get(n, {}), 15), "gr": top(gr.get(n, {}), 10)}, ensure_ascii=False,
                                                  separators=(",", ":")), "utf-8")
    ultimo = max(r["date"] for r in res)
    (out / "agregado.json").write_text(json.dumps(
        {"f": ultimo, "ya": ya, "g": GRUPOS, "t": agg, "P": list(paises)}, ensure_ascii=False, separators=(",", ":")), "utf-8")
    mapa = S.BASE_DIR / "mapa_mundo.json"
    if mapa.exists():
        m = json.loads(mapa.read_text("utf-8"))
        nombres = set(agg_n for agg_n in eq) | set(paises)
        pos = {n: EXTRA.get(n) or m["c"].get(ALIAS.get(n, n)) for n in nombres}
        sin = sorted(n for n, v in pos.items() if not v)
        (out / "mapa.json").write_text(json.dumps({"b": m["b"], "p": {n: v for n, v in pos.items() if v}},
                                                  ensure_ascii=False, separators=(",", ":")), "utf-8")
        print(f"Mapa: {len(nombres) - len(sin)} lugares con coordenadas; sin coordenadas: {', '.join(sin) or 'ninguno'}")
    else:
        print("Falta mapa_mundo.json: la vista Mapa no tendrá datos.")
    print(f"Listo: {out}/  ({len(agg)} selecciones, {len(res)} partidos, datos al {ultimo})")


UI_BTN = '<button data-t="3" aria-pressed="false">Selecciones</button>'
UI_HTML = r"""<div id="v3" class="hide">
<nav class="seg" id="sv"><button data-sv="r" aria-pressed="true">Ranking</button><button data-sv="e" aria-pressed="false">Elo</button><button data-sv="f" aria-pressed="false">Ficha</button><button data-sv="h" aria-pressed="false">Cara a cara</button><button data-sv="m" aria-pressed="false">Mapa</button></nav>
<div id="sc3"></div>
<small>Selecciones masculinas, desde 1872. Datos: github.com/martj42/international_results (CC0).</small></div>"""
UI_JS = r"""<style>#sv{margin:4px 0 12px}.fc{display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;border-radius:5px;color:#fff;font-weight:700;margin-right:3px}.fg{background:var(--acc)}.fe{background:#8a8f94}.fp{background:#c2483f}.kp{display:flex;gap:18px;flex-wrap:wrap;margin:8px 0}.kp b{display:block;font-size:20px}a.ft{color:var(--acc);cursor:pointer;text-decoration:underline}</style>
<script>
const SL={d:null,v:'r',slug:'mexico',b:'argentina',cache:{},
 r:{conf:'',g:'t',d:0,h:0,min:10,q:'',sort:'rend',dir:-1},f:{g:'t',q:'',d:1872,h:9999,s:'',n:100},hh:{g:'t',n:100},e:{conf:'',act:true,q:''},m:{modo:'s',g:'t',d:1872,h:9999},mapa:null,mA:{}};
const GO=[['t','Todas'],['o','Oficiales'],['0','Mundial'],['1','Eliminatorias mundialistas'],['2','Copas continentales'],['3','Eliminatorias continentales'],['4','Nations League'],['5','Amistosos'],['6','Otros torneos']];
const okG=(g,s)=>s==='t'||(s==='o'?g<5:+s===g),nm=t=>t[1]||t[0],fx=n=>String(n);
const fecha=n=>{const s=fx(n);return s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6)};
function selInit(){if(SL.d)return;$('sc3').innerHTML='<p class="vac">Cargando…</p>';
 fetch('sel/agregado.json').then(r=>{if(!r.ok)throw 0;return r.json()}).then(d=>{SL.d=d;SL.r.d=d.ya-3;SL.r.h=d.ya;SL.f.h=d.ya;
  SL.o=Object.entries(d.t).map(([s,t])=>[s,nm(t)]).sort((a,b)=>a[1].localeCompare(b[1]));
  if(!d.t[SL.slug])SL.slug=SL.o[0][0];if(!d.t[SL.b])SL.b=SL.o[1][0];
  const c=$('v3');c.addEventListener('click',selClick);c.addEventListener('change',selChange);c.addEventListener('input',selChange);selDraw()})
 .catch(()=>{$('sc3').innerHTML='<p class="vac">Aún no hay datos de selecciones. Corre «python selecciones.py nacionales» y publica la carpeta docs.</p>'})}
function load(s){return SL.cache[s]?Promise.resolve(SL.cache[s]):fetch('sel/'+s+'.json').then(r=>r.json()).then(j=>SL.cache[s]=j)}
const so=(id,v)=>`<select id="${id}">${SL.o.map(o=>`<option value="${o[0]}"${o[0]===v?' selected':''}>${o[1]}</option>`).join('')}</select>`;
const go=(id,v)=>`<select id="${id}">${GO.map(o=>`<option value="${o[0]}"${o[0]===v?' selected':''}>${o[1]}</option>`).join('')}</select>`;
function selDraw(){document.querySelectorAll('#sv button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.sv===SL.v));
 const r=SL.r,f=SL.f,h=SL.hh,cf=[...new Set(Object.values(SL.d.t).map(t=>t[2]))].sort();let c='';
 if(SL.v==='r')c=`<div class="card"><div class="row" style="margin:0"><label>Confederación <select id="rc"><option value="">Todas</option>${cf.map(x=>`<option${x===r.conf?' selected':''}>${x}</option>`).join('')}</select></label>
  <label>Competición ${go('rg',r.g)}</label><label>Desde <input id="rd" type="number" value="${r.d}"></label><label>Hasta <input id="rh" type="number" value="${r.h}"></label>
  <label>Mín. partidos <input id="rm" type="number" min="1" value="${r.min}"></label><label>Buscar <input id="rq" value="${r.q}"></label></div></div>`;
 if(SL.v==='f')c=`<div class="card"><div class="row" style="margin:0"><label>Selección ${so('fs',SL.slug)}</label><label>Competición ${go('fg',f.g)}</label>
  <label>Rival <input id="fq" value="${f.q}"></label><label>Desde <input id="fd" type="number" value="${f.d}"></label><label>Hasta <input id="fh" type="number" value="${f.h}"></label>
  <label>Sede <select id="fv"><option value="">Todas</option><option value="0"${f.s==='0'?' selected':''}>Local</option><option value="1"${f.s==='1'?' selected':''}>Visita</option><option value="2"${f.s==='2'?' selected':''}>Neutral</option></select></label></div></div>`;
 if(SL.v==='h')c=`<div class="card"><div class="row" style="margin:0"><label>${so('ha',SL.slug)}</label><label>contra ${so('hb',SL.b)}</label><label>Competición ${go('hg',h.g)}</label></div></div>`;
 if(SL.v==='m'){const m=SL.m;c=`<div class="card"><div class="row" style="margin:0"><label>Selección ${so('ms',SL.slug)}</label>
  <label>Ver <select id="mm"><option value="s"${m.modo==='s'?' selected':''}>Dónde jugó (sedes)</option><option value="r"${m.modo==='r'?' selected':''}>Contra quién (país del rival)</option></select></label>
  <label>Competición ${go('mg',m.g)}</label><label>Desde <input id="md" type="number" value="${m.d}"></label><label>Hasta <input id="mh" type="number" value="${m.h}"></label></div></div>`}
 if(SL.v==='e'){const e=SL.e;c=`<div class="card"><div class="row" style="margin:0"><label>Confederación <select id="ec"><option value="">Todas</option>${cf.map(x=>`<option${x===e.conf?' selected':''}>${x}</option>`).join('')}</select></label>
  <label><input id="ea" type="checkbox"${e.act?' checked':''}> Solo activas (últimos 4 años)</label><label>Buscar <input id="eq" value="${e.q}"></label></div></div>`}
 $('sc3').innerHTML=c+'<div id="sres"></div>';selTab()}
function selTab(){if(SL.v==='r')rank();else if(SL.v==='e')elo();else if(SL.v==='m')Promise.all([load(SL.slug),SL.mapa?SL.mapa:fetch('sel/mapa.json').then(r=>r.ok?r.json():null).then(x=>SL.mapa=x)]).then(([j])=>mapa(j));else if(SL.v==='f')load(SL.slug).then(ficha);else Promise.all([load(SL.slug),load(SL.b)]).then(([a,b])=>h2h(a,b))}
function rank(){const r=SL.r,q=r.q.toLowerCase();let a=[];
 for(const s in SL.d.t){const t=SL.d.t[s];if(r.conf&&t[2]!==r.conf||q&&!nm(t).toLowerCase().includes(q))continue;
  const v=[0,0,0,0,0,0];for(const y in t[3]){if(y<r.d||y>r.h)continue;for(const g in t[3][y])if(okG(+g,r.g))t[3][y][g].forEach((x,i)=>v[i]+=x)}
  if(v[0]<r.min)continue;const p=3*v[1]+v[2];a.push({s,n:nm(t),c:t[2],pj:v[0],g:v[1],e:v[2],p:v[3],gf:v[4],gc:v[5],dg:v[4]-v[5],pts:p,rend:p/(3*v[0])})}
 const k=r.sort;a.sort((x,y)=>{const c=typeof x[k]==='string'?x[k].localeCompare(y[k]):x[k]-y[k];return c?c*r.dir:(y.rend-x.rend)||(y.dg-x.dg)});
 const H=[['n','#'],['n','Selección'],['c','Conf.'],['pj','PJ'],['g','G'],['e','E'],['p','P'],['gf','GF'],['gc','GC'],['dg','DG'],['pts','Pts'],['rend','Rendimiento']];
 $('sres').innerHTML=`<div class="card tw"><table><thead><tr>${H.map(([k2,t],i)=>`<th data-rs="${i?k2:'rend'}" class="${i===1?'t e1 ':''}${i===2?'t ':''}${r.sort===k2&&i?'on':''}">${t}</th>`).join('')}</tr></thead><tbody>${a.map((d,i)=>`<tr><td class="n">${i+1}</td><td class="t e1"><a class="ft" data-ft="${d.s}">${d.n}</a></td><td class="t l">${d.c}</td><td>${d.pj}</td><td>${d.g}</td><td>${d.e}</td><td>${d.p}</td><td>${d.gf}</td><td>${d.gc}</td><td>${d.dg>0?'+':''}${d.dg}</td><td><b>${d.pts}</b></td><td><span class="pb"><i style="width:${d.rend*100}%"></i></span>${(d.rend*100).toFixed(1)}%</td></tr>`).join('')}</tbody></table>${a.length?'':'<div class="vac">Ninguna selección cumple los filtros.</div>'}</div>`}
const resu=ms=>{const a=[0,0,0,0,0,0];ms.forEach(m=>{a[0]++;if(m[2]>m[3])a[1]++;else if(m[2]<m[3])a[3]++;else a[2]++;a[4]+=m[2];a[5]+=m[3]});return a};
const nrival=s=>{const t=SL.d.t[s];return t?nm(t):s};
function lista(j,ms,n,id){const sede=['L','V','N'];
 return `<div class="card tw"><table><thead><tr><th class="t">Fecha</th><th class="t">Rival</th><th style="text-align:center">Marcador</th><th class="t">Competición</th><th>Sede</th></tr></thead><tbody>${ms.slice(0,n).map(m=>`<tr><td class="t l">${fecha(m[0])}</td><td class="t"><b>${nrival(m[1])}</b></td><td class="m">${m[2]} - ${m[3]}${m[7]>=0?` <small>(pen. ${m[7]?'G':'P'})</small>`:''}</td><td class="t l">${j.t[m[4]][0]}</td><td class="l">${sede[m[5]]} ${m[6]}</td></tr>`).join('')}</tbody></table>${ms.length>n?`<div class="vac"><button data-more="${id}">Ver más (${ms.length-n})</button></div>`:''}${ms.length?'':'<div class="vac">Sin partidos con esos filtros.</div>'}</div>`}
function kp(a,nombre){return `<div class="card"><b>${nombre}</b><div class="kp"><span><b>${a[0]}</b>PJ</span><span><b>${a[1]}</b>G</span><span><b>${a[2]}</b>E</span><span><b>${a[3]}</b>P</span><span><b>${a[4]}-${a[5]}</b>Goles</span><span><b>${a[0]?(100*(3*a[1]+a[2])/(3*a[0])).toFixed(1):0}%</b>Rendimiento</span></div>`}
const lim=()=>(SL.d.ya-3)*10000+101;
function elo(){const e=SL.e,q=e.q.toLowerCase();let a=[];
 for(const s in SL.d.t){const t=SL.d.t[s];if(e.conf&&t[2]!==e.conf||e.act&&t[6]<lim()||q&&!nm(t).toLowerCase().includes(q))continue;a.push({s,n:nm(t),c:t[2],e:t[4],mx:t[5][0],my:fx(t[5][1]).slice(0,4)})}
 a.sort((x,y)=>y.e-x.e);
 $('sres').innerHTML=`<div class="card tw"><table><thead><tr><th>#</th><th class="t e1">Selección</th><th class="t">Conf.</th><th>Elo</th><th>Máximo</th><th>Año</th></tr></thead><tbody>${a.map((d,i)=>`<tr><td class="n">${i+1}</td><td class="t e1"><a class="ft" data-ft="${d.s}">${d.n}</a></td><td class="t l">${d.c}</td><td><b>${d.e}</b></td><td>${d.mx}</td><td>${d.my}</td></tr>`).join('')}</tbody></table></div>`}
function chart(ser){const all=ser.flatMap(s=>s[1]);if(!all.length)return'';
 const yf=d=>Math.floor(d/10000)+((Math.floor(d/100)%100)-1)/12,x0=Math.floor(Math.min(...ser.map(s=>s[1][0]?yf(s[1][0][0]):1e4))),x1=SL.d.ya+1,
 vs=all.map(a=>a[1]),lo=Math.floor(Math.min(...vs)/100)*100,hi=Math.ceil(Math.max(...vs)/100)*100,W=600,H=220,L=36,B=22,
 X=d=>L+(yf(d)-x0)/(x1-x0)*(W-L-8),Y=v=>8+(hi-v)/(hi-lo||1)*(H-8-B),col=['var(--acc)','#e0a81f'],st=(x1-x0)>80?20:(x1-x0)>30?10:5;
 let g='';for(let v=lo;v<=hi;v+=100)g+=`<line x1="${L}" x2="${W-8}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${L-4}" y="${Y(v)+4}" font-size="10" text-anchor="end" fill="var(--mut)">${v}</text>`;
 for(let y=Math.ceil(x0/st)*st;y<=x1;y+=st)g+=`<text x="${X(y*10000+101)}" y="${H-6}" font-size="10" text-anchor="middle" fill="var(--mut)">${y}</text>`;
 const ls=ser.map((s,i)=>`<polyline fill="none" stroke="${col[i]}" stroke-width="1.6" points="${s[1].map(a=>X(a[0]).toFixed(1)+','+Y(a[1]).toFixed(1)).join(' ')}"/>`).join('');
 return `<div>${ser.map((s,i)=>`<span style="color:${col[i]}">■ ${s[0]}</span>`).join(' ')}</div><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">${g}${ls}</svg>`}
function marcas(ms){const a=[...ms].reverse(),r={i:[0],g:[0],p:[0]},c={i:0,g:0,p:0},s={i:'',g:'',p:''};let mg=null,mp=null,pg=0,pp=0;
 a.forEach(m=>{const w=m[2]>m[3],l=m[2]<m[3],d=fecha(m[0]);
  [['i',!l],['g',w],['p',l]].forEach(([k,ok])=>{if(ok){if(!c[k])s[k]=d;c[k]++;if(c[k]>r[k][0])r[k]=[c[k],s[k],d]}else c[k]=0});
  const df=m[2]-m[3];if(!mg||df>mg[0])mg=[df,m];if(!mp||df<mp[0])mp=[df,m];if(m[7]===1)pg++;if(m[7]===0)pp++});
 const rg=x=>x[0]?`<small>${x[1]} a ${x[2]}</small>`:'',mm=x=>x?`${x[1][2]}-${x[1][3]} vs ${nrival(x[1][1])} <small>${fecha(x[1][0])}</small>`:'—';
 return `<div class="card"><b>Rachas y marcas</b> <small>(con los filtros activos)</small><div class="kp"><span><b>${r.i[0]}</b>Invicto más largo ${rg(r.i)}</span><span><b>${r.g[0]}</b>Victorias seguidas ${rg(r.g)}</span><span><b>${r.p[0]}</b>Derrotas seguidas ${rg(r.p)}</span><span><b>${c.i}</b>Invicto actual</span><span><b>${pg}-${pp}</b>Tandas de penales</span></div>
 <div>Mayor goleada: ${mm(mg&&mg[0]>0?mg:null)}</div><div>Peor derrota: ${mm(mp&&mp[0]<0?mp:null)}</div></div>`}
function goles(j){const L=(t,x)=>`<div style="flex:1;min-width:230px"><b>${t}</b><table><tbody>${(x||[]).map(g=>`<tr><td class="t">${g[0]}</td><td><b>${g[1]}</b></td><td class="l">${g[2]} pen.</td><td class="l">${g[3]===g[4]?g[3]:g[3]+'–'+g[4]}</td></tr>`).join('')}</tbody></table></div>`;
 return j.g&&j.g.length?`<div class="card tw"><b>Goleadores</b> <small>(solo los goles registrados en el archivo; no son totales oficiales)</small><div class="row">${L('Histórico',j.g)}${L('Últimos 4 años',j.gr)}</div></div>`:''}
const eser=j=>[nrival(SL.slug),j.m.map(m=>[m[0],m[8]])];
function ficha(j){const f=SL.f,q=f.q.toLowerCase();
 const ms=j.m.filter(m=>okG(j.t[m[4]][1],f.g)&&m[0]>=f.d*10000&&m[0]<=f.h*10000+1231&&(!f.s||m[5]===+f.s)&&(!q||nrival(m[1]).toLowerCase().includes(q))).reverse();
 const fm=ms.slice(0,10).map(m=>`<span class="fc ${m[2]>m[3]?'fg':m[2]<m[3]?'fp':'fe'}">${m[2]>m[3]?'G':m[2]<m[3]?'P':'E'}</span>`).join('');
 const t=SL.d.t[SL.slug],act=t[6]>=lim(),rk=Object.values(SL.d.t).filter(x=>x[6]>=lim()&&x[4]>t[4]).length+1;
 $('sres').innerHTML=kp(resu(ms),nrival(SL.slug))+`<div>Elo actual: <b>${t[4]}</b>${act?` (n.º ${rk} entre las activas)`:''} · máximo ${t[5][0]} en ${fx(t[5][1]).slice(0,4)}</div>`+(fm?`<div>Últimos 10: ${fm}</div>`:'')+'</div>'
  +`<div class="card"><b>Evolución del Elo</b>${chart([eser(j)])}</div>`+marcas(ms)+goles(j)+lista(j,ms,f.n,'f')}
function h2h(j,b){const h=SL.hh,ms=j.m.filter(m=>m[1]===SL.b&&okG(j.t[m[4]][1],h.g)).reverse(),a=resu(ms);
 $('sres').innerHTML=`<div class="card"><b>${nrival(SL.slug)} vs ${nrival(SL.b)}</b><div class="kp"><span><b>${a[0]}</b>Partidos</span><span><b>${a[1]}</b>Ganó ${nrival(SL.slug)}</span><span><b>${a[2]}</b>Empates</span><span><b>${a[3]}</b>Ganó ${nrival(SL.b)}</span><span><b>${a[4]}-${a[5]}</b>Goles</span></div></div>`
  +`<div class="card"><b>Evolución del Elo</b>${chart([eser(j),[nrival(SL.b),b.m.map(m=>[m[0],m[8]])]])}</div>`+lista(j,ms,h.n,'h')}
const hav=(a,b)=>{const r=Math.PI/180,x=Math.sin((b[1]-a[1])*r/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin((b[0]-a[0])*r/2)**2;return 12742*Math.asin(Math.sqrt(x))};
function mapa(j){const m=SL.m,mp=SL.mapa;if(!mp){$('sres').innerHTML='<p class="vac">No hay mapa publicado todavía (falta mapa_mundo.json).</p>';return}
 const t=SL.d.t[SL.slug],P=SL.d.P,home=mp.p[t[0]],A={};
 j.m.filter(x=>okG(j.t[x[4]][1],m.g)&&x[0]>=m.d*10000&&x[0]<=m.h*10000+1231).forEach(x=>{
  const k=m.modo==='r'?SL.d.t[x[1]][0]:P[x[9]],a=A[k]=A[k]||{n:k,pj:0,g:0,e:0,p:0,km:0};a.pj++;if(x[2]>x[3])a.g++;else if(x[2]<x[3])a.p++;else a.e++;
  if(m.modo==='s'&&k!==t[0]&&home&&mp.p[k])a.km+=hav(home,mp.p[k])});
 SL.mA=A;const L=Object.values(A).filter(a=>mp.p[a.n]).sort((a,b)=>b.pj-a.pj),tot=L.reduce((s,a)=>s+a.pj,0),km=L.reduce((s,a)=>s+a.km,0);
 const fuera=L.filter(a=>a.n!==t[0]).reduce((s,a)=>s+a.pj,0),far=L.filter(a=>m.modo==='s'&&home&&a.n!==t[0]).reduce((b,a)=>!b||hav(home,mp.p[a.n])>hav(home,mp.p[b.n])?a:b,null);
 const cir=[...L].reverse().map(a=>{const [lo,la]=mp.p[a.n],rd=(3*a.g+a.e)/(3*a.pj);return `<circle data-mc="${a.n}" cx="${((lo+180)*1000/360).toFixed(1)}" cy="${((84-la)*1000/360).toFixed(1)}" r="${Math.min(22,3+Math.sqrt(a.pj)*1.5).toFixed(1)}" fill="hsl(${Math.round(rd*120)},65%,45%)" fill-opacity=".72" stroke="#fff" stroke-width=".6"/>`}).join('');
 const ho=home?`<circle cx="${((home[0]+180)*1000/360).toFixed(1)}" cy="${((84-home[1])*1000/360).toFixed(1)}" r="2" fill="none" stroke="var(--ink)" stroke-width="1.2"/>`:'';
 $('sres').innerHTML=`<div class="card"><b>${nrival(SL.slug)}: ${m.modo==='s'?'dónde jugó':'contra quién jugó'}</b><div class="kp"><span><b>${tot}</b>Partidos</span><span><b>${L.length}</b>${m.modo==='s'?'Países sede':'Países rivales'}</span>${m.modo==='s'?`<span><b>${fuera}</b>Fuera del país</span><span><b>${Math.round(km).toLocaleString('es')}</b>km acumulados</span>${far?`<span><b>${far.n}</b>Más lejos (${Math.round(hav(home,mp.p[far.n])).toLocaleString('es')} km)</span>`:''}`:''}</div>
  <small>Tamaño = partidos; color = rendimiento (rojo a verde). Toca un círculo.</small>
  <svg viewBox="0 0 1000 394" style="width:100%;height:auto;background:var(--panel)"><path d="${mp.b}" fill="var(--bar)" stroke="var(--line)" stroke-width=".5"/>${cir}${ho}</svg><div id="minfo" style="min-height:22px"></div></div>
  <div class="card tw"><table><thead><tr><th class="t">${m.modo==='s'?'País sede':'País rival'}</th><th>PJ</th><th>G</th><th>E</th><th>P</th>${m.modo==='s'?'<th>km (aprox.)</th>':''}</tr></thead><tbody>${L.slice(0,15).map(a=>`<tr><td class="t"><b>${a.n}</b></td><td>${a.pj}</td><td>${a.g}</td><td>${a.e}</td><td>${a.p}</td>${m.modo==='s'?`<td>${a.n===t[0]?'—':Math.round(a.km).toLocaleString('es')}</td>`:''}</tr>`).join('')}</tbody></table></div>
  <small>Las distancias se estiman entre el centro de cada país, no entre ciudades.</small>`}
function selClick(e){const t=e.target;
 if(t.dataset.mc){const a=SL.mA[t.dataset.mc];$('minfo').textContent=`${a.n}: ${a.pj} PJ (${a.g} G, ${a.e} E, ${a.p} P)${a.km?`, ${Math.round(a.km).toLocaleString('es')} km acumulados`:''}`;return}
 if(t.dataset.sv){SL.v=t.dataset.sv;selDraw()}
 else if(t.dataset.ft){SL.slug=t.dataset.ft;SL.v='f';selDraw()}
 else if(t.dataset.rs){const k=t.dataset.rs;SL.r.dir=SL.r.sort===k?-SL.r.dir:(k==='n'||k==='c'?1:-1);SL.r.sort=k;rank()}
 else if(t.dataset.more){(t.dataset.more==='f'?SL.f:SL.hh).n+=100;selTab()}}
function selChange(e){const t=e.target,i=t.id,v=t.value,r=SL.r,f=SL.f;
 if(i==='rc')r.conf=v;else if(i==='rg')r.g=v;else if(i==='rd')r.d=+v||0;else if(i==='rh')r.h=+v||9999;else if(i==='rm')r.min=+v||1;else if(i==='rq')r.q=v;
 else if(i==='fs')SL.slug=v;else if(i==='fg')f.g=v;else if(i==='fq')f.q=v;else if(i==='fd')f.d=+v||1872;else if(i==='fh')f.h=+v||9999;else if(i==='fv')f.s=v;
 else if(i==='ms')SL.slug=v;else if(i==='mm')SL.m.modo=v;else if(i==='mg')SL.m.g=v;else if(i==='md')SL.m.d=+v||1872;else if(i==='mh')SL.m.h=+v||9999;else if(i==='ec')SL.e.conf=v;else if(i==='ea')SL.e.act=t.checked;else if(i==='eq')SL.e.q=v;else if(i==='ha')SL.slug=v;else if(i==='hb')SL.b=v;else if(i==='hg')SL.hh.g=v;else return;
 f.n=100;SL.hh.n=100;selTab()}
</script>"""
