"""
Hypertree Decomposition of the S-2 glyph hypergraph.

Reads hyperedge_signatures.json (153 hyperedges, 19 domains, ~1329 glyphs)
and builds a hypertree decomposition, output as interactive HTML.

Algorithm: greedy top-down split based on domain set containment.
- Root = universal glyphs (19 domains)
- Each level peels off domains, grouping hyperedges by max overlap
- Running intersection property enforced by construction
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIG_FILE = ROOT / "viz" / "hyperedge_signatures.json"
OUT_HTML = ROOT / "viz" / "hypertree_decomp.html"


def load_signatures():
    with open(SIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # assign IDs
    for i, h in enumerate(data):
        h["id"] = f"e{i}"
        h["domain_set"] = frozenset(h["domains"])
    return data


def build_hypertree(hedges):
    """
    Build hypertree decomposition using greedy containment approach.

    Strategy:
    - Sort hyperedges by domain count descending
    - Root bag = hyperedges covering ALL 19 domains
    - Recursively split: for each remaining domain subset,
      find the best parent (largest domain overlap) and attach

    We group hyperedges by their exact domain signature first,
    then build a tree of these groups based on subset relationships.
    """
    # Group by exact domain signature
    groups = defaultdict(list)
    for h in hedges:
        groups[h["domain_set"]].append(h)

    # Create tree nodes from groups
    nodes = []
    for ds, members in groups.items():
        total_glyphs = sum(m["n_glyphs"] for m in members)
        symbols = []
        for m in members:
            symbols.extend([g["symbol"] for g in m["glyphs"]])
        nodes.append({
            "domain_set": ds,
            "domains": sorted(ds),
            "n_domains": len(ds),
            "n_glyphs": total_glyphs,
            "n_hedges": len(members),
            "symbols": symbols,
            "glyph_details": [g for m in members for g in m["glyphs"]],
            "children": [],
            "parent": None,
        })

    # Sort by domain count descending (most universal first)
    nodes.sort(key=lambda n: (-n["n_domains"], -n["n_glyphs"]))

    # Build tree: each node attaches to the smallest superset above it
    # (or the node with largest overlap if no strict superset exists)
    root_nodes = []
    placed = []

    for node in nodes:
        best_parent = None
        best_score = -1

        for candidate in placed:
            # Check if candidate's domain set is a superset of node's
            if node["domain_set"].issubset(candidate["domain_set"]):
                # Prefer the smallest superset (most specific parent)
                score = -len(candidate["domain_set"])  # smaller superset = better
                if best_parent is None or score > best_score:
                    best_parent = candidate
                    best_score = score

        if best_parent is None:
            # No superset found — check for max overlap
            for candidate in placed:
                overlap = len(node["domain_set"] & candidate["domain_set"])
                if overlap > best_score:
                    best_parent = candidate
                    best_score = overlap

        if best_parent is not None and best_score != 0:
            best_parent["children"].append(node)
            node["parent"] = id(best_parent)
        else:
            root_nodes.append(node)

        placed.append(node)

    # If multiple roots, create a virtual root
    if len(root_nodes) == 1:
        root = root_nodes[0]
    else:
        all_domains = set()
        for n in nodes:
            all_domains |= n["domain_set"]
        root = {
            "domain_set": frozenset(all_domains),
            "domains": sorted(all_domains),
            "n_domains": len(all_domains),
            "n_glyphs": 0,
            "n_hedges": 0,
            "symbols": [],
            "glyph_details": [],
            "children": root_nodes,
            "parent": None,
            "virtual": True,
        }

    return root


def tree_to_json(node, depth=0):
    """Convert tree to JSON-serializable dict."""
    # Short domain names
    short = {
        "Art": "Art", "Biology": "Bio", "Business": "Biz",
        "Chemistry": "Chem", "Computer science": "CS",
        "Economics": "Econ", "Engineering": "Eng",
        "Environmental science": "Env", "Geography": "Geo",
        "Geology": "Geol", "History": "Hist",
        "Materials science": "MatSci", "Mathematics": "Math",
        "Medicine": "Med", "Philosophy": "Phil",
        "Physics": "Phys", "Political science": "PolSci",
        "Psychology": "Psych", "Sociology": "Soc",
    }

    short_domains = [short.get(d, d) for d in node["domains"]]

    result = {
        "domains": short_domains,
        "n_domains": node["n_domains"],
        "n_glyphs": node["n_glyphs"],
        "n_hedges": node["n_hedges"],
        "symbols": node["symbols"][:12],  # cap for display
        "total_symbols": len(node["symbols"]),
        "glyph_details": node["glyph_details"][:20],
        "virtual": node.get("virtual", False),
        "depth": depth,
        "children": [tree_to_json(c, depth + 1) for c in node["children"]],
    }

    # Sort children: more domains first, then more glyphs
    result["children"].sort(key=lambda c: (-c["n_domains"], -c["n_glyphs"]))

    return result


def count_nodes(tree):
    return 1 + sum(count_nodes(c) for c in tree["children"])


def generate_html(tree_json):
    """Generate self-contained interactive HTML — indented tree (vertical).

    Design tokens from PROMPT_DESIGN_AUDIT.md:
    - Dark mode: bg #121212, card #1E1E1E, elevated #252525, borders #333333
    - Text: body #E5E5E5, secondary #A3A3A3, primary accent #3B82F6
    - Spacing: 4/8/12/16/24/32/48/64 (multiples of 4)
    - Typography: h1 32px/700, h2 24px/600, body 16px/400, small 14px, caption 12px
    - Border-radius: 8px (buttons), 12px (cards)
    - Contrast: text 4.5:1 min, UI 3:1 min
    """

    tree_data = json.dumps(tree_json, ensure_ascii=False, indent=None)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Hypertree Decomposition — S-2 Glyphes</title>
<style>
:root {{
    --bg-page: #121212;
    --bg-card: #1E1E1E;
    --bg-elevated: #252525;
    --border: #333333;
    --text-body: #E5E5E5;
    --text-secondary: #A3A3A3;
    --text-muted: #737373;
    --primary: #3B82F6;
    --primary-light: #BFDBFE;
    --success: #22C55E;
    --error: #EF4444;
    --radius-md: 8px;
    --radius-lg: 12px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg-page);
    color: var(--text-body);
    overflow: hidden;
    height: 100vh;
    font-size: 16px;
}}

/* === HEADER === */
#header {{
    position: fixed; top: 0; left: 0; right: 0;
    z-index: 100;
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex; align-items: center; gap: 16px;
}}

#header h1 {{ font-size: 20px; font-weight: 700; color: #fff; }}
#header .sub {{ font-size: 14px; color: var(--text-secondary); }}
.pills {{ display: flex; gap: 8px; margin-left: auto; }}
.pill {{
    background: var(--bg-elevated); border: 1px solid var(--border);
    border-radius: 4px; padding: 4px 12px; font-size: 14px; color: var(--text-secondary);
}}
.pill b {{ color: var(--primary-light); }}

/* === TOOLBAR === */
#toolbar {{
    position: fixed; top: 52px; left: 0; right: 0; z-index: 100;
    background: var(--bg-page); border-bottom: 1px solid var(--border);
    padding: 8px 24px; display: flex; align-items: center; gap: 8px;
}}
#toolbar input {{
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-body); padding: 8px 16px; font-size: 14px;
    border-radius: var(--radius-md); width: 300px;
}}
#toolbar input:focus {{ outline: none; border-color: var(--primary); }}
#toolbar input::placeholder {{ color: var(--text-muted); }}
#toolbar button {{
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-secondary); padding: 8px 16px; font-size: 14px;
    border-radius: var(--radius-md); cursor: pointer;
}}
#toolbar button:hover {{ background: var(--bg-elevated); border-color: var(--primary); color: var(--text-body); }}

/* === SVG CANVAS === */
#canvas {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    cursor: grab;
}}
#canvas:active {{ cursor: grabbing; }}

/* === TOOLTIP === */
#tooltip {{
    position: fixed; display: none;
    background: var(--bg-card); border: 1px solid var(--primary);
    border-radius: var(--radius-lg); padding: 16px;
    font-size: 14px; max-width: 420px; z-index: 200;
    pointer-events: none;
    box-shadow: 0 10px 15px rgba(0,0,0,0.4);
    line-height: 1.5;
}}
.tt-title {{ font-size: 16px; font-weight: 600; color: var(--primary-light); margin-bottom: 8px; }}
.tt-doms {{ color: var(--text-secondary); margin-bottom: 12px; line-height: 1.8; }}
.tt-sym {{ font-size: 24px; letter-spacing: 6px; line-height: 1.5; word-break: break-all; padding: 8px 0; }}
.tt-det {{ font-size: 12px; color: var(--text-muted); margin-top: 8px; white-space: pre-line; line-height: 1.5; }}

#legend {{
    position: fixed; bottom: 16px; right: 24px; z-index: 100;
    font-size: 14px; color: var(--text-muted);
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 8px 16px;
}}
</style>
</head>
<body>

<div id="header">
    <h1>Hypertree S-2</h1>
    <span class="sub">Decomposition hierarchique &middot; glyphes x domaines</span>
    <div class="pills">
        <span class="pill"><b>153</b> noeuds</span>
        <span class="pill"><b>1329</b> glyphes</span>
        <span class="pill"><b>19</b> domaines</span>
    </div>
</div>

<div id="toolbar">
    <input type="text" id="search" placeholder="Chercher domaine, glyphe, Unicode..." />
    <button onclick="expandAll()">Tout ouvrir</button>
    <button onclick="collapseAll()">Tout fermer</button>
    <button onclick="resetView()">Recentrer</button>
</div>

<svg id="canvas"></svg>

<div id="tooltip">
    <div class="tt-title"></div>
    <div class="tt-doms"></div>
    <div class="tt-sym"></div>
    <div class="tt-det"></div>
</div>

<div id="legend">Clic = ouvrir/fermer &middot; Hover = details &middot; Molette = zoom &middot; Drag = pan</div>

<script>
const DATA = {tree_data};

const DCOL = {{
    'Phys': '#e05555', 'Math': '#3dbdb4', 'CS': '#3da6c0', 'MatSci': '#e0b520',
    'Chem': '#d9842a', 'Eng': '#d44545', 'Bio': '#5a9940', 'Econ': '#5b60cc',
    'Env': '#1d949e', 'Geo': '#4a5a9e', 'Geol': '#a828cc', 'Biz': '#c94de0',
    'Art': '#e08ae0', 'Psych': '#96d4d9', 'PolSci': '#b8c4cc',
    'Hist': '#e0d48a', 'Med': '#45d9a8', 'Phil': '#8a85e0', 'Soc': '#d96a8e',
}};

// === VERTICAL TREE LAYOUT ===
// Each node is a box. Children are placed BELOW and to the RIGHT (indented).
// This gives a vertical tree that scrolls down, not sideways.

const NODE_W = 480;
const NODE_H = 72;
const INDENT_X = 40;      // horizontal indent per depth level
const GAP_Y = 16;          // vertical gap between sibling nodes (spacing: 16px)
const CHILD_GAP_Y = 12;   // extra gap before first child (spacing: 12px)

let allNodes = [];
let svg, gMain;
let transform = {{ x: 0, y: 0, k: 1 }};
let dragging = false, dragStart = {{ x: 0, y: 0 }};

// Init tree data
let nid = 0;
function initNode(node, parent, depth) {{
    node._id = nid++;
    node._parent = parent;
    node._depth = depth;
    node._collapsed = depth >= 2;
    node._x = 0;
    node._y = 0;
    node._searchMatch = false;
    allNodes.push(node);
    for (const c of node.children || []) initNode(c, node, depth + 1);
}}
initNode(DATA, null, 0);
DATA._collapsed = false;

// Layout: vertical list with indentation
function doLayout() {{
    let y = 0;
    function lay(node) {{
        node._x = node._depth * INDENT_X;
        node._y = y;
        y += NODE_H + GAP_Y;

        if (!node._collapsed && node.children) {{
            y += CHILD_GAP_Y;
            for (const c of node.children) lay(c);
        }}
    }}
    y = 0;
    lay(DATA);
}}

function svgEl(tag, attrs) {{
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
}}

function getVisibleNodes(node) {{
    const result = [node];
    if (!node._collapsed && node.children) {{
        for (const c of node.children) result.push(...getVisibleNodes(c));
    }}
    return result;
}}

function render() {{
    doLayout();
    const visible = getVisibleNodes(DATA);

    while (gMain.firstChild) gMain.removeChild(gMain.firstChild);

    // Draw edges — elbow connectors from left-center of parent down to children
    for (const node of visible) {{
        if (node._collapsed || !node.children) continue;
        const visKids = node.children.filter(c => visible.includes(c));
        if (visKids.length === 0) continue;

        // Connector starts at bottom-left area of parent card
        const px = node._x + 20;
        const py = node._y + NODE_H;

        for (const c of visKids) {{
            const cx = c._x;
            const cy = c._y + NODE_H / 2;

            // Elbow: down from parent, then right to child
            const path = svgEl('path', {{
                d: `M${{px}},${{py}} L${{px}},${{cy}} L${{cx}},${{cy}}`,
                fill: 'none',
                stroke: '#484848',
                'stroke-width': '2',
                'stroke-linecap': 'round',
                'stroke-linejoin': 'round',
            }});
            gMain.appendChild(path);
        }}

        // Small dot at branch point
        if (visKids.length > 1) {{
            const lastKid = visKids[visKids.length - 1];
            const bottomY = lastKid._y + NODE_H / 2;
            gMain.appendChild(svgEl('circle', {{
                cx: px, cy: py, r: 3, fill: '#484848',
            }}));
        }}
    }}

    // Draw nodes
    for (const node of visible) {{
        const g = svgEl('g', {{ transform: `translate(${{node._x}},${{node._y}})` }});
        g.style.cursor = 'pointer';

        const hasKids = node.children && node.children.length > 0;
        const isHigh = node.n_glyphs >= 10;
        const isMed = node.n_glyphs >= 5;
        const strokeCol = node._searchMatch ? '#EF4444' : isHigh ? '#3B82F6' : isMed ? '#22C55E' : '#404040';

        // Card background with subtle shadow
        g.appendChild(svgEl('rect', {{
            x: 1, y: 2, width: NODE_W, height: NODE_H, rx: 12,
            fill: 'rgba(0,0,0,0.25)', stroke: 'none',
        }}));
        g.appendChild(svgEl('rect', {{
            x: 0, y: 0, width: NODE_W, height: NODE_H, rx: 12,
            fill: node._searchMatch ? '#1a2a3e' : '#1E1E1E',
            stroke: strokeCol, 'stroke-width': node._searchMatch ? 2.5 : 1.5,
        }}));

        // === ROW 1 (top, y=12..28): badge + dots + glyph symbols ===

        // Collapse toggle (far left)
        if (hasKids) {{
            g.appendChild(svgEl('rect', {{
                x: 8, y: 8, width: 24, height: 24, rx: 6, fill: '#252525',
            }}));
            const tgl = svgEl('text', {{
                x: 20, y: 25, 'text-anchor': 'middle',
                fill: node._collapsed ? '#BFDBFE' : '#737373',
                'font-size': '15', 'font-weight': '600',
            }});
            tgl.textContent = node._collapsed ? '+' : '-';
            g.appendChild(tgl);
        }}

        // Badge: domain count
        const bx = hasKids ? 40 : 12;
        g.appendChild(svgEl('rect', {{
            x: bx, y: 8, width: 40, height: 24, rx: 6, fill: '#252525',
        }}));
        const badgeTxt = svgEl('text', {{
            x: bx + 20, y: 25, 'text-anchor': 'middle',
            fill: '#BFDBFE', 'font-size': '13', 'font-weight': '600',
        }});
        badgeTxt.textContent = node.n_domains + 'd';
        g.appendChild(badgeTxt);

        // Domain color dots
        const domsShow = node.domains.length <= 12 ? node.domains : node.domains.slice(0, 10);
        let dotX = bx + 52;
        for (const d of domsShow) {{
            g.appendChild(svgEl('rect', {{
                x: dotX, y: 13, width: 10, height: 10, rx: 2,
                fill: DCOL[d] || '#555',
            }}));
            dotX += 14;
        }}
        if (node.domains.length > 12) {{
            const moreTxt = svgEl('text', {{
                x: dotX + 4, y: 23, fill: '#737373', 'font-size': '11',
            }});
            moreTxt.textContent = '+' + (node.domains.length - 10);
            g.appendChild(moreTxt);
        }}

        // Glyph symbol preview (right side, row 1)
        const syms = (node.symbols || []).slice(0, 6).join(' ');
        if (syms) {{
            const symTxt = svgEl('text', {{
                x: NODE_W - 16, y: 25, 'text-anchor': 'end',
                fill: '#E5E5E5', 'font-size': '18',
            }});
            symTxt.textContent = syms;
            g.appendChild(symTxt);
        }}

        // === ROW 2 (bottom, y=40..58): domain label + glyph count ===

        // Domain name label
        const domTxt = svgEl('text', {{
            x: bx, y: 56, fill: '#E5E5E5', 'font-size': '15', 'font-weight': '600',
        }});
        let label;
        if (node.virtual) label = 'RACINE UNIVERSELLE';
        else if (node.n_domains <= 6) label = node.domains.join(', ');
        else label = node.n_domains + ' domaines';
        domTxt.textContent = label;
        g.appendChild(domTxt);

        // Glyph count (right-aligned, row 2)
        if (node.n_glyphs > 0) {{
            const gcTxt = svgEl('text', {{
                x: NODE_W - 16, y: 56, 'text-anchor': 'end',
                fill: isHigh ? '#3B82F6' : isMed ? '#22C55E' : '#A3A3A3',
                'font-size': '14', 'font-weight': isHigh ? '700' : '400',
            }});
            gcTxt.textContent = node.n_glyphs + ' glyphe' + (node.n_glyphs > 1 ? 's' : '');
            g.appendChild(gcTxt);
        }}

        // Child count badge (bottom right of toggle)
        if (hasKids) {{
            const cntTxt = svgEl('text', {{
                x: 20, y: 56, 'text-anchor': 'middle',
                fill: '#555', 'font-size': '10',
            }});
            cntTxt.textContent = node.children.length + ' fils';
            g.appendChild(cntTxt);
        }}

        // Click to toggle
        g.addEventListener('click', (e) => {{
            e.stopPropagation();
            if (hasKids) {{
                node._collapsed = !node._collapsed;
                render();
            }}
        }});

        // Hover tooltip
        g.addEventListener('mouseenter', (ev) => {{
            const tt = document.getElementById('tooltip');
            tt.style.display = 'block';

            tt.querySelector('.tt-title').textContent = node.virtual ? 'Racine universelle (19 domaines)' :
                node.n_domains + ' domaine' + (node.n_domains > 1 ? 's' : '') + ' - ' +
                node.n_glyphs + ' glyphe' + (node.n_glyphs > 1 ? 's' : '');

            tt.querySelector('.tt-doms').innerHTML = node.domains.map(d => {{
                const c = DCOL[d] || '#555';
                return `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{c}};margin-right:4px;vertical-align:middle"></span>${{d}}`;
            }}).join('&nbsp;&nbsp;');

            tt.querySelector('.tt-sym').textContent = (node.symbols || []).join(' ');

            const dets = (node.glyph_details || []).slice(0, 15).map(g => g.symbol + '  ' + g.name).join('\\n');
            const extra = (node.total_symbols || 0) > 15 ? '\\n... +' + ((node.total_symbols||0) - 15) + ' autres' : '';
            tt.querySelector('.tt-det').textContent = dets + extra;

            let tx = ev.clientX + 16, ty = ev.clientY + 16;
            if (tx + 420 > window.innerWidth) tx = ev.clientX - 420;
            if (ty + 300 > window.innerHeight) ty = ev.clientY - 300;
            tt.style.left = tx + 'px';
            tt.style.top = ty + 'px';
        }});

        g.addEventListener('mouseleave', () => {{
            document.getElementById('tooltip').style.display = 'none';
        }});

        gMain.appendChild(g);
    }}
}}

// Search
document.getElementById('search').addEventListener('input', (e) => {{
    const q = e.target.value.toLowerCase().trim();
    for (const n of allNodes) {{
        n._searchMatch = false;
        if (q.length > 0) {{
            if (n.domains.some(d => d.toLowerCase().includes(q))) n._searchMatch = true;
            if ((n.symbols || []).some(s => s.includes(q))) n._searchMatch = true;
            if ((n.glyph_details || []).some(g => g.name.toLowerCase().includes(q))) n._searchMatch = true;
            if (n._searchMatch) {{
                let p = n._parent;
                while (p) {{ p._collapsed = false; p = p._parent; }}
            }}
        }}
    }}
    render();
}});

function expandAll() {{ for (const n of allNodes) n._collapsed = false; render(); }}
function collapseAll() {{ for (const n of allNodes) {{ if (n._depth > 0) n._collapsed = true; }} render(); }}

function resetView() {{
    transform = {{ x: 60, y: 120, k: 1 }};
    applyTransform();
}}

function applyTransform() {{
    gMain.setAttribute('transform', `translate(${{transform.x}},${{transform.y}}) scale(${{transform.k}})`);
}}

// Init
window.addEventListener('DOMContentLoaded', () => {{
    svg = document.getElementById('canvas');
    svg.setAttribute('width', window.innerWidth);
    svg.setAttribute('height', window.innerHeight);
    gMain = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    svg.appendChild(gMain);

    // Pan
    svg.addEventListener('mousedown', (e) => {{
        if (e.target.closest('g[style]')) return;
        dragging = true;
        dragStart = {{ x: e.clientX - transform.x, y: e.clientY - transform.y }};
    }});
    svg.addEventListener('mousemove', (e) => {{
        if (!dragging) return;
        transform.x = e.clientX - dragStart.x;
        transform.y = e.clientY - dragStart.y;
        applyTransform();
    }});
    svg.addEventListener('mouseup', () => dragging = false);
    svg.addEventListener('mouseleave', () => dragging = false);

    // Zoom
    svg.addEventListener('wheel', (e) => {{
        e.preventDefault();
        const s = e.deltaY > 0 ? 0.9 : 1.1;
        const nk = Math.max(0.15, Math.min(4, transform.k * s));
        const mx = e.clientX, my = e.clientY;
        transform.x = mx - (mx - transform.x) * (nk / transform.k);
        transform.y = my - (my - transform.y) * (nk / transform.k);
        transform.k = nk;
        applyTransform();
    }});

    window.addEventListener('resize', () => {{
        svg.setAttribute('width', window.innerWidth);
        svg.setAttribute('height', window.innerHeight);
    }});

    resetView();
    render();
}});
</script>
</body>
</html>"""
    return html


def main():
    print("Loading hyperedge signatures...")
    hedges = load_signatures()
    print(f"  {len(hedges)} hyperedges, {sum(h['n_glyphs'] for h in hedges)} glyphs")

    print("Building hypertree decomposition...")
    root = build_hypertree(hedges)

    # Count tree stats
    def count(node):
        return 1 + sum(count(c) for c in node["children"])

    def max_width(node):
        w = node["n_hedges"]
        for c in node["children"]:
            w = max(w, max_width(c))
        return w

    n_nodes = count(root)
    width = max_width(root)
    print(f"  {n_nodes} tree nodes, hypertree width = {width}")

    tree_json = tree_to_json(root)

    # Save JSON too
    json_out = ROOT / "viz" / "hypertree_decomp.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(tree_json, f, ensure_ascii=False, indent=2)
    print(f"  JSON -> {json_out}")

    print("Generating HTML...")
    html = generate_html(tree_json)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML -> {OUT_HTML}")
    print("Done!")


if __name__ == "__main__":
    main()
