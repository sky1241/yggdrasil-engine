#!/usr/bin/env python3
"""
gen_viz_v3.py — Generates yggdrasil_rain_v3.html
La Pluie v3: Vivant/Musée/Fusion cubes + 9 continent filters + escaliers spectraux.

Changes vs v3-old:
  - C2/C3 checkboxes → Vivant/Musée/Fusion radio buttons
  - Symbol tuple: [s, px, pz, isCentre, domain, cube, wc]
    cube: 0=vivant, 1=musée, 2=always-show (S1-S6, centres)
    wc: works_count
  - Escalier toggle: highlights geo lianes + passe-partout symbols
"""
import json, colorsys, re, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2_HTML = os.path.join(ROOT, 'viz', 'yggdrasil_rain_v2.html')
V3_HTML = os.path.join(ROOT, 'viz', 'yggdrasil_rain_v3.html')

# ══════════════════════════════════════════════════════════
# 1. Extract positions from v2 HTML
# ══════════════════════════════════════════════════════════
print("[1] Extracting positions from v2 HTML...")
with open(V2_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

m1 = re.search(r'^(const ST_C1=\[.*?\];)$', html, re.MULTILINE)
m2 = re.search(r'^(const CTR_C1=\[.*?\];)$', html, re.MULTILINE)
m3 = re.search(r'^(const ST_C2=\[.*?\];)$', html, re.MULTILINE)
m4 = re.search(r'^(const CTR_C2=\[.*?\];)$', html, re.MULTILINE)
if not all([m1, m2, m3, m4]):
    raise ValueError("Cannot extract data from v2 HTML")

st_c1 = json.loads(m1.group(1)[len("const ST_C1="):-1])
st_c2 = json.loads(m3.group(1)[len("const ST_C2="):-1])
CTR_C1_LINE = m2.group(1)
CTR_C2_LINE = m4.group(1)

total_c1 = sum(len(s['sy']) for s in st_c1)
total_c2 = sum(len(s['sy']) for s in st_c2)
print(f"  C1: {total_c1}, C2: {total_c2}")

# ══════════════════════════════════════════════════════════
# 2. Load strates_export_v2.json for cube info
# ══════════════════════════════════════════════════════════
print("[2] Loading cube info from strates_export_v2.json...")
with open(os.path.join(ROOT, 'data', 'strates_export_v2.json'), encoding='utf-8') as f:
    stdata = json.load(f)

# Build lookup: (symbol_s, domain) → {cube, wc}
cube_lookup = {}
for st in stdata['strates']:
    for sym in st['symbols']:
        key = (sym['s'], sym.get('domain', ''))
        cube_val = sym.get('cube', 'vivant')  # default vivant
        wc = sym.get('works_count', 0)
        cube_lookup[key] = {'cube': cube_val, 'wc': wc}

# Also build name-only lookup as fallback
name_lookup = {}
for st in stdata['strates']:
    for sym in st['symbols']:
        if sym['s'] not in name_lookup:
            name_lookup[sym['s']] = {'cube': sym.get('cube', 'vivant'), 'wc': sym.get('works_count', 0)}

print(f"  Cube lookup: {len(cube_lookup)} entries")

# ══════════════════════════════════════════════════════════
# 3. Load escaliers spectraux
# ══════════════════════════════════════════════════════════
print("[3] Loading escaliers spectraux...")
esc_path = os.path.join(ROOT, 'data', 'escaliers_unified.json')
esc_geo_set = set()
esc_key_set = set()
esc_rte_geo = []
esc_rte_key = []
esc_centroids = {}
if os.path.exists(esc_path):
    with open(esc_path, encoding='utf-8') as f:
        esc_data = json.load(f)
    # Top 200 geo by score (for glow)
    for e in esc_data.get('geo', [])[:200]:
        esc_geo_set.add(e['s'])
    # All key (passe-partout)
    for e in esc_data.get('key', []):
        esc_key_set.add(e['s'])
    # Route data (all 300 geo + 69 key + centroids)
    for e in esc_data.get('geo', [])[:300]:
        esc_rte_geo.append([round(e['px'], 4), round(e['pz'], 4), e['alien'], round(e['score'], 3)])
    for e in esc_data.get('key', []):
        esc_rte_key.append([round(e['px'], 4), round(e['pz'], 4), e['home'], e['continents'], e['n_continents']])
    for name, c in esc_data.get('centroids', {}).items():
        esc_centroids[name] = [round(c['px'], 4), round(c['pz'], 4)]
    print(f"  Geo: {len(esc_geo_set)} glow, {len(esc_rte_geo)} routes")
    print(f"  Key: {len(esc_key_set)} glow, {len(esc_rte_key)} routes")
    print(f"  Centroids: {len(esc_centroids)}")
else:
    print(f"  ⚠️ {esc_path} not found, skipping escaliers")

# ══════════════════════════════════════════════════════════
# 4. Enrich symbol tuples with cube/wc
# ══════════════════════════════════════════════════════════
print("[4] Enriching symbol tuples...")

# cube encoding: 0=vivant, 1=musée, 2=always-show
CUBE_MAP = {'vivant': 0, 'musee': 1}

def enrich_strate(strate_data, strate_idx):
    """Add cube/wc to each symbol tuple in a strate."""
    new_sy = []
    for sym in strate_data['sy']:
        # sym = [s, px, pz, isCentre, domain]
        s_name = sym[0]
        domain = sym[4] if len(sym) > 4 else ''
        is_centre = sym[3]

        # Lookup cube info
        info = cube_lookup.get((s_name, domain)) or name_lookup.get(s_name) or {}
        cube_str = info.get('cube', 'vivant')
        wc = info.get('wc', 0)

        # S1-S6 symbols and centres are always visible (cube=2)
        if strate_idx > 0 or is_centre == 1:
            cube = 2
        else:
            cube = CUBE_MAP.get(cube_str, 0)

        new_sy.append([s_name, sym[1], sym[2], is_centre, domain, cube, wc])
    strate_data['sy'] = new_sy

for i, st in enumerate(st_c1):
    enrich_strate(st, i)

for i, st in enumerate(st_c2):
    # C2 symbols: always visible (they're conjectures, separate layer)
    for j, sym in enumerate(st['sy']):
        s_name = sym[0]
        domain = sym[4] if len(sym) > 4 else ''
        info = cube_lookup.get((s_name, domain)) or name_lookup.get(s_name) or {}
        wc = info.get('wc', 0)
        st['sy'][j] = [s_name, sym[1], sym[2], sym[3], domain, 2, wc]

# Recount
n_vivant = sum(1 for st in st_c1 for sym in st['sy'] if sym[5] == 0)
n_musee = sum(1 for st in st_c1 for sym in st['sy'] if sym[5] == 1)
n_always = sum(1 for st in st_c1 for sym in st['sy'] if sym[5] == 2)
print(f"  C1 vivant: {n_vivant}, musée: {n_musee}, always: {n_always}")

# ══════════════════════════════════════════════════════════
# 5. Generate domain colors
# ══════════════════════════════════════════════════════════
print("[5] Generating domain colors...")

domain_counts = Counter()
for st in st_c1 + st_c2:
    for sym in st['sy']:
        domain_counts[sym[4]] += 1

sorted_domains = domain_counts.most_common()
n_domains = len(sorted_domains)

FAMILY_HUES = {
    'algèbre': 230, 'algèbre lin': 225, 'topologie': 250, 'géométrie': 215,
    'géom diff': 210, 'géom algébrique': 245, 'nb théorie': 260, 'combinatoire': 270,
    'probabilités': 235, 'statistiques': 240, 'analyse': 220, 'analyse fonctionnelle': 228,
    'EDP': 205, 'optimisation': 218, 'ensembles': 275, 'logique': 265,
    'calculabilité': 255, 'complexité': 258, 'automates': 262, 'catégories': 248,
    'trigonométrie': 222, 'systèmes dynamiques': 238, 'analyse numérique': 212,
    'arithmétique': 268, 'descriptive': 272, 'nombres': 264, 'nb premiers': 266,
    'ordinaux': 278, 'complexes': 232, 'mesure': 226, 'stochastique': 236,
    'mécanique analytique': 208,
    'quantique': 185, 'mécanique': 175, 'thermo': 178, 'mécanique stat': 182,
    'fluides': 190, 'relativité': 188, 'cosmologie': 195, 'électromagn': 172,
    'nucléaire': 168, 'particules': 180, 'QFT': 192, 'optique': 176,
    'gravitation': 198,
    'informatique': 290, 'ML': 310, 'crypto': 295, 'signal': 300,
    'information': 305, 'vision': 315, 'NLP': 320, 'robotique': 325,
    'télécommunications': 298, 'contrôle': 302,
    'chimie': 35, 'chimie organique': 42, 'polymères': 48, 'électrochimie': 28,
    'nanotechnologie': 55, 'matériaux': 25,
    'biologie': 120, 'écologie': 105, 'évolution': 130, 'immunologie': 100,
    'génomique': 135, 'oncologie': 95, 'bioinformatique': 140,
    'médecine': 350, 'neurosciences': 345, 'biomédical': 355,
    'pharmacologie': 5, 'épidémiologie': 10, 'psychologie': 340,
    'géosciences': 70, 'climatologie': 80, 'sismologie': 65, 'volcanologie': 62,
    'océanographie': 85, 'agronomie': 75, 'environnement': 88,
    'ingénierie': 200, 'aérospatiale': 202, 'énergie': 197,
    'économie': 18, 'finance': 22, 'linguistique': 335, 'anthropologie': 330,
    'sociologie': 338, 'science politique': 15, 'démographie': 12,
    'droit': 8, 'éducation': 332, 'histoire': 20,
    'science générale': 160, 'astronomie': 193,
}

domain_colors = {}
for i, (domain, count) in enumerate(sorted_domains):
    hue = FAMILY_HUES.get(domain, (i * 360 / n_domains) % 360)
    sat = 0.70 + 0.12 * ((i % 3) / 2)
    lit = 0.52 + 0.08 * ((i % 5) / 4)
    r, g, b = colorsys.hls_to_rgb(hue / 360, lit, sat)
    domain_colors[domain] = (int(r * 255), int(g * 255), int(b * 255))

dc_js = "const DC={"
for domain, (r, g, b) in domain_colors.items():
    dc_js += f'"{domain}":[{r},{g},{b}],'
dc_js += "};"

dl_js = "const DL=" + json.dumps([[d, c] for d, c in sorted_domains], ensure_ascii=False) + ";"

print(f"  {n_domains} domain colors generated")

# ══════════════════════════════════════════════════════════
# 6. Serialize enriched data
# ══════════════════════════════════════════════════════════
print("[6] Serializing data...")

ST_C1_LINE = "const ST_C1=" + json.dumps(st_c1, ensure_ascii=False, separators=(',', ':')) + ";"
ST_C2_LINE = "const ST_C2=" + json.dumps(st_c2, ensure_ascii=False, separators=(',', ':')) + ";"

# Escalier sets as JS
esc_geo_js = "const ESC_GEO=new Set(" + json.dumps(sorted(esc_geo_set), ensure_ascii=False) + ");"
esc_key_js = "const ESC_KEY=new Set(" + json.dumps(sorted(esc_key_set), ensure_ascii=False) + ");"
rte_geo_js = "const RTE_GEO=" + json.dumps(esc_rte_geo, ensure_ascii=False, separators=(',', ':')) + ";"
rte_key_js = "const RTE_KEY=" + json.dumps(esc_rte_key, ensure_ascii=False, separators=(',', ':')) + ";"
rte_c_js = "const RTE_C=" + json.dumps(esc_centroids, ensure_ascii=False, separators=(',', ':')) + ";"

print(f"  ST_C1: {len(ST_C1_LINE):,} chars, ST_C2: {len(ST_C2_LINE):,} chars")
print(f"  Routes: {len(rte_geo_js):,} + {len(rte_key_js):,} + {len(rte_c_js):,} chars")

# ══════════════════════════════════════════════════════════
# 7. Generate HTML
# ══════════════════════════════════════════════════════════
print("[7] Generating HTML...")

# Route rendering JS (injected via {route_render_js} — literal braces, not f-string)
route_render_js = """  // ═══ ROUTES at S0 ═══
  if(showRte && currentST.length > 0) {
    const rot0 = time * 0.3;
    const cr0 = Math.cos(rot0), sr0 = Math.sin(rot0);
    const y0 = currentST[0].yr * BOX.h;
    const rp = (px, pz) => [px*cr0 - pz*sr0, px*sr0 + pz*cr0];

    // Geo routes (orange arcs concept → alien centroid)
    for (const g of RTE_GEO) {
      const ac = RTE_C[g[2]];
      if (!ac) continue;
      if (hasDomFilter) {
        const acont = CONTINENTS.find(c => c.id === g[2]);
        if (acont && !acont.doms.some(d => activeDomains.has(d))) continue;
      }
      const [rx, rz] = rp(g[0], g[1]);
      const [ax, az] = rp(ac[0], ac[1]);
      const dist = Math.sqrt((ax-rx)**2 + (az-rz)**2);
      const arcH = dist * 0.15;
      ctx.beginPath();
      for (let i = 0; i <= 16; i++) {
        const t = i / 16;
        const x = rx + (ax-rx)*t;
        const z = rz + (az-rz)*t;
        const ay = y0 + arcH * 4 * t * (1-t);
        const p = project(x, ay, z);
        if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = `rgba(255,107,53,${Math.min(0.5, g[3] * 0.6)})`;
      ctx.lineWidth = Math.max(0.4, g[3] * 1.2);
      ctx.stroke();
    }

    // Key routes (cyan dashed arcs concept → each continent)
    ctx.setLineDash([3, 4]);
    for (const k of RTE_KEY) {
      const [rx, rz] = rp(k[0], k[1]);
      const conts = k[3];
      const nc = k[4];
      for (const cont of conts) {
        if (cont === k[2]) continue;
        if (hasDomFilter) {
          const ccont = CONTINENTS.find(c => c.id === cont);
          if (ccont && !ccont.doms.some(d => activeDomains.has(d))) continue;
        }
        const cc = RTE_C[cont];
        if (!cc) continue;
        const [ax, az] = rp(cc[0], cc[1]);
        const dist = Math.sqrt((ax-rx)**2 + (az-rz)**2);
        const arcH = dist * 0.12;
        ctx.beginPath();
        for (let i = 0; i <= 12; i++) {
          const t = i / 12;
          const x = rx + (ax-rx)*t;
          const z = rz + (az-rz)*t;
          const ay = y0 + arcH * 4 * t * (1-t);
          const p = project(x, ay, z);
          if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
        }
        ctx.strokeStyle = `rgba(53,212,255,${Math.min(0.4, 0.1 + nc * 0.04)})`;
        ctx.lineWidth = 0.6;
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);
  }
"""

v3_html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YGGDRASIL \u2014 La Pluie v3 \u00b7 Vivant/Mus\u00e9e</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Instrument+Serif:ital@0;1&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080d;color:#c8ccd4;font-family:'JetBrains Mono',monospace;overflow:hidden;height:100vh;width:100vw}}
canvas{{display:block;position:fixed;top:0;left:0;z-index:1}}
#hud{{position:fixed;top:18px;left:22px;z-index:10;pointer-events:none}}
#hud h1{{font-family:'Instrument Serif',serif;font-size:24px;font-weight:400;color:#e8e8f0;margin-bottom:2px}}
#hud .sub{{font-size:9px;color:#3a3a4a;letter-spacing:2.5px;text-transform:uppercase}}
#info{{position:fixed;bottom:24px;left:24px;z-index:10;pointer-events:none;max-width:520px}}
#info .sn{{font-family:'Instrument Serif',serif;font-size:19px;color:#fff;margin-bottom:2px}}
#info .sf{{font-size:12px;color:#8af;margin-bottom:5px}}
#info .sd{{font-size:10.5px;color:#667;line-height:1.5}}
#info .sl{{font-size:9px;color:#3a3a4a;margin-top:6px}}
#cont-panel{{position:fixed;top:12px;right:12px;z-index:10;pointer-events:all;
  display:flex;flex-direction:column;gap:2px;max-height:94vh;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:#222 transparent}}
#cont-panel::-webkit-scrollbar{{width:3px}}
#cont-panel::-webkit-scrollbar-thumb{{background:#333;border-radius:2px}}
.cb{{display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:4px;cursor:pointer;
  transition:all 0.15s;border:1px solid rgba(255,255,255,0.04);user-select:none}}
.cb:hover{{background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.08)}}
.cb.act{{border-color:rgba(255,255,255,0.15)}}
.cb.dim{{opacity:0.2}}
.cb-icon{{font-size:11px;flex-shrink:0}}
.cb-name{{font-size:8.5px;letter-spacing:0.5px;color:#556;transition:color 0.15s;white-space:nowrap}}
.cb.act .cb-name,.cb:hover .cb-name{{color:#bbc}}
.cb-count{{font-size:7px;color:#334;margin-left:auto;padding-left:6px}}
.sub-doms{{display:none;flex-direction:column;gap:0px;padding:0 0 2px 20px}}
.sub-doms.open{{display:flex}}
.sd-item{{display:flex;align-items:center;gap:5px;padding:1px 8px 1px 4px;border-radius:3px;cursor:pointer;
  transition:all 0.15s;border:1px solid transparent;opacity:0.5}}
.sd-item:hover{{background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.06);opacity:1}}
.sd-item.act{{background:rgba(255,255,255,0.05);border-color:rgba(255,255,255,0.1);opacity:1}}
.sd-item.dim{{opacity:0.12}}
.sd-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.sd-name{{font-size:7.5px;color:#445;letter-spacing:0.3px;white-space:nowrap;max-width:105px;overflow:hidden;text-overflow:ellipsis}}
.sd-item.act .sd-name,.sd-item:hover .sd-name{{color:#88a}}
.sd-cnt{{font-size:6.5px;color:#2a2a35;margin-left:auto;padding-left:3px}}
#cont-reset{{font-size:8px;color:#445;letter-spacing:1.5px;text-align:center;padding:5px 0;cursor:pointer;
  border-top:1px solid #1a1a22;margin-top:3px}}
#cont-reset:hover{{color:#8af}}
#strate-legend{{position:fixed;top:50%;left:12px;transform:translateY(-50%);z-index:10;display:flex;flex-direction:column;gap:1px;pointer-events:all}}
.si{{display:flex;align-items:center;gap:6px;padding:3px 8px;border-radius:3px;cursor:pointer;transition:all 0.2s;border:1px solid transparent}}
.si:hover{{background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.06)}}
.si.act{{background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.12)}}
.sd2{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.sn2{{font-size:8px;color:#445;letter-spacing:0.5px;white-space:nowrap}}
.si.act .sn2,.si:hover .sn2{{color:#889}}
#controls{{position:fixed;top:70px;left:22px;z-index:10;font-size:10px;color:#555;letter-spacing:1px;pointer-events:all}}
#controls input{{vertical-align:middle;accent-color:#f97316}}
#controls label{{cursor:pointer;margin-right:8px}}
.ctrl-row{{margin-bottom:5px;display:flex;align-items:center;gap:2px}}
.ctrl-sep{{height:1px;background:#1a1a22;margin:6px 0}}
#hint{{position:fixed;bottom:20px;right:20px;z-index:10;font-size:9px;color:#222;letter-spacing:1px;text-align:right;line-height:1.9}}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud">
  <h1>Yggdrasil \u00b7 La Pluie v3</h1>
  <div class="sub">{n_vivant} vivants \u00b7 {n_musee} mus\u00e9e \u00b7 {n_domains} domaines \u00b7 9 continents</div>
</div>
<div id="info">
  <div class="sn" id="sn">\u2014</div>
  <div class="sf" id="sf"></div>
  <div class="sd" id="sd"></div>
  <div class="sl" id="sl"></div>
</div>
<div id="controls">
  <div class="ctrl-row">
    <label><input type="radio" name="cube" value="vivant" checked onchange="switchCube()"> Vivant</label>
    <label><input type="radio" name="cube" value="musee" onchange="switchCube()"> Mus\u00e9e</label>
    <label><input type="radio" name="cube" value="fusion" onchange="switchCube()"> Fusion</label>
  </div>
  <div class="ctrl-sep"></div>
  <div class="ctrl-row">
    <label><input type="checkbox" id="toggleEsc" onchange="toggleEsc()"> \U0001F33F Escaliers</label>
    <label><input type="checkbox" id="toggleRte" onchange="toggleRte()"> \U0001F30F Routes</label>
    <label><input type="checkbox" id="toggleC2" onchange="toggleC2mode()"> C2 Conjectures</label>
  </div>
</div>
<div id="strate-legend"></div>
<div id="cont-panel"></div>
<div id="hint"><kbd>drag</kbd> rotation \u00b7 <kbd>scroll</kbd> zoom \u00b7 <kbd>clic</kbd> continent \u00b7 <kbd>espace</kbd> pause</div>
<script>
{ST_C1_LINE}
{CTR_C1_LINE}
{ST_C2_LINE}
{CTR_C2_LINE}
let currentST=ST_C1,currentCTR=CTR_C1;
{dc_js}
{dl_js}
{esc_geo_js}
{esc_key_js}
{rte_geo_js}
{rte_key_js}
{rte_c_js}

// \u2550\u2550\u2550 State \u2550\u2550\u2550
let cubeMode='vivant'; // 'vivant','musee','fusion'
let showEsc=false;
let showRte=false;
let showC2=false;
const activeDomains=new Set();
let activeContinent=null;
let activeS=-1;

// \u2550\u2550\u2550 Continent \u2192 Domains mapping \u2550\u2550\u2550
const CONTINENTS=[
  {{id:'chimie',icon:'\U0001F7E0',name:'CHIMIE & MAT\u00c9RIAUX',
    doms:['chimie','chimie organique','polym\u00e8res','nanotechnologie','\u00e9lectrochimie','mat\u00e9riaux']}},
  {{id:'bio',icon:'\U0001F7E2',name:'BIO & M\u00c9DECINE',
    doms:['biologie','m\u00e9decine','immunologie','pharmacologie','g\u00e9nomique','biom\u00e9dical','oncologie','bioinformatique','neurosciences','\u00e9pid\u00e9miologie']}},
  {{id:'terre',icon:'\U0001F30D',name:'TERRE & VIVANT',
    doms:['g\u00e9osciences','climatologie','oc\u00e9anographie','\u00e9cologie','environnement','sismologie','volcanologie','agronomie','\u00e9volution']}},
  {{id:'physique',icon:'\U0001F535',name:'PHYSIQUE',
    doms:['m\u00e9canique','quantique','relativit\u00e9','particules','QFT','nucl\u00e9aire','cosmologie','m\u00e9canique stat','astronomie','m\u00e9canique analytique','gravitation']}},
  {{id:'ingenierie',icon:'\u2699\uFE0F',name:'ING\u00c9NIERIE & TECHNO',
    doms:['ing\u00e9nierie','a\u00e9rospatiale','\u00e9lectromagn','optique','signal','t\u00e9l\u00e9communications','robotique','\u00e9nergie','fluides','thermo','contr\u00f4le']}},
  {{id:'math',icon:'\U0001F7E3',name:'MATH PURE',
    doms:['alg\u00e8bre','analyse','topologie','g\u00e9om\u00e9trie','EDP','probabilit\u00e9s','combinatoire','nb th\u00e9orie',
      'ensembles','cat\u00e9gories','syst\u00e8mes dynamiques','alg\u00e8bre lin','analyse fonctionnelle',
      'g\u00e9om alg\u00e9brique','g\u00e9om diff','analyse num\u00e9rique','trigonom\u00e9trie',
      'arithm\u00e9tique','nombres','nb premiers','complexes','ordinaux','stochastique','mesure']}},
  {{id:'info',icon:'\U0001F4BB',name:'INFO & MATH DISCR\u00c8TE',
    doms:['informatique','complexit\u00e9','calculabilit\u00e9','automates','logique','crypto','optimisation','ML','vision','information','NLP']}},
  {{id:'humaines',icon:'\U0001F534',name:'SCIENCES HUMAINES',
    doms:['\u00e9conomie','finance','sociologie','psychologie','linguistique','\u00e9ducation','histoire','anthropologie','science politique','d\u00e9mographie','droit']}},
  {{id:'transversal',icon:'\u25C7',name:'TRANSVERSAL',
    doms:['science g\u00e9n\u00e9rale','statistiques','descriptive']}}
];
const DOM_TO_CONT={{}};
CONTINENTS.forEach(c=>c.doms.forEach(d=>DOM_TO_CONT[d]=c.id));

// \u2550\u2550\u2550 Canvas \u2550\u2550\u2550
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
let W,H;function resize(){{W=cv.width=innerWidth;H=cv.height=innerHeight}}resize();addEventListener('resize',resize);
const BOX={{w:3.8,h:3.8,d:3.8}},CAM={{dist:7.0,scale:420,persp:0.18}},SHRINK=0.85;
let yaw=0,yawSpd=0.004,tiltX=-0.32,zoom=1.0;
let dragging=false,pm={{x:0,y:0}},autoRot=true,autoT=null,mouseX=0,mouseY=0,time=0;

cv.addEventListener('mousedown',e=>{{dragging=true;pm={{x:e.clientX,y:e.clientY}};autoRot=false;clearTimeout(autoT)}});
addEventListener('mousemove',e=>{{mouseX=e.clientX;mouseY=e.clientY;if(!dragging)return;yaw+=(e.clientX-pm.x)*0.005;tiltX+=(e.clientY-pm.y)*0.004;tiltX=Math.max(-1.3,Math.min(1.3,tiltX));pm={{x:e.clientX,y:e.clientY}}}});
addEventListener('mouseup',()=>{{dragging=false;autoT=setTimeout(()=>autoRot=true,3000)}});
cv.addEventListener('wheel',e=>{{e.preventDefault();zoom*=e.deltaY>0?0.95:1.05;zoom=Math.max(0.3,Math.min(3,zoom))}},{{passive:false}});
cv.addEventListener('touchstart',e=>{{if(e.touches.length===1){{dragging=true;pm={{x:e.touches[0].clientX,y:e.touches[0].clientY}};autoRot=false;clearTimeout(autoT)}}}});
cv.addEventListener('touchmove',e=>{{if(!dragging||e.touches.length!==1)return;e.preventDefault();const t=e.touches[0];yaw+=(t.clientX-pm.x)*0.005;tiltX+=(t.clientY-pm.y)*0.004;tiltX=Math.max(-1.3,Math.min(1.3,tiltX));pm={{x:t.clientX,y:t.clientY}}}},{{passive:false}});
cv.addEventListener('touchend',()=>{{dragging=false;autoT=setTimeout(()=>autoRot=true,3000)}});
addEventListener('keydown',e=>{{if(e.key===' '){{autoRot=!autoRot;e.preventDefault()}}}});

function project(x,y,z){{
  const cy=Math.cos(yaw),sy=Math.sin(yaw),x1=x*cy+z*sy,z1=-x*sy+z*cy;
  const cx=Math.cos(tiltX),sx=Math.sin(tiltX),y2=y*cx-z1*sx,z2=y*sx+z1*cx;
  const sc=CAM.scale*zoom,den=Math.max(0.001,CAM.dist-z2),pf=sc/den,of=sc/CAM.dist,f=of+(pf-of)*CAM.persp;
  return{{x:x1*f+W/2,y:-y2*f+H/2,z:z2,f}}
}}
function rgba(c,a){{return`rgba(${{c[0]}},${{c[1]}},${{c[2]}},${{a}})`}}

// \u2550\u2550\u2550 Mode switching \u2550\u2550\u2550
function switchCube(){{
  cubeMode=document.querySelector('input[name="cube"]:checked').value;
  activeS=-1;buildStrateLegend();
}}
function toggleEsc(){{showEsc=document.getElementById('toggleEsc').checked}}
function toggleRte(){{showRte=document.getElementById('toggleRte').checked}}
function toggleC2mode(){{
  showC2=document.getElementById('toggleC2').checked;
  activeS=-1;buildStrateLegend();
}}

// \u2550\u2550\u2550 Continent panel \u2550\u2550\u2550
const contPanel=document.getElementById('cont-panel');
function domCountInContinent(cont){{
  let total=0;
  cont.doms.forEach(d=>{{const found=DL.find(x=>x[0]===d);if(found)total+=found[1]}});
  return total;
}}

function buildContPanel(){{
  contPanel.innerHTML='';
  CONTINENTS.forEach(cont=>{{
    const total=domCountInContinent(cont);
    const btn=document.createElement('div');btn.className='cb';btn.dataset.cont=cont.id;
    btn.innerHTML=`<span class="cb-icon">${{cont.icon}}</span><span class="cb-name">${{cont.name}}</span><span class="cb-count">${{total}}</span>`;
    btn.addEventListener('click',()=>{{
      if(activeContinent===cont.id){{activeContinent=null;activeDomains.clear()}}
      else{{activeContinent=cont.id;activeDomains.clear();cont.doms.forEach(d=>activeDomains.add(d))}}
      updateContUI();
    }});
    contPanel.appendChild(btn);
    const subDiv=document.createElement('div');subDiv.className='sub-doms';subDiv.dataset.cont=cont.id;
    cont.doms.forEach(d=>{{
      const found=DL.find(x=>x[0]===d);const cnt=found?found[1]:0;
      if(cnt===0)return;
      const c=DC[d]||[128,128,128];
      const el=document.createElement('div');el.className='sd-item';el.dataset.dom=d;
      el.innerHTML=`<div class="sd-dot" style="background:rgb(${{c[0]}},${{c[1]}},${{c[2]}})"></div><span class="sd-name">${{d}}</span><span class="sd-cnt">${{cnt}}</span>`;
      el.addEventListener('click',e=>{{
        e.stopPropagation();
        if(activeDomains.size===1&&activeDomains.has(d)){{
          activeDomains.clear();const cc=CONTINENTS.find(x=>x.id===activeContinent);
          if(cc)cc.doms.forEach(dd=>activeDomains.add(dd));
        }}else{{activeDomains.clear();activeDomains.add(d)}}
        updateContUI();
      }});
      subDiv.appendChild(el);
    }});
    contPanel.appendChild(subDiv);
  }});
  const reset=document.createElement('div');reset.id='cont-reset';reset.textContent='TOUT';
  reset.addEventListener('click',()=>{{activeContinent=null;activeDomains.clear();updateContUI()}});
  contPanel.appendChild(reset);
}}

function updateContUI(){{
  const hasFilter=activeContinent!==null;
  contPanel.querySelectorAll('.cb').forEach(el=>{{
    const cid=el.dataset.cont;
    el.classList.toggle('act',cid===activeContinent);
    el.classList.toggle('dim',hasFilter&&cid!==activeContinent);
  }});
  contPanel.querySelectorAll('.sub-doms').forEach(el=>{{
    el.classList.toggle('open',el.dataset.cont===activeContinent);
  }});
  contPanel.querySelectorAll('.sd-item').forEach(el=>{{
    const d=el.dataset.dom;const isSolo=activeDomains.size===1;
    el.classList.toggle('act',activeDomains.has(d));
    el.classList.toggle('dim',isSolo&&!activeDomains.has(d));
  }});
}}
buildContPanel();

// \u2550\u2550\u2550 Strate legend (left) \u2550\u2550\u2550
const strateLeg=document.getElementById('strate-legend');
function buildStrateLegend(){{
  strateLeg.innerHTML='';
  currentST.forEach((s,i)=>{{
    const el=document.createElement('div');el.className='si';
    el.innerHTML=`<div class="sd2" style="background:rgb(${{s.c}})"></div><div class="sn2">${{s.sh}} <span style="color:#334">${{s.sy.length}}</span></div>`;
    el.addEventListener('click',()=>{{activeS=activeS===i?-1:i;strateLeg.querySelectorAll('.si').forEach((el2,j)=>el2.classList.toggle('act',j===activeS))}});
    strateLeg.appendChild(el);
  }});
}}
buildStrateLegend();

// \u2550\u2550\u2550 Cube edges \u2550\u2550\u2550
const CE=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
function bv(){{const h=BOX.w/2,hy=BOX.h/2,hz=BOX.d/2;return[[-h,-hy,-hz],[h,-hy,-hz],[h,hy,-hz],[-h,hy,-hz],[-h,-hy,hz],[h,-hy,hz],[h,hy,hz],[-h,hy,hz]]}}

// \u2550\u2550\u2550 Cube filter helper \u2550\u2550\u2550
function cubeVisible(cb){{
  // cb: 0=vivant, 1=mus\u00e9e, 2=always
  if(cb===2) return true;
  if(cubeMode==='fusion') return true;
  if(cubeMode==='vivant') return cb===0;
  return cb===1; // musee mode
}}

// \u2550\u2550\u2550 Render \u2550\u2550\u2550
function frame(){{
  requestAnimationFrame(frame);
  time+=0.003;
  ctx.clearRect(0,0,W,H);
  const gr=ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,W*0.7);
  gr.addColorStop(0,'#0d0d14');gr.addColorStop(1,'#050508');
  ctx.fillStyle=gr;ctx.fillRect(0,0,W,H);
  if(autoRot)yaw+=yawSpd;

  const vts=bv().map(v=>project(v[0],v[1],v[2]));
  ctx.strokeStyle='rgba(255,255,255,0.025)';ctx.lineWidth=0.5;
  CE.forEach(([a,b])=>{{ctx.beginPath();ctx.moveTo(vts[a].x,vts[a].y);ctx.lineTo(vts[b].x,vts[b].y);ctx.stroke()}});

  const hasDomFilter=activeDomains.size>0;
  const items=[];

  // C1 symbols
  currentST.forEach((st,si)=>{{
    const y=st.yr*BOX.h;
    let sop=0.85;
    if(activeS>=0)sop=si===activeS?1:0.04;

    const sh=SHRINK,hw=BOX.w*sh/2,hd=BOX.d*sh/2;
    const qv=[[-hw,y,-hd],[hw,y,-hd],[hw,y,hd],[-hw,y,hd]];
    const pq=qv.map(v=>project(v[0],v[1],v[2]));
    const avgZ=pq.reduce((a,p)=>a+p.z,0)/4;
    let planeOp=st.op*0.3;
    if(activeS>=0)planeOp=si===activeS?0.12:0.005;
    items.push({{type:'p',z:avgZ-0.01,si,pts:pq,col:st.c,op:planeOp}});

    const rot=time*(0.3-si*0.035);
    const cr=Math.cos(rot),sr=Math.sin(rot);

    st.sy.forEach(sym=>{{
      const isCentre=sym[3]===1;
      const cb=sym[5]; // cube: 0=vivant, 1=musee, 2=always
      if(!cubeVisible(cb))return; // skip hidden by cube filter

      let ox=sym[1],oz=sym[2];
      if(!isCentre){{const rx=ox*cr-oz*sr;const rz=ox*sr+oz*cr;ox=rx;oz=rz}}
      const pp=project(ox,y,oz);
      const dom=sym[4];
      const domCol=DC[dom]||st.c;
      let finalOp=sop;
      // Musee symbols slightly dimmer in fusion mode
      if(cubeMode==='fusion'&&cb===1)finalOp*=0.45;
      if(hasDomFilter&&!activeDomains.has(dom))finalOp*=0.03;
      const isEsc=showEsc&&(ESC_GEO.has(sym[0])||ESC_KEY.has(sym[0]));
      items.push({{type:'s',z:pp.z,si,sym,px:pp.x,py:pp.y,pf:pp.f,col:domCol,sop:finalOp,isCentre,isC2:false,isEsc}});
    }});
  }});

  // C2 overlay
  if(showC2){{
    ST_C2.forEach((st,si)=>{{
      const y=st.yr*BOX.h;
      let sop=0.55;
      if(activeS>=0)sop=si===activeS?0.7:0.03;
      const rot=time*(0.3-si*0.035);
      const cr=Math.cos(rot),sr=Math.sin(rot);
      st.sy.forEach(sym=>{{
        const isCentre=sym[3]===1;
        let ox=sym[1],oz=sym[2];
        if(!isCentre){{const rx=ox*cr-oz*sr;const rz=ox*sr+oz*cr;ox=rx;oz=rz}}
        const pp=project(ox,y,oz);
        const dom=sym[4];
        const domCol=DC[dom]||st.c;
        let finalOp=sop;
        if(hasDomFilter&&!activeDomains.has(dom))finalOp*=0.03;
        items.push({{type:'s',z:pp.z,si,sym,px:pp.x,py:pp.y,pf:pp.f,col:domCol,sop:finalOp,isCentre,isC2:true,isEsc:false}});
      }});
    }});
  }}

  items.sort((a,b)=>a.z-b.z);
  const sc0=CAM.scale*zoom/CAM.dist;
  let ns=null,nd=18;

{route_render_js}

  items.forEach(it=>{{
    if(it.type==='p'){{
      ctx.beginPath();ctx.moveTo(it.pts[0].x,it.pts[0].y);
      for(let i=1;i<4;i++)ctx.lineTo(it.pts[i].x,it.pts[i].y);
      ctx.closePath();ctx.fillStyle=rgba(it.col,it.op);ctx.fill();
      ctx.strokeStyle=rgba(it.col,it.op*2);ctx.lineWidth=0.5;ctx.stroke();
    }}
    if(it.type==='s'){{
      if(it.isCentre){{
        const bs=Math.max(12,Math.min(26,18*(it.pf/sc0)));
        ctx.shadowColor=`rgb(${{it.col[0]}},${{it.col[1]}},${{it.col[2]}})`;ctx.shadowBlur=16;
        ctx.font=`700 ${{bs}}px "JetBrains Mono",monospace`;
        ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.fillStyle=rgba(it.col,it.sop);ctx.fillText(it.sym[0],it.px,it.py);
        ctx.shadowBlur=0;
        ctx.fillStyle=`rgba(255,255,255,${{it.sop*0.5}})`;
        ctx.font=`700 ${{bs*0.7}}px "JetBrains Mono",monospace`;
        ctx.fillText(it.sym[0],it.px,it.py);
      }}else{{
        const dotR=Math.max(0.6,Math.min(2.2,1.5*(it.pf/sc0)));
        const dx=mouseX-it.px,dy=mouseY-it.py,dist=Math.sqrt(dx*dx+dy*dy);
        if(dist<14&&dist<nd){{nd=dist;ns=it}}

        // Escalier glow
        if(it.isEsc){{
          const isGeo=ESC_GEO.has(it.sym[0]);
          const glowCol=isGeo?[100,255,160]:[255,220,80]; // green for geo, gold for key
          ctx.beginPath();ctx.arc(it.px,it.py,dotR*5,0,Math.PI*2);
          ctx.fillStyle=rgba(glowCol,it.sop*0.15);ctx.fill();
          ctx.beginPath();ctx.arc(it.px,it.py,dotR*2.5,0,Math.PI*2);
          ctx.fillStyle=rgba(glowCol,it.sop*0.4);ctx.fill();
        }}

        if(dist<14){{
          ctx.beginPath();ctx.arc(it.px,it.py,dotR*3.5,0,Math.PI*2);
          ctx.fillStyle=rgba(it.col,Math.min(1,it.sop*1.3));ctx.fill();
        }}else{{
          ctx.beginPath();ctx.arc(it.px,it.py,it.isEsc?dotR*1.8:dotR,0,Math.PI*2);
          ctx.fillStyle=rgba(it.col,it.sop*(it.isEsc?0.9:0.65));ctx.fill();
        }}
      }}
    }}
  }});

  // Hover tooltip
  if(ns){{
    const s=ns.sym;
    const c=ns.col;
    const contId=DOM_TO_CONT[s[4]]||'';
    const contInfo=CONTINENTS.find(x=>x.id===contId);
    document.getElementById('sn').textContent=s[0];
    document.getElementById('sn').style.color=`rgb(${{c[0]}},${{c[1]}},${{c[2]}})`;
    const wcStr=s[6]>0?' \u00b7 '+s[6].toLocaleString()+' papers':'';
    document.getElementById('sf').textContent=s[4]+(contInfo?' \u00b7 '+contInfo.icon+' '+contInfo.name:'')+wcStr;
    document.getElementById('sf').style.color=`rgb(${{c[0]}},${{c[1]}},${{c[2]}})`;
    const stName=currentST[ns.si]?.sh||'';
    const cubeStr=s[5]===0?'vivant':s[5]===1?'mus\u00e9e':'';
    const escStr=ESC_GEO.has(s[0])?' \u00b7 \U0001F33F liane g\u00e9o':ESC_KEY.has(s[0])?' \u00b7 \U0001F511 passe-partout':'';
    document.getElementById('sd').textContent=stName;
    document.getElementById('sl').textContent=(ns.isC2?'C2 conjecture':'C1')+(cubeStr?' \u00b7 '+cubeStr:'')+escStr;
    ctx.strokeStyle=rgba(c,0.3);ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(ns.px-20,ns.py);ctx.lineTo(ns.px+20,ns.py);ctx.stroke();
    ctx.beginPath();ctx.moveTo(ns.px,ns.py-20);ctx.lineTo(ns.px,ns.py+20);ctx.stroke();
  }}

  // Axis labels
  const bot=project(0,-BOX.h/2-0.35,0),top2=project(0,BOX.h/2+0.35,0);
  ctx.font='500 8px "JetBrains Mono",monospace';ctx.textAlign='center';
  ctx.fillStyle='rgba(74,222,128,0.25)';ctx.fillText('SOL',bot.x,bot.y);
  ctx.fillStyle='rgba(239,68,68,0.25)';ctx.fillText('PLAFOND',top2.x,top2.y);
}}

frame();
</script>
</body>
</html>'''

with open(V3_HTML, 'w', encoding='utf-8') as f:
    f.write(v3_html)

sz = os.path.getsize(V3_HTML)
print(f"\nv3 written: {sz:,} bytes ({sz/1024:.0f} KB)")
print(f"  -> {V3_HTML}")
