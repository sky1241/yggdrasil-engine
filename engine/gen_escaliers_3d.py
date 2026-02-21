#!/usr/bin/env python3
"""
🌿 GEN ESCALIERS 3D — Yggdrasil Engine
Generates viz/yggdrasil_escaliers_3d.html from:
  - data/escaliers_unified.json (300 geo + 69 key + centroids)
  - data/strates_export_v2.json (S1-S6 symbols)

Pipeline: engine/gen_escaliers_3d.py → viz/yggdrasil_escaliers_3d.html

Sky × Claude — 21 février 2026, Versoix
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

print("=" * 60)
print("🌿 GEN ESCALIERS 3D — Yggdrasil Engine")
print("=" * 60)

# ══════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════
print("\n[1] Loading data...")

with open(ROOT / 'data' / 'escaliers_unified.json', encoding='utf-8') as f:
    esc = json.load(f)

with open(ROOT / 'data' / 'strates_export_v2.json', encoding='utf-8') as f:
    strates = json.load(f)['strates']

# ══════════════════════════════════════════════════
# PREPARE INLINE DATA
# ══════════════════════════════════════════════════
print("\n[2] Preparing data for JS...")

# Centroids: {name: [px, pz]}
centroids_js = {}
for name, c in esc['centroids'].items():
    centroids_js[name] = [round(c['px'], 4), round(c['pz'], 4)]

# Geo: [{s, f, px, pz, home, alien, sc}]
geo_js = []
for g in esc['geo'][:300]:
    geo_js.append({
        's': g['s'], 'f': g['from'],
        'px': round(g['px'], 4), 'pz': round(g['pz'], 4),
        'home': g['home'], 'alien': g['alien'],
        'sc': round(g['score'], 3)
    })

# Key: [{s, f, px, pz, home, nc, sc, conts}] — WITH conts array!
key_js = []
for k in esc['key']:
    key_js.append({
        's': k['s'], 'f': k['from'],
        'px': round(k['px'], 4), 'pz': round(k['pz'], 4),
        'home': k['home'], 'nc': k['n_continents'],
        'sc': round(k['score'], 3),
        'conts': k['continents']
    })

# Upper strates: [{s, f, px, pz, st, dom, c2?}]
upper_js = []
for st in strates:
    if st['id'] < 1:
        continue
    for sym in st['symbols']:
        entry = {
            's': sym['s'], 'f': sym['from'],
            'px': round(sym['px'], 4), 'pz': round(sym['pz'], 4),
            'st': st['id'], 'dom': sym['domain']
        }
        if sym.get('class') == 'C2':
            entry['c2'] = True
        upper_js.append(entry)

D = {'c': centroids_js, 'g': geo_js, 'k': key_js, 'u': upper_js}
data_json = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
n_geo = len(geo_js)
n_key = len(key_js)
n_upper = len(upper_js)

print(f"  Data: {len(data_json):,} chars")
print(f"  Geo: {n_geo}, Key: {n_key}, Upper: {n_upper}")
print(f"  Centroids: {list(centroids_js.keys())}")

# ══════════════════════════════════════════════════
# HTML TEMPLATE
# ══════════════════════════════════════════════════
print("\n[3] Generating HTML...")

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Yggdrasil — Escaliers 3D</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{overflow:hidden;background:#0a0a12;font-family:'Segoe UI',system-ui,sans-serif;color:#e0e0e0}
canvas{display:block}
#panel{position:fixed;top:10px;left:10px;background:rgba(10,10,18,0.92);border:1px solid #333;border-radius:8px;padding:12px 16px;z-index:10;min-width:220px;backdrop-filter:blur(8px)}
#panel h3{font-size:14px;color:#4ade80;margin-bottom:10px;letter-spacing:1px}
.lbl{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;padding:2px 0}
.lbl:hover{color:#fff}
.lbl input{accent-color:#4ade80}
.sep{height:1px;background:#333;margin:8px 0}
#info{position:fixed;top:10px;right:10px;text-align:right;z-index:10}
#info h2{font-size:16px;color:#4ade80;margin-bottom:4px}
#info .sub{font-size:11px;color:#888}
#tt{position:fixed;display:none;background:rgba(10,10,18,0.95);border:1px solid #555;border-radius:6px;padding:8px 12px;font-size:12px;pointer-events:none;z-index:20;max-width:300px;backdrop-filter:blur(4px)}
.tn{font-weight:bold;color:#fff;font-size:13px}
.tf{color:#aaa;font-size:11px}
.td{color:#4ade80;font-size:11px;margin-top:3px}
.tr{color:#fa8;font-size:11px;margin-top:2px}
#legend{position:fixed;bottom:10px;left:10px;background:rgba(10,10,18,0.85);border:1px solid #333;border-radius:6px;padding:8px 12px;font-size:11px;z-index:10}
.lr{display:flex;align-items:center;gap:6px;margin:2px 0}
.ld{width:10px;height:10px;border-radius:50%;display:inline-block}
</style>
</head>
<body>

<div id="panel">
  <h3>🌿 ESCALIERS 3D</h3>
  <label class="lbl"><input type="checkbox" id="chk-planes" checked onchange="tog('planes')"> Strate planes</label>
  <label class="lbl"><input type="checkbox" id="chk-grid" checked onchange="tog('grid')"> Grille S0</label>
  <label class="lbl"><input type="checkbox" id="chk-centroids" checked onchange="tog('centroids')"> Centroïdes (9)</label>
  <div class="sep"></div>
  <label class="lbl"><input type="checkbox" id="chk-geo" checked onchange="tog('geo')"> 🌿 Geo escaliers (__N_GEO__)</label>
  <label class="lbl"><input type="checkbox" id="chk-key" checked onchange="tog('key')"> 🔑 Key escaliers (__N_KEY__)</label>
  <label class="lbl"><input type="checkbox" id="chk-upper" checked onchange="tog('upper')"> S1-S6 symboles (__N_UPPER__)</label>
  <div class="sep"></div>
  <label class="lbl"><input type="checkbox" id="chk-georte" checked onchange="tog('georte')"> 🌿 Geo routes (orange)</label>
  <label class="lbl"><input type="checkbox" id="chk-keyrte" checked onchange="tog('keyrte')"> 🔑 Key routes (cyan)</label>
</div>

<div id="info">
  <h2>YGGDRASIL — Escaliers 3D</h2>
  <div class="sub">__N_GEO__ geo 🌿 + __N_KEY__ key 🔑 + __N_UPPER__ S1-S6</div>
  <div class="sub">9 continents · 7 strates</div>
</div>

<div id="tt"></div>

<div id="legend">
  <div class="lr"><span class="ld" style="background:#4ade80"></span> Geo escalier (vert)</div>
  <div class="lr"><span class="ld" style="background:#fbbf24"></span> Key escalier (or)</div>
  <div class="lr"><span class="ld" style="background:#ff6b35"></span> Geo route → alien</div>
  <div class="lr"><span class="ld" style="background:#35d4ff"></span> Key route → continents</div>
  <div class="lr"><span class="ld" style="background:#a78bfa"></span> S1-S6 symbole</div>
  <div class="lr"><span class="ld" style="background:#ff6b6b"></span> C2 conjecture</div>
</div>

<script src="https://unpkg.com/three@0.128.0/build/three.min.js"></script>
<script src="https://unpkg.com/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
'use strict';

// ═══════════════════════════════════════════════
// DATA (generated from escaliers_unified.json)
// ═══════════════════════════════════════════════
const D = __DATA__;

// ═══════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════
const SCALE = 200;
const GAP = 80;

const CC = {
  math:0xb450ff, physique:0x3c78ff, ingenierie:0xb4b43c,
  chimie:0xffa500, info:0x00b4dc, transversal:0x787878,
  bio:0x00c850, humaines:0xdc3c3c, terre:0x64b464
};
const CN = {
  math:'MATH', physique:'PHYSIQUE', ingenierie:'INGÉNIERIE',
  chimie:'CHIMIE', info:'INFO', transversal:'TRANSVERSAL',
  bio:'BIO', humaines:'HUMAINES', terre:'TERRE'
};

// ═══════════════════════════════════════════════
// GLOBALS
// ═══════════════════════════════════════════════
let scene, camera, renderer, controls;
const mouse = new THREE.Vector2(-999, -999);
const raycaster = new THREE.Raycaster();
const hov = [];
const layers = {};
const tt = document.getElementById('tt');
let mx = 0, my = 0;

function tw(px, pz, st) {
  return new THREE.Vector3(px * SCALE, (st || 0) * GAP, pz * SCALE);
}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════
function init() {
  const W = innerWidth, H = innerHeight;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a12);
  scene.fog = new THREE.FogExp2(0x0a0a12, 0.0008);

  camera = new THREE.PerspectiveCamera(55, W / H, 1, 5000);
  camera.position.set(50, 350, 500);
  camera.lookAt(0, 40, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  document.body.appendChild(renderer.domElement);

  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 40, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.minDistance = 50;
  controls.maxDistance = 2000;
  controls.update();

  // Lights
  scene.add(new THREE.AmbientLight(0x404060, 0.6));
  const dl = new THREE.DirectionalLight(0xffffff, 0.7);
  dl.position.set(200, 400, 200);
  scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0x8080ff, 0.3);
  dl2.position.set(-200, 200, -200);
  scene.add(dl2);

  // Build
  buildGrid();
  buildPlanes();
  buildCentroids();
  buildGeo();
  buildKey();
  buildUpper();
  buildGeoRte();
  buildKeyRte();

  addEventListener('resize', onResize);
  renderer.domElement.addEventListener('mousemove', onMouse);

  animate();
}

// ═══════════════════════════════════════════════
// LAYER HELPERS
// ═══════════════════════════════════════════════
function mkLayer(name) {
  const g = new THREE.Group();
  g.name = name;
  layers[name] = g;
  scene.add(g);
  return g;
}

function tog(name) {
  if (layers[name]) layers[name].visible = document.getElementById('chk-' + name).checked;
}

// ═══════════════════════════════════════════════
// BUILD: GRID
// ═══════════════════════════════════════════════
function buildGrid() {
  const g = mkLayer('grid');
  const grid = new THREE.GridHelper(600, 30, 0x1a3a1a, 0x111118);
  grid.material.opacity = 0.25;
  grid.material.transparent = true;
  g.add(grid);
}

// ═══════════════════════════════════════════════
// BUILD: STRATE PLANES
// ═══════════════════════════════════════════════
function buildPlanes() {
  const g = mkLayer('planes');
  for (let s = 0; s <= 6; s++) {
    const geo = new THREE.PlaneGeometry(600, 600);
    const mat = new THREE.MeshBasicMaterial({
      color: s === 0 ? 0x1a2a1a : 0x1a1a2a,
      transparent: true, opacity: s === 0 ? 0.12 : 0.04,
      side: THREE.DoubleSide, depthWrite: false
    });
    const plane = new THREE.Mesh(geo, mat);
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = s * GAP;
    g.add(plane);

    const lbl = mkLbl(s === 0 ? 'S0 — SOL' : 'S' + s, s === 0 ? '#4ade80' : '#8888aa', s === 0 ? 24 : 18);
    lbl.position.set(-310, s * GAP + 5, 0);
    g.add(lbl);
  }
}

// ═══════════════════════════════════════════════
// BUILD: CENTROIDS
// ═══════════════════════════════════════════════
function buildCentroids() {
  const g = mkLayer('centroids');
  const sGeo = new THREE.SphereGeometry(4, 16, 16);

  for (const [name, [px, pz]] of Object.entries(D.c)) {
    const col = CC[name] || 0x888888;
    const pos = tw(px, pz);
    pos.y = 2;

    // Sphere
    const mat = new THREE.MeshPhongMaterial({ color: col, emissive: col, emissiveIntensity: 0.3 });
    const mesh = new THREE.Mesh(sGeo, mat);
    mesh.position.copy(pos);
    g.add(mesh);

    // Glow ring
    const rGeo = new THREE.RingGeometry(6, 10, 32);
    const rMat = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.25, side: THREE.DoubleSide, depthWrite: false });
    const ring = new THREE.Mesh(rGeo, rMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.copy(pos);
    ring.position.y = 0.5;
    g.add(ring);

    // Label
    const lbl = mkLbl(CN[name] || name, '#' + col.toString(16).padStart(6, '0'), 18);
    lbl.position.copy(pos);
    lbl.position.y = 14;
    g.add(lbl);

    mesh.userData = { t: 'centroid', name: CN[name], cont: name };
    hov.push(mesh);
  }
}

// ═══════════════════════════════════════════════
// BUILD: GEO ESCALIERS (vertical green lines)
// ═══════════════════════════════════════════════
function buildGeo() {
  const g = mkLayer('geo');
  const sGeo = new THREE.SphereGeometry(1.5, 8, 8);
  const sMat = new THREE.MeshPhongMaterial({ color: 0x4ade80, emissive: 0x4ade80, emissiveIntensity: 0.4 });

  for (const e of D.g) {
    const base = tw(e.px, e.pz);
    const top = base.clone();
    top.y = e.sc * GAP;

    // Vertical line
    const lGeo = new THREE.BufferGeometry().setFromPoints([base, top]);
    const lMat = new THREE.LineBasicMaterial({ color: 0x4ade80, transparent: true, opacity: 0.5 });
    g.add(new THREE.Line(lGeo, lMat));

    // Top sphere
    const dot = new THREE.Mesh(sGeo, sMat);
    dot.position.copy(top);
    g.add(dot);

    dot.userData = { t: 'geo', s: e.s, f: e.f, home: e.home, alien: e.alien, sc: e.sc };
    hov.push(dot);
  }
}

// ═══════════════════════════════════════════════
// BUILD: KEY ESCALIERS (vertical gold lines)
// ═══════════════════════════════════════════════
function buildKey() {
  const g = mkLayer('key');
  const sGeo = new THREE.SphereGeometry(2, 8, 8);
  const sMat = new THREE.MeshPhongMaterial({ color: 0xfbbf24, emissive: 0xfbbf24, emissiveIntensity: 0.4 });

  for (const e of D.k) {
    const base = tw(e.px, e.pz);
    const top = base.clone();
    top.y = e.sc * GAP;

    const lGeo = new THREE.BufferGeometry().setFromPoints([base, top]);
    const lMat = new THREE.LineBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.6 });
    g.add(new THREE.Line(lGeo, lMat));

    const dot = new THREE.Mesh(sGeo, sMat);
    dot.position.copy(top);
    g.add(dot);

    // Label for high-connectivity keys
    if (e.nc >= 5) {
      const lbl = mkLbl(e.s, '#fbbf24', 13);
      lbl.position.copy(top);
      lbl.position.y += 6;
      g.add(lbl);
    }

    dot.userData = { t: 'key', s: e.s, f: e.f, home: e.home, nc: e.nc, conts: e.conts, sc: e.sc };
    hov.push(dot);
  }
}

// ═══════════════════════════════════════════════
// BUILD: UPPER STRATES (S1-S6 symbols)
// ═══════════════════════════════════════════════
function buildUpper() {
  const g = mkLayer('upper');
  const sGeo = new THREE.SphereGeometry(1.8, 8, 8);

  for (const u of D.u) {
    const col = u.c2 ? 0xff6b6b : 0xa78bfa;
    const mat = new THREE.MeshPhongMaterial({ color: col, emissive: col, emissiveIntensity: 0.3 });
    const dot = new THREE.Mesh(sGeo, mat);
    dot.position.copy(tw(u.px, u.pz, u.st));
    g.add(dot);

    dot.userData = { t: 'upper', s: u.s, f: u.f, st: u.st, dom: u.dom, c2: u.c2 };
    hov.push(dot);
  }
}

// ═══════════════════════════════════════════════
// BUILD: GEO ROUTES (orange arcs at S0)
// ═══════════════════════════════════════════════
function buildGeoRte() {
  const g = mkLayer('georte');

  for (const e of D.g) {
    const ac = D.c[e.alien];
    if (!ac) continue;
    const start = tw(e.px, e.pz);
    const end = tw(ac[0], ac[1]);
    const alpha = Math.min(0.7, e.sc * 0.8);
    const arc = mkArc(start, end, 0xff6b35, alpha, false);
    if (arc) g.add(arc);
  }
}

// ═══════════════════════════════════════════════
// BUILD: KEY ROUTES (cyan dashed arcs at S0)
// ═══════════════════════════════════════════════
function buildKeyRte() {
  const g = mkLayer('keyrte');

  for (const e of D.k) {
    for (const cont of e.conts) {
      if (cont === e.home) continue;
      const cc = D.c[cont];
      if (!cc) continue;
      const start = tw(e.px, e.pz);
      const end = tw(cc[0], cc[1]);
      const alpha = Math.min(0.6, 0.15 + e.nc * 0.05);
      const arc = mkArc(start, end, 0x35d4ff, alpha, true);
      if (arc) g.add(arc);
    }
  }
}

// ═══════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════
function mkArc(a, b, color, opacity, dashed) {
  const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
  const dist = a.distanceTo(b);
  if (dist < 1) return null;
  mid.y = dist * 0.22;

  const curve = new THREE.QuadraticBezierCurve3(a.clone(), mid, b.clone());
  const pts = curve.getPoints(24);
  const geo = new THREE.BufferGeometry().setFromPoints(pts);

  let mat;
  if (dashed) {
    mat = new THREE.LineDashedMaterial({
      color, transparent: true, opacity,
      dashSize: 4, gapSize: 3, depthWrite: false
    });
  } else {
    mat = new THREE.LineBasicMaterial({
      color, transparent: true, opacity, depthWrite: false
    });
  }

  const line = new THREE.Line(geo, mat);
  if (dashed) line.computeLineDistances();
  return line;
}

function mkLbl(text, color, size) {
  const cv = document.createElement('canvas');
  const ctx = cv.getContext('2d');
  cv.width = 256; cv.height = 64;
  ctx.font = `bold ${size || 16}px monospace`;
  ctx.fillStyle = color || '#fff';
  ctx.textAlign = 'center';
  ctx.fillText(text, 128, 42);
  const tex = new THREE.CanvasTexture(cv);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false });
  const sp = new THREE.Sprite(mat);
  sp.scale.set(40, 10, 1);
  return sp;
}

// ═══════════════════════════════════════════════
// INTERACTION
// ═══════════════════════════════════════════════
function onMouse(e) {
  mx = e.clientX; my = e.clientY;
  mouse.x = (e.clientX / innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / innerHeight) * 2 + 1;
}

function onResize() {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}

// ═══════════════════════════════════════════════
// ANIMATE
// ═══════════════════════════════════════════════
function animate() {
  requestAnimationFrame(animate);
  controls.update();

  // Raycaster hover
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(hov);

  // Find first visible hit (parent layer must be visible)
  let hit = null;
  for (const h of hits) {
    let p = h.object.parent;
    let vis = true;
    while (p) { if (!p.visible) { vis = false; break; } p = p.parent; }
    if (vis) { hit = h; break; }
  }

  if (hit) {
    const d = hit.object.userData;
    let html = '';

    if (d.t === 'geo') {
      html = `<div class="tn">🌿 ${d.s}</div>
        <div class="tf">${d.f}</div>
        <div class="td">Score: ${(d.sc*100).toFixed(0)}%</div>
        <div class="tr">${d.home} → ${d.alien}</div>`;
    } else if (d.t === 'key') {
      html = `<div class="tn">🔑 ${d.s}</div>
        <div class="tf">${d.f}</div>
        <div class="td">${d.nc} continents · Score: ${(d.sc*100).toFixed(0)}%</div>
        <div class="tr">${d.conts.join(' · ')}</div>`;
    } else if (d.t === 'upper') {
      html = `<div class="tn">${d.c2?'⚡':'🟣'} ${d.s}</div>
        <div class="tf">${d.f}</div>
        <div class="td">S${d.st} · ${d.dom}${d.c2?' · C2 conjecture':''}</div>`;
    } else if (d.t === 'centroid') {
      html = `<div class="tn">◉ ${d.name}</div>
        <div class="td">Centroïde continent</div>`;
    }

    tt.innerHTML = html;
    tt.style.display = 'block';
    tt.style.left = (mx + 15) + 'px';
    tt.style.top = (my - 10) + 'px';
  } else {
    tt.style.display = 'none';
  }

  renderer.render(scene, camera);
}

init();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════
# GENERATE
# ══════════════════════════════════════════════════
html = HTML.replace('__DATA__', data_json)
html = html.replace('__N_GEO__', str(n_geo))
html = html.replace('__N_KEY__', str(n_key))
html = html.replace('__N_UPPER__', str(n_upper))

out_path = ROOT / 'viz' / 'yggdrasil_escaliers_3d.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = out_path.stat().st_size / 1024
print(f"\n[4] Written: {out_path}")
print(f"  Size: {size_kb:.0f} KB")
print(f"  Geo: {n_geo} escaliers + routes")
print(f"  Key: {n_key} escaliers + routes (with conts array!)")
print(f"  Upper: {n_upper} S1-S6 symbols")
print(f"  Centroids: 9")
print(f"\n✅ GEN ESCALIERS 3D TERMINÉ")
print("=" * 60)
