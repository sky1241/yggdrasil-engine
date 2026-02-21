#!/usr/bin/env python3
"""
gen_viz_v3.py — Generates yggdrasil_rain_v3.html
Uses spectral positions from strates_export_v2.json.
95 domain colors, interactive legend with filters.
"""
import json, colorsys, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2_HTML = os.path.join(ROOT, 'viz', 'yggdrasil_rain_v2.html')
V3_HTML = os.path.join(ROOT, 'viz', 'yggdrasil_rain_v3.html')

# ── Extract data from v2 HTML ──
with open(V2_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

m1 = re.search(r'^(const ST_C1=\[.*?\];)$', html, re.MULTILINE)
m2 = re.search(r'^(const CTR_C1=\[.*?\];)$', html, re.MULTILINE)
m3 = re.search(r'^(const ST_C2=\[.*?\];)$', html, re.MULTILINE)
m4 = re.search(r'^(const CTR_C2=\[.*?\];)$', html, re.MULTILINE)
if not all([m1, m2, m3, m4]):
    raise ValueError("Cannot extract data from v2 HTML")

ST_C1_LINE = m1.group(1)
CTR_C1_LINE = m2.group(1)
ST_C2_LINE = m3.group(1)
CTR_C2_LINE = m4.group(1)

# Parse ST_C1 to count domains and total symbols
st_c1 = json.loads(ST_C1_LINE[len("const ST_C1="):-1])
st_c2 = json.loads(ST_C2_LINE[len("const ST_C2="):-1])
total_c1 = sum(len(s['sy']) for s in st_c1)
total_c2 = sum(len(s['sy']) for s in st_c2)

# Count domains across all strates
from collections import Counter
domain_counts = Counter()
for st in st_c1 + st_c2:
    for sym in st['sy']:
        domain_counts[sym[4]] += 1

sorted_domains = domain_counts.most_common()
n_domains = len(sorted_domains)
print(f"Total C1: {total_c1}, C2: {total_c2}")
print(f"Domains: {n_domains}")

# ── Generate domain colors ──
# Group domains by scientific family for better color coherence
FAMILY_HUES = {
    # Math: blue-purple (220-280)
    'algèbre': 230, 'algèbre lin': 225, 'topologie': 250, 'géométrie': 215,
    'géom diff': 210, 'géom algébrique': 245, 'nb théorie': 260, 'combinatoire': 270,
    'probabilités': 235, 'statistiques': 240, 'analyse': 220, 'analyse fonctionnelle': 228,
    'EDP': 205, 'optimisation': 218, 'ensembles': 275, 'logique': 265,
    'calculabilité': 255, 'complexité': 258, 'automates': 262, 'catégories': 248,
    'trigonométrie': 222, 'systèmes dynamiques': 238, 'analyse numérique': 212,
    'arithmétique': 268, 'descriptive': 272, 'nombres': 264, 'nb premiers': 266,
    'ordinaux': 278, 'complexes': 232, 'mesure': 226, 'stochastique': 236,
    'mécanique analytique': 208,
    # Physics: cyan-teal (170-200)
    'quantique': 185, 'mécanique': 175, 'thermo': 178, 'mécanique stat': 182,
    'fluides': 190, 'relativité': 188, 'cosmologie': 195, 'électromagn': 172,
    'nucléaire': 168, 'particules': 180, 'QFT': 192, 'optique': 176,
    'gravitation': 198,
    # CS/AI: violet-magenta (290-330)
    'informatique': 290, 'ML': 310, 'crypto': 295, 'signal': 300,
    'information': 305, 'vision': 315, 'NLP': 320, 'robotique': 325,
    'télécommunications': 298, 'contrôle': 302,
    # Chemistry: orange-yellow (30-60)
    'chimie': 35, 'chimie organique': 42, 'polymères': 48, 'électrochimie': 28,
    'nanotechnologie': 55, 'matériaux': 25,
    # Biology: green (90-140)
    'biologie': 120, 'écologie': 105, 'évolution': 130, 'immunologie': 100,
    'génomique': 135, 'oncologie': 95, 'bioinformatique': 140,
    # Medicine: red-pink (340-360, 0-20)
    'médecine': 350, 'neurosciences': 345, 'biomédical': 355,
    'pharmacologie': 5, 'épidémiologie': 10, 'psychologie': 340,
    # Earth: brown-olive (60-90)
    'géosciences': 70, 'climatologie': 80, 'sismologie': 65, 'volcanologie': 62,
    'océanographie': 85, 'agronomie': 75, 'environnement': 88,
    # Engineering: steel blue (200-220)
    'ingénierie': 200, 'aérospatiale': 202, 'énergie': 197,
    # Social: warm (15-30)
    'économie': 18, 'finance': 22, 'linguistique': 335, 'anthropologie': 330,
    'sociologie': 338, 'science politique': 15, 'démographie': 12,
    'droit': 8, 'éducation': 332, 'histoire': 20,
    # General: neutral
    'science générale': 160, 'astronomie': 193,
}

domain_colors = {}
for i, (domain, count) in enumerate(sorted_domains):
    hue = FAMILY_HUES.get(domain, (i * 360 / n_domains) % 360)
    # Vary saturation/lightness by rank within same hue family
    sat = 0.70 + 0.12 * ((i % 3) / 2)
    lit = 0.52 + 0.08 * ((i % 5) / 4)
    r, g, b = colorsys.hls_to_rgb(hue / 360, lit, sat)
    domain_colors[domain] = (int(r * 255), int(g * 255), int(b * 255))

# Generate JS color map
dc_js = "const DC={"
for domain, (r, g, b) in domain_colors.items():
    dc_js += f'"{domain}":[{r},{g},{b}],'
dc_js += "};"

# Domain list sorted by count for legend
dl_js = "const DL=" + json.dumps([[d, c] for d, c in sorted_domains], ensure_ascii=False) + ";"

print(f"Generated {n_domains} domain colors")
for d, c in sorted_domains[:10]:
    rgb = domain_colors[d]
    print(f"  {d:25s} {c:5d}  rgb({rgb[0]},{rgb[1]},{rgb[2]})")

# ── Write v3 HTML ──
v3_html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YGGDRASIL — La Pluie v3 · Domaines spectraux</title>
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
#dom-panel{{position:fixed;top:50%;right:12px;transform:translateY(-50%);z-index:10;max-height:80vh;overflow-y:auto;
  display:flex;flex-direction:column;gap:0px;pointer-events:all;padding:4px;
  scrollbar-width:thin;scrollbar-color:#222 transparent}}
#dom-panel::-webkit-scrollbar{{width:3px}}
#dom-panel::-webkit-scrollbar-thumb{{background:#333;border-radius:2px}}
.di{{display:flex;align-items:center;gap:6px;padding:2px 8px 2px 5px;border-radius:3px;cursor:pointer;
  transition:all 0.2s;border:1px solid transparent;opacity:0.6}}
.di:hover{{background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.06);opacity:1}}
.di.act{{background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.12);opacity:1}}
.di.dim{{opacity:0.15}}
.dd{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.dn{{font-size:8px;letter-spacing:0.4px;color:#556;transition:color 0.2s;white-space:nowrap;max-width:120px;overflow:hidden;text-overflow:ellipsis}}
.di.act .dn,.di:hover .dn{{color:#99a}}
.dc{{font-size:7px;color:#334;margin-left:auto;padding-left:4px}}
#dom-reset{{font-size:8px;color:#445;letter-spacing:1px;text-align:center;padding:4px 0;cursor:pointer;border-top:1px solid #1a1a22;margin-top:2px}}
#dom-reset:hover{{color:#8af}}
#strate-legend{{position:fixed;top:50%;left:12px;transform:translateY(-50%);z-index:10;display:flex;flex-direction:column;gap:1px;pointer-events:all}}
.si{{display:flex;align-items:center;gap:6px;padding:3px 8px;border-radius:3px;cursor:pointer;transition:all 0.2s;border:1px solid transparent}}
.si:hover{{background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.06)}}
.si.act{{background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.12)}}
.sd2{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.sn2{{font-size:8px;color:#445;letter-spacing:0.5px;white-space:nowrap}}
.si.act .sn2,.si:hover .sn2{{color:#889}}
#controls{{position:fixed;top:70px;left:22px;z-index:10;font-size:10px;color:#555;letter-spacing:1px}}
#controls input{{vertical-align:middle;accent-color:#f97316}}
#controls label{{cursor:pointer}}
#hint{{position:fixed;bottom:20px;right:20px;z-index:10;font-size:9px;color:#222;letter-spacing:1px;text-align:right;line-height:1.9}}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud">
  <h1>Yggdrasil · La Pluie v3</h1>
  <div class="sub">{total_c1} symboles · {n_domains} domaines · positions spectrales</div>
</div>
<div id="info">
  <div class="sn" id="sn">—</div>
  <div class="sf" id="sf"></div>
  <div class="sd" id="sd"></div>
  <div class="sl" id="sl"></div>
</div>
<div id="controls">
  <label><input type="checkbox" id="toggleC2" onchange="switchMode()"> C2 Conjectures</label>
  <label><input type="checkbox" id="toggleC3" onchange="switchMode()"> C3 Fusion</label>
</div>
<div id="strate-legend"></div>
<div id="dom-panel"></div>
<div id="hint"><kbd>drag</kbd> rotation · <kbd>scroll</kbd> zoom · <kbd>clic</kbd> domaine · <kbd>shift+clic</kbd> solo · <kbd>espace</kbd> pause</div>
<script>
{ST_C1_LINE}
{CTR_C1_LINE}
{ST_C2_LINE}
{CTR_C2_LINE}
let currentST=ST_C1,currentCTR=CTR_C1,isC2=false,isC3=false;
{dc_js}
{dl_js}

// ═══ State ═══
const activeDomains=new Set();
let activeS=-1;

// ═══ Canvas ═══
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

// ═══ Domain panel ═══
const domPanel=document.getElementById('dom-panel');
function buildDomPanel(){{
  domPanel.innerHTML='';
  DL.forEach(([name,count])=>{{
    const el=document.createElement('div');el.className='di';el.dataset.dom=name;
    const c=DC[name]||[128,128,128];
    el.innerHTML=`<div class="dd" style="background:rgb(${{c[0]}},${{c[1]}},${{c[2]}})"></div><div class="dn">${{name}}</div><div class="dc">${{count}}</div>`;
    el.addEventListener('click',e=>{{
      if(e.shiftKey){{
        // Solo mode
        if(activeDomains.size===1&&activeDomains.has(name)){{activeDomains.clear()}}
        else{{activeDomains.clear();activeDomains.add(name)}}
      }}else{{
        if(activeDomains.has(name))activeDomains.delete(name);else activeDomains.add(name);
      }}
      updateDomUI();
    }});
    domPanel.appendChild(el);
  }});
  const reset=document.createElement('div');reset.id='dom-reset';reset.textContent='TOUS';
  reset.addEventListener('click',()=>{{activeDomains.clear();updateDomUI()}});
  domPanel.appendChild(reset);
}}
function updateDomUI(){{
  const hasFilter=activeDomains.size>0;
  domPanel.querySelectorAll('.di').forEach(el=>{{
    const d=el.dataset.dom;
    el.classList.toggle('act',activeDomains.has(d));
    el.classList.toggle('dim',hasFilter&&!activeDomains.has(d));
  }});
}}
buildDomPanel();

// ═══ Strate legend (left) ═══
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

// ═══ Mode switching ═══
function switchMode(){{
  isC2=document.getElementById('toggleC2').checked;
  isC3=document.getElementById('toggleC3').checked;
  if(isC3){{isC2=false;document.getElementById('toggleC2').checked=false;currentST=ST_C1;currentCTR=CTR_C1}}
  else if(isC2){{currentST=ST_C2;currentCTR=CTR_C2}}
  else{{currentST=ST_C1;currentCTR=CTR_C1}}
  activeS=-1;buildStrateLegend();
}}

// ═══ Cube edges ═══
const CE=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
function bv(){{const h=BOX.w/2,hy=BOX.h/2,hz=BOX.d/2;return[[-h,-hy,-hz],[h,-hy,-hz],[h,hy,-hz],[-h,hy,-hz],[-h,-hy,hz],[h,-hy,hz],[h,hy,hz],[-h,hy,hz]]}}

// ═══ Render ═══
function frame(){{
  requestAnimationFrame(frame);
  time+=0.003;
  ctx.clearRect(0,0,W,H);
  const gr=ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,W*0.7);
  gr.addColorStop(0,'#0d0d14');gr.addColorStop(1,'#050508');
  ctx.fillStyle=gr;ctx.fillRect(0,0,W,H);
  if(autoRot)yaw+=yawSpd;

  // Cube wireframe
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

    // Strate plane
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
      let ox=sym[1],oz=sym[2];
      if(!isCentre){{const rx=ox*cr-oz*sr;const rz=ox*sr+oz*cr;ox=rx;oz=rz}}
      const pp=project(ox,y,oz);
      const dom=sym[4];
      const domCol=DC[dom]||st.c;
      let finalOp=sop;
      if(hasDomFilter&&!activeDomains.has(dom))finalOp*=0.04;
      items.push({{type:'s',z:pp.z,si,sym,px:pp.x,py:pp.y,pf:pp.f,col:domCol,sop:finalOp,isCentre}});
    }});
  }});

  // C3: also draw C2
  if(isC3){{
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
        if(hasDomFilter&&!activeDomains.has(dom))finalOp*=0.04;
        items.push({{type:'s',z:pp.z,si,sym,px:pp.x,py:pp.y,pf:pp.f,col:domCol,sop:finalOp,isCentre,isC2:true}});
      }});
    }});
  }}

  items.sort((a,b)=>a.z-b.z);
  const sc0=CAM.scale*zoom/CAM.dist;
  let ns=null,nd=18;

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
        if(dist<14){{
          ctx.beginPath();ctx.arc(it.px,it.py,dotR*3.5,0,Math.PI*2);
          ctx.fillStyle=rgba(it.col,Math.min(1,it.sop*1.3));ctx.fill();
        }}else{{
          ctx.beginPath();ctx.arc(it.px,it.py,dotR,0,Math.PI*2);
          ctx.fillStyle=rgba(it.col,it.sop*0.65);ctx.fill();
        }}
      }}
    }}
  }});

  // Hover tooltip
  if(ns){{
    const s=ns.sym;
    const c=ns.col;
    document.getElementById('sn').textContent=s[0];
    document.getElementById('sn').style.color=`rgb(${{c[0]}},${{c[1]}},${{c[2]}})`;
    document.getElementById('sf').textContent=s[4];
    document.getElementById('sf').style.color=`rgb(${{c[0]}},${{c[1]}},${{c[2]}})`;
    const stName=currentST[ns.si]?.sh||'';
    document.getElementById('sd').textContent=stName;
    document.getElementById('sl').textContent=ns.isC2?'C2 conjecture':'C1';
    // Crosshair
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
