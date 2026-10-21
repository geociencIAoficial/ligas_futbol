#!/usr/bin/env python3
"""Clasificación mundial de clubes por sus partidos de liga (fuente: Wikipedia).

    python selecciones.py tablas                      # baja la tabla de cada liga (~2 min)
    python selecciones.py tablas --ligas "Liga MX"    # solo algunas
    python selecciones.py panel                       # panel.html: se abre con doble clic

Cada liga se busca por el título de su artículo de la temporada en curso. Si
Wikipedia lo nombra distinto, agrega otro patrón al final de la línea en LIGAS.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timezone

import selecciones as S

# nombre | país | confederación | A = temporada partida (2026–27), C = año calendario | patrones
# {t} temporada (2026–27), {th} con guion (2026-27), {y} año, {s} Apertura/Clausura.
# Con prefijo es: la página es de Wikipedia en español. Varios patrones se separan con ;
LIGAS_TXT = """
Premier League|Inglaterra|UEFA|A|{t} Premier League
La Liga|España|UEFA|A|{t} La Liga
Serie A|Italia|UEFA|A|{t} Serie A
Bundesliga|Alemania|UEFA|A|{t} Bundesliga
Ligue 1|Francia|UEFA|A|{t} Ligue 1
Eredivisie|Países Bajos|UEFA|A|{t} Eredivisie
Primeira Liga|Portugal|UEFA|A|{t} Primeira Liga
Belgian Pro League|Bélgica|UEFA|A|{t} Belgian Pro League
Scottish Premiership|Escocia|UEFA|A|{t} Scottish Premiership
Süper Lig|Turquía|UEFA|A|{t} Süper Lig
Super League Greece|Grecia|UEFA|A|{t} Super League Greece
Austrian Bundesliga|Austria|UEFA|A|{t} Austrian Football Bundesliga
Swiss Super League|Suiza|UEFA|A|{t} Swiss Super League
Danish Superliga|Dinamarca|UEFA|A|{t} Danish Superliga
Eliteserien|Noruega|UEFA|C|{t} Eliteserien
Allsvenskan|Suecia|UEFA|C|{t} Allsvenskan
Ekstraklasa|Polonia|UEFA|A|{t} Ekstraklasa
Czech First League|Chequia|UEFA|A|{t} Czech First League
Croatian HNL|Croacia|UEFA|A|{t} Croatian Football League
Serbian SuperLiga|Serbia|UEFA|A|{t} Serbian SuperLiga
Ukrainian Premier League|Ucrania|UEFA|A|{t} Ukrainian Premier League
Russian Premier League|Rusia|UEFA|A|{t} Russian Premier League
Argentine Primera División|Argentina|CONMEBOL|C|{t} Argentine Primera División;{t} Liga Profesional de Fútbol
Brasileirão Série A|Brasil|CONMEBOL|C|{t} Campeonato Brasileiro Série A
Categoría Primera A|Colombia|CONMEBOL|C|{t} Categoría Primera A season;{t} Categoría Primera A
Chilean Primera División|Chile|CONMEBOL|C|es:Liga de Primera {y};{t} Chilean Primera División
Uruguayan Primera División|Uruguay|CONMEBOL|C|es:Campeonato Uruguayo de Primera División {y};{t} Uruguayan Primera División
Paraguayan Primera División|Paraguay|CONMEBOL|C|es:Torneo Clausura {y} (Paraguay);es:Torneo Apertura {y} (Paraguay);{t} Paraguayan Primera División
Ecuadorian Serie A|Ecuador|CONMEBOL|C|es:Serie A de Ecuador {y};{t} Ecuadorian Serie A
Liga 1 (Perú)|Perú|CONMEBOL|C|{t} Liga 1 (Peru);{t} Peruvian Primera División
Liga MX|México|CONCACAF|A|{t} Liga MX season;{t} Liga MX
MLS|Estados Unidos y Canadá|CONCACAF|C|{t} Major League Soccer season
Canadian Premier League|Canadá|CONCACAF|C|{t} Canadian Premier League season
Liga FPD|Costa Rica|CONCACAF|A|es:Campeonato de {s} {y} (Costa Rica);{t} Liga FPD;{t} Liga FPD season
Liga Panameña|Panamá|CONCACAF|A|es:Torneo Clausura {y} (Panamá);es:Torneo Apertura {y} (Panamá);{t} Liga Panameña de Fútbol season;{t} Liga Panameña de Fútbol
Liga Nacional (Honduras)|Honduras|CONCACAF|A|es:Torneo {s} {y} (Honduras);{t} Honduran Liga Nacional;{t} Liga Nacional de Honduras
Liga Nacional (Guatemala)|Guatemala|CONCACAF|A|es:Torneo {s} {y} (Guatemala);{t} Liga Nacional de Guatemala;{t} Liga Nacional de Fútbol de Guatemala
Primera División (El Salvador)|El Salvador|CONCACAF|A|{t} Primera División de El Salvador
Liga Primera (Nicaragua)|Nicaragua|CONCACAF|A|{t} Liga Primera;{t} Liga Primera de Nicaragua
Egyptian Premier League|Egipto|CAF|A|{t} Egyptian Premier League
Botola Pro|Marruecos|CAF|A|{t} Botola Pro;{t} Botola
Tunisian Ligue 1|Túnez|CAF|A|{t} Tunisian Ligue Professionnelle 1
Algerian Ligue 1|Argelia|CAF|A|{t} Algerian Ligue Professionnelle 1
South African Premiership|Sudáfrica|CAF|A|es:Premier Soccer League {th};{t} South African Premier Division;{t} Premier Soccer League
Saudi Pro League|Arabia Saudita|AFC|A|{t} Saudi Pro League
J1 League|Japón|AFC|A|{t} J1 League;{y} J1 League
K League 1|Corea del Sur|AFC|C|{t} K League 1
Chinese Super League|China|AFC|C|{t} Chinese Super League
Persian Gulf Pro League|Irán|AFC|A|{t} Persian Gulf Pro League
UAE Pro League|Emiratos Árabes|AFC|A|es:UAE Pro League {th};{t} UAE Pro League
Qatar Stars League|Catar|AFC|A|es:Liga de fútbol de Catar {th};{t} Qatar Stars League
A-League Men|Australia|AFC|A|{t} A-League Men
"""
LIGAS = [(l[0], l[1], l[2], l[3], l[4].split(";"))
         for l in (x.split("|") for x in LIGAS_TXT.strip().splitlines())]

TABLA_SQL = """CREATE TABLE IF NOT EXISTS tabla_liga (
    liga TEXT NOT NULL, temporada TEXT, equipo TEXT NOT NULL, wiki_titulo TEXT,
    pj INTEGER, g INTEGER, e INTEGER, p INTEGER, gf INTEGER, gc INTEGER, pts INTEGER,
    obtenida_en TEXT, PRIMARY KEY (liga, equipo));"""

# Ligas con Apertura y Clausura en el mismo artículo (y tablas acumuladas): vueltas por torneo
LIGAS_RONDAS = {"Liga MX": 1, "Liga FPD": 2, "Liga Panameña": 2, "Liga Nacional (Honduras)": 2,
                "Liga Nacional (Guatemala)": 2, "Primera División (El Salvador)": 2,
                "Liga Primera (Nicaragua)": 2}

COLS = {"pj": ("pld", "mp", "gp", "pj", "j"), "g": ("w", "pg", "g"), "e": ("d", "t", "pe", "e"),
        "p": ("l", "pp"), "gf": ("gf", "f"), "gc": ("ga", "gc", "a", "c"),
        "pts": ("pts", "points", "puntos", "pt"), "equipo": ("team", "club", "equipo")}

# Páginas con varias tablas: la que se prefiere por el título de su sección (regex sobre texto sin acentos)
LIGAS_PREFER = {"Uruguayan Primera División": "anual|acumulad", "Ecuadorian Serie A": "acumulad|general"}
EXCLUIR_ES = "descenso|promedi|cociente"        # tablas auxiliares de páginas en español


def candidatos(tipo: str, patrones: list[str], hoy: date) -> list[str]:
    ini = hoy.year if hoy.month >= 7 else hoy.year - 1
    ts = [f"{ini}–{str(ini + 1)[2:]}" if tipo == "A" else str(hoy.year)]
    if tipo == "A":
        ts.append(str(hoy.year))          # respaldo: ligas que pasan a año calendario
    s = "Apertura" if hoy.month >= 7 else "Clausura"
    return list(dict.fromkeys(p.format(t=t, th=t.replace("–", "-"), y=hoy.year, s=s)
                              for t in ts for p in patrones))


def parsear_posiciones(html: str, rondas: int | None = None, prefer: str | None = None,
                       excluir: str | None = None) -> list[dict]:
    """Filas de la tabla de posiciones; ignora el resto de tablas del artículo.

    rondas: ligas con dos torneos por artículo (Liga MX = 1 vuelta). Se usa el torneo más
    reciente y se descartan las tablas acumuladas.
    prefer / excluir: expresiones regulares sobre el título de la sección de cada tabla.
    """
    tablas = []
    for t in S._raiz(html).find_all("table"):
        tr0 = t.find("tr")
        if tr0 is None:
            continue
        cab = [(S.norm(S._texto(c)).split() or [""])[0] for c in tr0.find_all(["th", "td"])]
        idx = {k: next((i for i, h in enumerate(cab) if h in v), None) for k, v in COLS.items()}
        if None in idx.values():
            continue
        h = t.find_previous(["h2", "h3", "h4", "h5"])
        enc = S.norm(S._texto(h)) if h else ""
        if excluir and re.search(excluir, enc):
            continue
        tabla = []
        for tr in t.find_all("tr")[1:]:
            c = tr.find_all(["th", "td"])
            if len(c) <= max(idx.values()):
                continue
            a = S._enlace_jugador(c[idx["equipo"]])
            nombre = S._texto(a) if a else S._texto(c[idx["equipo"]])
            num = {k: S.a_entero(S._texto(c[i])) for k, i in idx.items() if k != "equipo"}
            if nombre and None not in num.values():
                tabla.append({"equipo": nombre, "wiki": S.titulo(a) if a else None, **num})
        if rondas and any(f["pj"] > rondas * (len(tabla) - 1) for f in tabla):
            continue                                  # tabla acumulada, no de un torneo
        tablas.append((enc, tabla))
    if prefer:
        elegidas = [t for t in tablas if re.search(prefer, t[0])][:1]
        tablas = elegidas or tablas
    filas, pos = [], {}
    for _, tabla in tablas:
        for fila in tabla:
            n = fila["wiki"] or fila["equipo"]
            if n in pos and not (rondas and fila["pj"]):
                continue
            if n in pos:
                filas[pos[n]] = fila                  # torneo más reciente
            else:
                pos[n] = len(filas)
                filas.append(fila)
    return filas


def html_pagina(pagina: str, refrescar: bool = False) -> str:
    """Con prefijo es: usa la API de Wikipedia en español."""
    if not pagina.startswith("es:"):
        return S.wiki_html(pagina, refrescar)
    api = S.WIKI_API
    S.WIKI_API = "https://es.wikipedia.org/w/api.php"
    try:
        return S.wiki_html(pagina[3:], refrescar)
    finally:
        S.WIKI_API = api


MALOS = ("femenil", "women", "segunda", "ascenso", "cup", "copa", "youth", "reserve", "u-", "u20", "u21")


def buscar_titulos(tipo, pats, hoy):
    """Respaldo: busca en Wikipedia artículos de la temporada que se parezcan a los patrones."""
    pats = [p for p in pats if not p.startswith("es:")]
    if not pats:
        return []
    ts = {str(hoy.year), f"{hoy.year if hoy.month >= 7 else hoy.year - 1}–"}
    bases = {p.replace("{t}", "").replace("{y}", "").replace("{s}", "").replace(" season", "").strip().lower()
             for p in pats}
    S._wiki.headers["User-Agent"] = S.user_agent()
    try:
        r = S._wiki.get(S.WIKI_API, timeout=30, params={
            "action": "query", "list": "search", "format": "json", "formatversion": 2,
            "srlimit": 8, "srsearch": f"{hoy.year} {sorted(bases, key=len)[-1]}"}).json()
    except Exception:
        return []
    time.sleep(S.WIKI_PAUSA_S)
    out = []
    for x in r.get("query", {}).get("search", []):
        t = x["title"]
        if any(t.startswith(v) for v in ts) and any(b in t.lower() for b in bases) \
                and not any(m in t.lower() for m in MALOS):
            out.append(t)
    return out


def cargar_manuales(con) -> set[str]:
    """Ligas que Wikipedia aún no tiene: se llenan a mano en datos_manuales.csv."""
    import csv
    ruta = S.BASE_DIR / "datos_manuales.csv"
    if not ruta.exists():
        return set()
    por_liga: dict[str, list] = {}
    for r in csv.DictReader(ruta.open(encoding="utf-8-sig")):
        try:
            g, e = int(r["g"]), int(r["e"])
            pts = int(r["pts"]) if (r.get("pts") or "").strip() else 3 * g + e
            fila = (r["liga"].strip(), "datos_manuales.csv", r["equipo"].strip(), None, int(r["pj"]), g, e,
                    int(r["p"]), int(r["gf"]), int(r["gc"]), pts, S.ahora())
        except (KeyError, ValueError, AttributeError):
            continue
        por_liga.setdefault(fila[0], []).append(fila)
    for liga, filas in por_liga.items():
        con.execute("DELETE FROM tabla_liga WHERE liga=?", (liga,))
        con.executemany("INSERT OR REPLACE INTO tabla_liga VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", filas)
        print(f"  {liga}: {len(filas)} equipos (datos_manuales.csv)")
    return set(por_liga)


def cmd_tablas(args):
    hoy = date.today()
    pedidas = {S.norm(x) for x in (args.ligas or [])}
    sin = []
    with S.conectar() as con:
        con.execute(TABLA_SQL)
        for nombre, pais, conf, tipo, pats in LIGAS:
            if pedidas and S.norm(nombre) not in pedidas:
                continue
            motivos, vistos = [], set()
            cola = candidatos(tipo, pats, hoy)
            buscado = False
            while cola:
                pagina = cola.pop(0)
                if pagina in vistos:
                    continue
                vistos.add(pagina)
                try:
                    html = html_pagina(pagina, args.refrescar)
                except RuntimeError:
                    motivos.append(f"{pagina}: no existe")
                    time.sleep(S.WIKI_PAUSA_S)
                else:
                    filas = parsear_posiciones(html, LIGAS_RONDAS.get(nombre), LIGAS_PREFER.get(nombre),
                                               EXCLUIR_ES if pagina.startswith("es:") else None)
                    if filas and any(f["pj"] for f in filas):
                        con.execute("DELETE FROM tabla_liga WHERE liga=?", (nombre,))
                        con.executemany("INSERT OR REPLACE INTO tabla_liga VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                        [(nombre, pagina, f["equipo"], f["wiki"], f["pj"], f["g"], f["e"],
                                          f["p"], f["gf"], f["gc"], f["pts"], S.ahora()) for f in filas])
                        print(f"  {nombre}: {len(filas)} equipos ({pagina})")
                        break
                    motivos.append(f"{pagina}: existe pero no se reconoció la tabla de posiciones")
                if not cola and not buscado:      # último recurso: buscar el título en Wikipedia
                    buscado = True
                    cola = buscar_titulos(tipo, pats, hoy)
            else:
                sin.append(nombre)
                print(f"  {nombre}: sin tabla")
                for m in motivos:
                    print(f"      - {m}")
        man = cargar_manuales(con)
        sin = [x for x in sin if x not in man]
    if sin:
        print(f"\n{len(sin)} ligas sin tabla: {', '.join(sin)}.\n"
              "Revisa arriba el motivo de cada una y ajusta su línea en LIGAS_TXT.")


def _datos():
    meta = {l[0]: l for l in LIGAS}
    with S.conectar() as con:
        con.execute(TABLA_SQL)
        filas = con.execute("SELECT * FROM tabla_liga").fetchall()
    if not filas:
        return None, None
    datos = [[r["equipo"], r["liga"], meta[r["liga"]][1] if r["liga"] in meta else "",
              meta[r["liga"]][2] if r["liga"] in meta else "", r["pj"], r["g"], r["e"], r["p"],
              r["gf"], r["gc"], r["pts"]] for r in filas]
    return datos, max(r["obtenida_en"] for r in filas)[:10]


def _html(datos, fecha, pwa=False):
    h = (PLANTILLA.replace("__DATOS__", json.dumps(datos, ensure_ascii=False).replace("</", "<\\/"))
         .replace("__FECHA__", fecha))
    return h.replace("__PWA_HEAD__", PWA_HEAD if pwa else "").replace("__PWA_JS__", PWA_JS if pwa else "")


def cmd_panel(args):
    datos, fecha = _datos()
    if not datos:
        print("No hay tablas. Corre primero:  python selecciones.py tablas")
        return
    salida = S.BASE_DIR / "panel.html"
    salida.write_text(_html(datos, fecha), "utf-8")
    print(f"Listo: {salida}  ({len(datos)} equipos de {len({d[1] for d in datos})} ligas)")


def _icono(n: int) -> bytes:
    """PNG sencillo: tres barras ascendentes sobre fondo oscuro (zona segura para íconos adaptables)."""
    import struct, zlib
    fondo, claro, verde = (18, 33, 28), (232, 241, 237), (62, 207, 132)
    barras = [(.28, .56, claro), (.45, .42, claro), (.62, .26, verde)]   # x, y superior, color
    filas = []
    for y in range(n):
        fila = bytearray([0])
        for x in range(n):
            c = fondo
            for bx, by, bc in barras:
                if bx * n <= x < (bx + .13) * n and by * n <= y < .74 * n:
                    c = bc
            fila += bytes(c)
        filas.append(bytes(fila))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(filas), 9)) + chunk(b"IEND", b""))


def cmd_web(args):
    datos, fecha = _datos()
    if not datos:
        print("No hay tablas. Corre primero:  python selecciones.py tablas")
        return
    d = S.BASE_DIR / "docs"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(_html(datos, fecha, pwa=True), "utf-8")
    (d / "manifest.webmanifest").write_text(json.dumps({
        "name": "Clasificación mundial de clubes", "short_name": "Clubes", "lang": "es",
        "id": "./", "start_url": "./", "scope": "./", "categories": ["sports"], "display": "standalone",
        "background_color": "#12211c", "theme_color": "#12211c",
        "icons": [{"src": f"icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png",
                   "purpose": "any maskable"} for n in (192, 512)]}, ensure_ascii=False, indent=1), "utf-8")
    (d / "sw.js").write_text(SW.replace("__V__", fecha + "-" + str(len(datos))), "utf-8")
    for n in (192, 512):
        (d / f"icon-{n}.png").write_bytes(_icono(n))
    (d / "apple-touch-icon.png").write_bytes(_icono(192))
    (d / ".nojekyll").write_text("", "utf-8")
    print(f"Listo: {d}/  ({len(datos)} equipos, datos al {fecha})")


PWA_HEAD = """<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="theme-color" content="#12211c"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Clubes">"""
PWA_JS = "<script>if('serviceWorker' in navigator)addEventListener('load',()=>navigator.serviceWorker.register('sw.js'))</script>"
SW = """const V='clubes-__V__',A=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(A)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;
 e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(V).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)))});
"""


PLANTILLA = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">__PWA_HEAD__<title>Clasificación mundial de clubes</title>
<style>
:root{--bg:#f2f5f4;--panel:#fff;--ink:#12211c;--mut:#5d6f68;--line:#dbe4e0;--acc:#17824a;--acc2:#e0a81f;--bar:#cfe8d9;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0e1714;--panel:#16231f;--ink:#e8f1ed;--mut:#93a8a0;--line:#26372f;--acc:#3ecf84;--acc2:#e8b93a;--bar:#1f4a35;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 "Segoe UI",system-ui,sans-serif}
header{padding:28px 20px 8px;max-width:1180px;margin:auto}h1{margin:0;font-size:28px;letter-spacing:-.4px}
header p{margin:4px 0 0;color:var(--mut)}main{max-width:1180px;margin:auto;padding:12px 20px 40px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px}
.seg{display:flex;gap:4px;flex-wrap:wrap}.seg button,.ctl button{font:inherit;border:1px solid var(--line);background:transparent;color:var(--ink);padding:7px 14px;border-radius:7px;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:12px}label{color:var(--mut);font-size:13px}
select,input{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--ink)}
input[type=number]{width:64px}.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{background:var(--bar);border-radius:99px;padding:2px 6px 2px 11px;font-size:13px}
.chip button{border:0;background:none;color:inherit;cursor:pointer;font-size:15px}
.pick{max-height:170px;overflow:auto;border:1px solid var(--line);border-radius:7px;padding:6px 10px;columns:3 190px;width:100%}
.pick label{display:block;color:var(--ink);font-size:14px}.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{cursor:pointer;color:var(--mut);font-weight:600;font-size:13px;position:sticky;top:0;background:var(--panel);user-select:none}
th.on{color:var(--acc)}td.t,th.t{text-align:left}td.n{color:var(--mut);width:36px}td.l{color:var(--mut);font-size:13px}
.pb{display:inline-block;vertical-align:middle;width:90px;height:8px;background:var(--bar);border-radius:4px;margin-right:8px;overflow:hidden}
.pb i{display:block;height:100%;background:var(--acc)}tr:hover td{background:color-mix(in srgb,var(--bar) 35%,transparent)}
td.e1,th.e1{position:sticky;left:0;background:var(--panel);z-index:1}td.e1{box-shadow:1px 0 0 var(--line)}
@media(max-width:640px){body{font-size:14px}header{padding:max(20px,env(safe-area-inset-top)) 14px 4px}main{padding:8px 10px calc(30px + env(safe-area-inset-bottom))}h1{font-size:22px}th,td{padding:7px 7px}.card{padding:10px}.seg button{flex:1;padding:8px 6px}}
.vac{padding:30px;text-align:center;color:var(--mut)}.hide{display:none}small{color:var(--mut)}
</style></head><body>
<header><h1>Clasificación mundial de clubes</h1>
<p>Partidos de liga de la temporada en curso. Datos de Wikipedia al __FECHA__.</p></header>
<main>
<div class="card"><div class="seg" id="modos"></div><div class="row" id="ctl"></div>
<div class="row"><label>Buscar <input id="q" placeholder="Equipo"></label>
<label>Mínimo de partidos <input id="min" type="number" min="1" value="5"></label>
<small>Rendimiento = puntos obtenidos entre puntos en juego (3 por partido jugado).</small></div></div>
<div class="card tw"><table><thead id="th"></thead><tbody id="tb"></tbody></table><div id="vac" class="vac hide">Ningún equipo cumple los filtros.</div></div>
</main>
<script>
const D=__DATOS__.map(r=>({k:r[1]+'|'+r[0],eq:r[0],liga:r[1],pais:r[2],conf:r[3],pj:r[4],g:r[5],e:r[6],p:r[7],gf:r[8],gc:r[9],dg:r[8]-r[9],pts:r[10],rend:r[4]?r[10]/(r[4]*3):0}));
const LIGAS=[...new Set(D.map(d=>d.liga))].sort(),CONFS=[...new Set(D.map(d=>d.conf))].sort();
const COLS=[['n','#'],['eq','Equipo'],['liga','Liga'],['pj','PJ'],['g','G'],['e','E'],['p','P'],['gf','GF'],['gc','GC'],['dg','DG'],['pts','Pts'],['rend','Rendimiento']];
const S={modo:'mundo',conf:CONFS[0],liga:LIGAS[0],cl:new Set(),ce:new Set(),ligaEq:LIGAS[0],sort:'rend',dir:-1};
const $=i=>document.getElementById(i),opt=(a,v)=>a.map(x=>`<option${x===v?' selected':''}>${x}</option>`).join('');
const MODOS={mundo:'Mundo',conf:'Confederación',pais:'País / liga',custom:'Personalizado'};
function ctl(){
 $('modos').innerHTML=Object.entries(MODOS).map(([k,v])=>`<button aria-pressed="${S.modo===k}" data-m="${k}">${v}</button>`).join('');
 let h='';
 if(S.modo==='conf')h=`<label>Confederación <select id="sc">${opt(CONFS,S.conf)}</select></label>`;
 if(S.modo==='pais')h=`<label>Liga <select id="sl">${opt(LIGAS,S.liga)}</select></label>`;
 if(S.modo==='custom'){
  const ch=[...S.cl].map(l=>`<span class="chip">${l} (completa)<button data-rl="${l}" title="Quitar">×</button></span>`).concat(
   [...S.ce].map(k=>`<span class="chip">${k.split('|')[1]} <small>${k.split('|')[0]}</small><button data-re="${k}" title="Quitar">×</button></span>`)).join('');
  const eqs=D.filter(d=>d.liga===S.ligaEq).sort((a,b)=>a.eq.localeCompare(b.eq));
  h=`<div style="width:100%"><div class="chips">${ch||'<small>Agrega ligas completas (hasta 10) o equipos sueltos de cualquier liga.</small>'}</div></div>
  <label>Liga <select id="se">${opt(LIGAS,S.ligaEq)}</select></label>
  <button id="al" ${S.cl.size>=10?'disabled':''}>Agregar liga completa (${S.cl.size}/10)</button>
  <div class="pick">${eqs.map(d=>`<label><input type="checkbox" value="${d.k}" ${S.ce.has(d.k)?'checked':''}> ${d.eq}</label>`).join('')}</div>
  <button id="ae">Agregar equipos marcados</button>`;}
 $('ctl').innerHTML=h;
}
function filas(){
 let r=D;
 if(S.modo==='conf')r=r.filter(d=>d.conf===S.conf);
 if(S.modo==='pais')r=r.filter(d=>d.liga===S.liga);
 if(S.modo==='custom')r=r.filter(d=>S.cl.has(d.liga)||S.ce.has(d.k));
 const q=$('q').value.trim().toLowerCase(),m=+$('min').value||1;
 return r.filter(d=>d.pj>=m&&(!q||d.eq.toLowerCase().includes(q)));
}
function pintar(){
 $('th').innerHTML='<tr>'+COLS.map(([k,t])=>`<th data-s="${k}" class="${k==='eq'?'e1 ':''}${k==='eq'||k==='liga'?'t ':''}${S.sort===k?'on':''}">${t}${S.sort===k?(S.dir<0?' ▼':' ▲'):''}</th>`).join('')+'</tr>';
 const f=filas(),k=S.sort;
 f.sort((a,b)=>{let x=a[k],y=b[k];if(k==='n'){x=a.rend;y=b.rend}
  const c=typeof x==='string'?x.localeCompare(y):x-y;return c?c*S.dir:(b.rend-a.rend)||(b.dg-a.dg)||(b.gf-a.gf)});
 $('tb').innerHTML=f.map((d,i)=>`<tr><td class="n">${i+1}</td><td class="t e1"><b>${d.eq}</b></td><td class="t l">${d.liga}</td><td>${d.pj}</td><td>${d.g}</td><td>${d.e}</td><td>${d.p}</td><td>${d.gf}</td><td>${d.gc}</td><td>${d.dg>0?'+':''}${d.dg}</td><td><b>${d.pts}</b></td><td><span class="pb"><i style="width:${d.rend*100}%"></i></span>${(d.rend*100).toFixed(1)}%</td></tr>`).join('');
 $('vac').classList.toggle('hide',f.length>0);
}
function todo(){ctl();pintar()}
document.addEventListener('click',e=>{const t=e.target;
 if(t.dataset.m){S.modo=t.dataset.m;todo()}
 else if(t.dataset.s){const k=t.dataset.s;S.dir=S.sort===k?-S.dir:(k==='eq'||k==='liga'?1:-1);S.sort=k;pintar()}
 else if(t.dataset.rl){S.cl.delete(t.dataset.rl);todo()}
 else if(t.dataset.re){S.ce.delete(t.dataset.re);todo()}
 else if(t.id==='al'){S.cl.add(S.ligaEq);todo()}
 else if(t.id==='ae'){document.querySelectorAll('.pick input:checked').forEach(c=>S.ce.add(c.value));todo()}});
document.addEventListener('change',e=>{const t=e.target;
 if(t.id==='sc'){S.conf=t.value;pintar()}else if(t.id==='sl'){S.liga=t.value;pintar()}else if(t.id==='se'){S.ligaEq=t.value;ctl()}
 else if(t.id==='min')pintar()});
$('q').addEventListener('input',pintar);todo();
</script>__PWA_JS__</body></html>
"""
