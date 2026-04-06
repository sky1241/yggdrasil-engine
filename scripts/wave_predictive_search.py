#!/usr/bin/env python3
"""
YGGDRASIL — Recherche prédictive V3
=====================================
Cherche dans WT3 + arXiv tars les formules pour prédire r et t₀.
Exécution du metaprompt_predictive_wave.md.

Sky × Claude — Session 34, 6 avril 2026
"""
import json, sys, os, math, time, sqlite3, tarfile, gzip, re, io
import numpy as np
from scipy.stats import spearmanr
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

REPO = "D:/ygg/yggdrasil-engine"
DB = os.path.join(REPO, "data", "wt3.db")
ARXIV = "E:/arxiv/src"
CONCEPTS_PATH = os.path.join(REPO, "data", "scan", "concepts_65k.json")
WT4_PATH = os.path.join(REPO, "data", "scan", "wt4_spectral.json")
CHECK_PATH = os.path.join(REPO, "data", "results", "_wave_checkpoint.json")
OUTPUT = os.path.join(REPO, "data", "results", "wave_predictive_search.json")

# Load data
cdata = json.load(open(CONCEPTS_PATH, 'r', encoding='utf-8'))
idx2info = {v['idx']: v for k, v in cdata['concepts'].items()}
ck = json.load(open(CHECK_PATH, 'r', encoding='utf-8'))
wt4 = json.load(open(WT4_PATH, 'r', encoding='utf-8'))

METS = list(ck['phase_1'].keys())
logistic = ck['phase_3e']['fits']
mare = ck['phase_2']
bfs = ck['phase_1']

print("=" * 80)
print("RECHERCHE PRÉDICTIVE V3 — Formules pour r et t₀")
print("=" * 80)

# ══════════════════════════════════════════════════════
# PART 1: Nouvelles features locales (ce qu'on n'a pas encore mesuré)
# ══════════════════════════════════════════════════════

print("\n[1] NOUVELLES FEATURES LOCALES")
print("=" * 80)

conn = sqlite3.connect(DB)
c = conn.cursor()

new_features = {}
for m_name in METS:
    seeds = bfs[m_name]['seeds']
    t0 = time.time()

    # Get 1-hop neighbors
    neighbors = set()
    for s in seeds:
        c.execute("SELECT concept_b, weight FROM cooc_global WHERE concept_a=?", (s,))
        for nb, w in c.fetchall():
            neighbors.add(nb)
        c.execute("SELECT concept_a, weight FROM cooc_global WHERE concept_b=?", (s,))
        for nb, w in c.fetchall():
            neighbors.add(nb)
    neighbors -= set(seeds)

    # Degree distribution of neighbors (excess degree)
    nbr_degrees = []
    nbr_weights = []
    sample_nbrs = list(neighbors)[:500]
    for nb in sample_nbrs:
        c.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_a=?", (nb,))
        deg_a = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM cooc_global WHERE concept_b=?", (nb,))
        deg_b = c.fetchone()[0]
        nbr_degrees.append(deg_a + deg_b)

        c.execute("SELECT SUM(weight) FROM cooc_global WHERE concept_a=?", (nb,))
        wa = c.fetchone()[0] or 0
        c.execute("SELECT SUM(weight) FROM cooc_global WHERE concept_b=?", (nb,))
        wb = c.fetchone()[0] or 0
        nbr_weights.append(wa + wb)

    nbr_deg = np.array(nbr_degrees, dtype=float)
    nbr_w = np.array(nbr_weights, dtype=float)

    # New features
    degree_variance = float(np.var(nbr_deg)) if len(nbr_deg) > 1 else 0
    degree_skew = float(np.mean(((nbr_deg - nbr_deg.mean()) / max(nbr_deg.std(), 1))**3)) if len(nbr_deg) > 2 else 0
    weight_variance = float(np.var(nbr_w)) if len(nbr_w) > 1 else 0
    weight_median = float(np.median(nbr_w)) if len(nbr_w) > 0 else 0
    weight_max = float(np.max(nbr_w)) if len(nbr_w) > 0 else 0
    contrast_ratio = weight_max / max(weight_median, 1)

    # Spectral distance of seeds from graph center
    # WT4 has positions for glyphs but concepts are in the full JSON
    # Use concept positions if available
    seed_spectral_dist = 0
    n_found = 0
    concepts_section = wt4.get('concepts', {})
    for s in seeds:
        s_str = str(s)
        if s_str in concepts_section:
            pos = concepts_section[s_str]
            x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
            dist = math.sqrt(x**2 + y**2 + z**2)
            seed_spectral_dist += dist
            n_found += 1
    if n_found > 0:
        seed_spectral_dist /= n_found

    # Assortativity locale (do high-degree neighbors connect to high-degree neighbors?)
    # Simplified: correlation between degree of seed and mean degree of neighbors
    seed_deg_total = sum(mare[m_name].get('seed_degree', 0) for _ in [1])
    mean_nbr_deg = float(np.mean(nbr_deg)) if len(nbr_deg) > 0 else 0

    new_features[m_name] = {
        'degree_variance': round(degree_variance, 1),
        'degree_skew': round(degree_skew, 4),
        'weight_variance': round(weight_variance, 1),
        'weight_median': round(weight_median, 1),
        'weight_max': round(weight_max, 1),
        'contrast_ratio': round(contrast_ratio, 2),
        'seed_spectral_dist': round(seed_spectral_dist, 4),
        'mean_nbr_degree': round(mean_nbr_deg, 1),
    }

    dt = time.time() - t0
    print(f"  {m_name:25s} deg_var={degree_variance:>12.0f} skew={degree_skew:+.2f} "
          f"contrast={contrast_ratio:.1f} spec_dist={seed_spectral_dist:.3f} ({dt:.0f}s)")

conn.close()

# Correlate new features with r and t₀
r_vals = np.array([logistic[m].get('r_growth', 1) for m in METS])
t0_vals = np.array([logistic[m].get('t0', 1) for m in METS])
K_vals = np.array([logistic[m].get('K', bfs[m]['r_max']) for m in METS])

print(f"\n  Corrélations nouvelles features:")
print(f"  {'Feature':25s} {'vs r':>8s} {'p':>8s} {'vs t₀':>8s} {'p':>8s} {'vs K':>8s} {'p':>8s}")
new_corrs = {}
for fn in ['degree_variance', 'degree_skew', 'weight_variance', 'weight_median',
           'weight_max', 'contrast_ratio', 'seed_spectral_dist', 'mean_nbr_degree']:
    vals = np.array([new_features[m][fn] for m in METS])
    r_r, p_r = spearmanr(vals, r_vals)
    r_t, p_t = spearmanr(vals, t0_vals)
    r_k, p_k = spearmanr(vals, K_vals)
    new_corrs[fn] = {
        'vs_r': {'rho': round(r_r, 4), 'p': round(p_r, 4)},
        'vs_t0': {'rho': round(r_t, 4), 'p': round(p_t, 4)},
        'vs_K': {'rho': round(r_k, 4), 'p': round(p_k, 4)},
    }
    flag_r = " ***" if abs(r_r) > 0.6 else " *" if abs(r_r) > 0.4 else ""
    flag_t = " ***" if abs(r_t) > 0.6 else ""
    print(f"  {fn:25s} {r_r:+8.4f} {p_r:8.4f}{flag_r} {r_t:+8.4f} {p_t:8.4f}{flag_t} {r_k:+8.4f} {p_k:8.4f}")

# Also test composites with existing features
print(f"\n  Composites:")
n_seeds = np.array([mare[m]['n_seeds'] for m in METS])
hub_frac = np.array([mare[m]['hub_fraction'] for m in METS])
density = np.array([mare[m]['local_density'] for m in METS])
avg_ew = np.array([mare[m]['avg_edge_weight'] for m in METS])
spec_dist = np.array([new_features[m]['seed_spectral_dist'] for m in METS])
deg_var = np.array([new_features[m]['degree_variance'] for m in METS])
contrast = np.array([new_features[m]['contrast_ratio'] for m in METS])

composites = {
    'hub_frac / n_seeds': hub_frac / (n_seeds + 0.1),
    '1/n_seeds': 1.0 / n_seeds,
    'contrast × hub_frac': contrast * hub_frac,
    'deg_var × hub_frac': deg_var * hub_frac,
    'spec_dist × n_seeds': spec_dist * n_seeds,
    '1/(density × n_seeds)': 1.0 / (density * n_seeds + 0.01),
    'log(deg_var)': np.log1p(deg_var),
}

for fn, vals in composites.items():
    r_r, p_r = spearmanr(vals, r_vals)
    r_t, p_t = spearmanr(vals, t0_vals)
    flag_r = " ***" if abs(r_r) > 0.6 else " *" if abs(r_r) > 0.4 else ""
    flag_t = " ***" if abs(r_t) > 0.6 else ""
    print(f"  {fn:30s} vs_r={r_r:+.4f}{flag_r}  vs_t0={r_t:+.4f}{flag_t}")


# ══════════════════════════════════════════════════════
# PART 2: Papers dans WT3 sur prédiction cascade/epidemic size
# ══════════════════════════════════════════════════════

print(f"\n\n[2] PAPERS WT3 — Prédiction de cascade/epidemic size")
print("=" * 80)

conn = sqlite3.connect(DB)
c = conn.cursor()

title_searches = [
    ('%predict% %cascade% %size%', 'predict_cascade_size'),
    ('%epidemic% %final size% %network%', 'epidemic_final_size'),
    ('%outbreak% %size% %centrality%', 'outbreak_centrality'),
    ('%diffusion% %speed% %predict%', 'diffusion_speed'),
    ('%spreading% %rate% %topology%', 'spreading_topology'),
    ('%influence% %spread% %predict%', 'influence_predict'),
    ('%PageRank% %epidemic%', 'pagerank_epidemic'),
    ('%spectral% %centrality% %spread%', 'spectral_spreading'),
    ('%local% %structure% %epidemic%', 'local_structure_epidemic'),
    ('%cascade% %predict% %network%', 'cascade_predict'),
    ('%aftershock% %productivity%', 'aftershock_etas'),
    ('%Omori% %law%', 'omori_law'),
    ('%ETAS% %model%', 'etas_model'),
    ('%neural% %avalanche% %predict%', 'neural_avalanche'),
    ('%invasion% %speed% %network%', 'invasion_speed'),
    ('%contagion% %predict% %topology%', 'contagion_predict'),
]

papers_found = {}
total = 0
for pat, label in title_searches:
    c.execute("SELECT paper_id, title, year FROM papers WHERE title LIKE ? ORDER BY year DESC LIMIT 10", (pat,))
    rows = c.fetchall()
    if rows:
        papers_found[label] = []
        print(f"\n  --- {label} ({len(rows)}) ---")
        for pid, title, year in rows:
            total += 1
            papers_found[label].append({'paper_id': pid, 'title': title, 'year': year})
            print(f"    {year} | {pid:35s} | {title[:75] if title else '?'}")

print(f"\n  Total: {total} papers trouvés")
conn.close()


# ══════════════════════════════════════════════════════
# PART 3: Extract key papers from arXiv tars
# ══════════════════════════════════════════════════════

print(f"\n\n[3] EXTRACTION PAPIERS ARXIV")
print("=" * 80)

def get_tex(tar_path, member):
    tf = tarfile.open(tar_path, 'r')
    f = tf.extractfile(member)
    raw = gzip.decompress(f.read())
    tf.close()
    try: text = raw.decode('utf-8')
    except: text = raw.decode('latin-1')
    if not any(text[:5].startswith(x) for x in ['\\', '%', '\r']):
        try:
            inner = tarfile.open(fileobj=io.BytesIO(raw))
            texfiles = [m for m in inner.getmembers() if m.name.endswith('.tex') and m.size > 1000]
            if texfiles:
                texfiles.sort(key=lambda m: m.size, reverse=True)
                ct = inner.extractfile(texfiles[0]).read()
                try: return ct.decode('utf-8')
                except: return ct.decode('latin-1')
        except: pass
    return text

# Key papers to extract (from web search results + known IDs)
key_papers = [
    # Saichev & Sornette 2005 — ETAS model (Carmack move sismologie)
    (f"{ARXIV}/arXiv_src_0501_001.tar", "0501/cond-mat0501132.gz", "Saichev_Sornette_2005_ETAS"),
    # Watts 2002 — Simple model of cascades (threshold model)
    # Not on arXiv — skip
    # Moreno rumor spreading (already extracted in session 34)
    # Newman generating functions (already extracted)
]

for tar_path, member, label in key_papers:
    print(f"\n  --- {label} ---")
    if not os.path.exists(tar_path):
        print(f"    TAR NOT FOUND")
        continue
    try:
        tex = get_tex(tar_path, member)
        m = re.search(r'\\title\{([^}]+)\}', tex)
        if m: print(f"    TITLE: {m.group(1)[:120]}")
        m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.DOTALL)
        if m: print(f"    ABSTRACT: {m.group(1).strip()[:400]}")
        eqs = []
        for m in re.finditer(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', tex, re.DOTALL):
            eqs.append(m.group(1).strip())
        print(f"    EQUATIONS ({len(eqs)}):")
        for eq in eqs[:5]:
            print(f"      {' '.join(eq.split())[:180]}")
    except Exception as e:
        print(f"    ERROR: {e}")


# ══════════════════════════════════════════════════════
# PART 4: Carmack moves — scan cooc deserts
# ══════════════════════════════════════════════════════

print(f"\n\n[4] CARMACK MOVES — NOUVEAUX DÉSERTS")
print("=" * 80)

conn = sqlite3.connect(DB)
c = conn.cursor()
total_works = sum(v.get('works_count', 0) for v in idx2info.values())

# New concept pairs to check
new_carmack = [
    # Web search pistes
    (9157, 9788, 'eigenvalues × epidemic_model'),       # eigenvalues + epidemic
    (9157, 53869, 'eigenvalues × cascade'),              # eigenvalues + cascade
    (3378, 53869, 'random_walk × cascade'),              # random walk + cascade
    (12999, 53869, 'heat_kernel × cascade'),             # heat kernel + cascade
    (12999, 9788, 'heat_kernel × epidemic'),             # heat kernel + epidemic
    # Sismologie
    (10173, 9788, 'seismology × epidemic'),              # seismology + epidemic
    (10173, 12054, 'seismology × branching_process'),    # seismology + branching
    (10173, 2489, 'seismology × percolation'),           # seismology + percolation
    # Neuroscience × network
    (12633, 17674, 'cognitive_psych × scale_free'),      # cognitive + scale-free
    # Finance × physics stat
    (32088, 7678, 'financial_contagion × phase_transition'),
    (6986, 2489, 'systemic_risk × percolation'),
    # Logistic × graph (notre modèle)
    (44219, 61010, 'population × spectral_graph'),       # population dynamics + spectral
    (44219, 2429, 'population × laplacian'),             # population + laplacian
]

print(f"  {'Paire':55s} {'cooc':>7s} {'E':>7s} {'z':>7s} {'status':>8s} {'score':>8s}")
carmack_results = []
for a, b, label in new_carmack:
    lo, hi = min(a, b), max(a, b)
    c.execute("SELECT weight FROM cooc_global WHERE concept_a=? AND concept_b=?", (lo, hi))
    row = c.fetchone()
    obs = row[0] if row else 0
    wa = idx2info.get(a, {}).get('works_count', 0)
    wb = idx2info.get(b, {}).get('works_count', 0)
    exp = wa * wb / total_works if total_works > 0 else 0
    std = max(math.sqrt(max(exp * (1 - wa/total_works) * (1 - wb/total_works), 0)), 1.0)
    z = (obs - exp) / std
    desert = obs == 0
    score = math.log1p(wa) * math.log1p(wb) * abs(z) if desert else 0
    status = "DESERT" if desert else "linked"
    carmack_results.append({
        'pair': label, 'a': a, 'b': b,
        'cooc': round(obs, 4), 'expected': round(exp, 2),
        'z': round(z, 4), 'desert': desert, 'score': round(score, 2),
    })
    print(f"  {label:55s} {obs:7.2f} {exp:7.1f} {z:+7.2f} {status:>8s} {score:8.1f}")

conn.close()


# ══════════════════════════════════════════════════════
# PART 5: GRAND RÉSUMÉ
# ══════════════════════════════════════════════════════

print(f"\n\n{'='*80}")
print("RÉSUMÉ — CE QU'ON A TROUVÉ")
print(f"{'='*80}")

# Best new feature for r
best_r_feat = max(new_corrs.items(), key=lambda x: abs(x[1]['vs_r']['rho']))
best_t0_feat = max(new_corrs.items(), key=lambda x: abs(x[1]['vs_t0']['rho']))

print(f"\n  Meilleur prédicteur de r (vitesse): {best_r_feat[0]} (ρ={best_r_feat[1]['vs_r']['rho']:+.4f})")
print(f"  Meilleur prédicteur de t₀ (timing): {best_t0_feat[0]} (ρ={best_t0_feat[1]['vs_t0']['rho']:+.4f})")
print(f"  Papers trouvés: {total}")
print(f"  Nouveaux déserts: {sum(1 for s in carmack_results if s['desert'])}/{len(carmack_results)}")

# Save
output = {
    "search": "wave_predictive_search_v3",
    "date": "2026-04-06",
    "new_features": new_features,
    "new_correlations": new_corrs,
    "papers_found": papers_found,
    "n_papers": total,
    "carmack_results": carmack_results,
    "best_predictor_r": {"feature": best_r_feat[0], "rho": best_r_feat[1]['vs_r']['rho']},
    "best_predictor_t0": {"feature": best_t0_feat[0], "rho": best_t0_feat[1]['vs_t0']['rho']},
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n  Saved: {OUTPUT}")
print("DONE.")
