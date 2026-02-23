#!/usr/bin/env python3
"""
🌿 ESCALIERS SPECTRAUX — Yggdrasil Engine
Détecte les lianes inter-continents dans l'espace spectral (px, pz).

Principe:
  ASCENSEUR 🛗 = concept au centre de son propre continent (intra-continent)
  ESCALIER  🌿 = concept positionné entre 2 continents DISTANTS (inter-continent)

Score de liane = excentricité × portée du pont × log(papers)
  - excentricité: ratio distance_propre / distance_autre (>1 = éloigné de chez soi)
  - portée: distance entre les 2 centroïdes connectés (BIO↔PHYSIQUE >> BIO↔TERRE)
  - papers: poids réel du concept (log scale pour ne pas écraser)

Sky × Claude — 21 février 2026, Versoix
"""

import json
import math
import os
from collections import Counter, defaultdict

# ═══════════════════════════════════════════════════════════════
# MAPPING DOMAIN → CONTINENT
# ═══════════════════════════════════════════════════════════════

CONTINENTS = {
    'chimie': {
        'icon': '🟠', 'name': 'CHIMIE & MATÉRIAUX',
        'doms': ['chimie', 'chimie organique', 'polymères', 'nanotechnologie',
                 'électrochimie', 'matériaux']
    },
    'bio': {
        'icon': '🟢', 'name': 'BIO & MÉDECINE',
        'doms': ['biologie', 'médecine', 'immunologie', 'pharmacologie',
                 'génomique', 'biomédical', 'oncologie', 'bioinformatique',
                 'neurosciences', 'épidémiologie']
    },
    'terre': {
        'icon': '🌍', 'name': 'TERRE & VIVANT',
        'doms': ['géosciences', 'climatologie', 'océanographie', 'écologie',
                 'environnement', 'sismologie', 'volcanologie', 'agronomie',
                 'évolution']
    },
    'physique': {
        'icon': '🔵', 'name': 'PHYSIQUE',
        'doms': ['mécanique', 'quantique', 'relativité', 'particules', 'QFT',
                 'nucléaire', 'cosmologie', 'mécanique stat', 'astronomie',
                 'mécanique analytique', 'gravitation']
    },
    'ingenierie': {
        'icon': '⚙️', 'name': 'INGÉNIERIE & TECHNO',
        'doms': ['ingénierie', 'aérospatiale', 'électromagn', 'optique',
                 'signal', 'télécommunications', 'robotique', 'énergie',
                 'fluides', 'thermo', 'contrôle']
    },
    'math': {
        'icon': '🟣', 'name': 'MATH PURE',
        'doms': ['algèbre', 'analyse', 'topologie', 'géométrie', 'EDP',
                 'probabilités', 'combinatoire', 'nb théorie', 'ensembles',
                 'catégories', 'systèmes dynamiques', 'algèbre lin',
                 'analyse fonctionnelle', 'géom algébrique', 'géom diff',
                 'analyse numérique', 'trigonométrie', 'arithmétique',
                 'nombres', 'nb premiers', 'complexes', 'ordinaux',
                 'stochastique', 'mesure']
    },
    'info': {
        'icon': '💻', 'name': 'INFO & MATH DISCRÈTE',
        'doms': ['informatique', 'complexité', 'calculabilité', 'automates',
                 'logique', 'crypto', 'optimisation', 'ML', 'vision',
                 'information', 'NLP']
    },
    'humaines': {
        'icon': '🔴', 'name': 'SCIENCES HUMAINES',
        'doms': ['économie', 'finance', 'sociologie', 'psychologie',
                 'linguistique', 'éducation', 'histoire', 'anthropologie',
                 'science politique', 'démographie', 'droit']
    },
    'transversal': {
        'icon': '◇', 'name': 'TRANSVERSAL',
        'doms': ['science générale', 'statistiques']
    }
}

# Reverse map: domain → continent_id
DOM_TO_CONT = {}
for cont_id, cont_data in CONTINENTS.items():
    for d in cont_data['doms']:
        DOM_TO_CONT[d] = cont_id


def load_data(base_path=None):
    """Charge strates_export_v2.json et retourne les symboles S0."""
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    path = os.path.join(base_path, 'data', 'core', 'strates_export_v2.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    
    symbols = data['strates'][0]['symbols']
    print(f"📦 Chargé: {len(symbols)} symboles S0")
    return symbols


def compute_centroids(symbols):
    """Calcule le centroïde spectral (px, pz) de chaque continent."""
    sums = defaultdict(lambda: {'px': 0.0, 'pz': 0.0, 'n': 0})
    unmapped = Counter()
    
    for sym in symbols:
        dom = sym['domain']
        cont = DOM_TO_CONT.get(dom)
        if cont is None:
            unmapped[dom] += 1
            continue
        sums[cont]['px'] += sym['px']
        sums[cont]['pz'] += sym['pz']
        sums[cont]['n'] += 1
    
    centroids = {}
    for cont_id, s in sums.items():
        if s['n'] > 0:
            centroids[cont_id] = {
                'px': s['px'] / s['n'],
                'pz': s['pz'] / s['n'],
                'n': s['n']
            }
    
    if unmapped:
        print(f"⚠️  Domaines non mappés: {dict(unmapped)}")
    
    print(f"\n🎯 CENTROÏDES CONTINENTS:")
    for cid, c in sorted(centroids.items(), key=lambda x: -x[1]['n']):
        icon = CONTINENTS[cid]['icon']
        print(f"  {icon} {cid:15s} ({c['n']:>5,}) → px={c['px']:+.4f}, pz={c['pz']:+.4f}")
    
    return centroids


def dist(x1, z1, x2, z2):
    """Distance euclidienne 2D."""
    return math.sqrt((x1 - x2)**2 + (z1 - z2)**2)


def compute_inter_centroid_distances(centroids):
    """Matrice de distances entre centroïdes. Clé pour pondérer les lianes."""
    dists = {}
    cont_ids = sorted(centroids.keys())
    
    print(f"\n📏 DISTANCES INTER-CENTROÏDES:")
    for i, c1 in enumerate(cont_ids):
        for c2 in cont_ids[i+1:]:
            d = dist(centroids[c1]['px'], centroids[c1]['pz'],
                     centroids[c2]['px'], centroids[c2]['pz'])
            dists[(c1, c2)] = d
            dists[(c2, c1)] = d
    
    # Afficher triées
    pairs = [(k, v) for k, v in dists.items() if k[0] < k[1]]
    pairs.sort(key=lambda x: -x[1])
    for (c1, c2), d in pairs:
        icon1 = CONTINENTS[c1]['icon']
        icon2 = CONTINENTS[c2]['icon']
        tag = "🔥 LOIN" if d > 0.8 else ("📐 MOYEN" if d > 0.4 else "🤝 PROCHE")
        print(f"  {icon1}{c1:12s} ↔ {icon2}{c2:12s}: {d:.4f}  {tag}")
    
    return dists


def detect_lianes(symbols, centroids, inter_dists, ratio_threshold=0.8):
    """
    Détecte les lianes spectrales.
    
    Pour chaque concept:
    1. Distance à son propre centroïde (d_home)
    2. Distance au centroïde le plus proche d'un AUTRE continent (d_alien)
    3. Ratio = d_alien / d_home — si < threshold → le concept est plus proche de l'alien
    4. Score = (1 - ratio) × portée_inter × log(concept_weight + 1)
       - portée_inter = distance entre les 2 centroïdes (filtre naturel BIO↔TERRE)
    """
    lianes = []
    skipped_unmapped = 0
    skipped_transversal = 0
    
    for sym in symbols:
        dom = sym['domain']
        home_cont = DOM_TO_CONT.get(dom)
        
        if home_cont is None:
            skipped_unmapped += 1
            continue
        
        # Skip transversal — par nature multi-continent, pas informatif
        if home_cont == 'transversal':
            skipped_transversal += 1
            continue
        
        px, pz = sym['px'], sym['pz']
        
        # Distance à son propre centroïde
        hc = centroids[home_cont]
        d_home = dist(px, pz, hc['px'], hc['pz'])
        
        # Trouver le centroïde alien le plus proche
        best_alien = None
        best_d_alien = float('inf')
        
        for cont_id, c in centroids.items():
            if cont_id == home_cont or cont_id == 'transversal':
                continue
            d = dist(px, pz, c['px'], c['pz'])
            if d < best_d_alien:
                best_d_alien = d
                best_alien = cont_id
        
        if best_alien is None:
            continue
        
        # Ratio: < 1 signifie plus proche de l'alien que de chez soi
        if d_home < 0.001:  # Au cœur exact de son continent
            continue
        
        ratio = best_d_alien / d_home
        
        if ratio < ratio_threshold:
            # Portée inter-centroïdes (distance entre les 2 continents)
            pair = tuple(sorted([home_cont, best_alien]))
            portee = inter_dists.get((pair[0], pair[1]), 0)
            
            # Score composite: excentricité × portée
            excentricite = 1.0 - ratio  # Plus c'est haut, plus le concept est "alien"
            score = excentricite * portee
            
            lianes.append({
                's': sym['s'],
                'from': sym['from'],
                'domain': dom,
                'home': home_cont,
                'alien': best_alien,
                'px': px,
                'pz': pz,
                'd_home': round(d_home, 4),
                'd_alien': round(best_d_alien, 4),
                'ratio': round(ratio, 4),
                'portee': round(portee, 4),
                'score': round(score, 4)
            })
    
    # Trier par score décroissant
    lianes.sort(key=lambda x: -x['score'])
    
    print(f"\n🌿 LIANES SPECTRALES DÉTECTÉES:")
    print(f"  Total: {len(lianes)} (seuil ratio < {ratio_threshold})")
    print(f"  Skipped: {skipped_unmapped} non mappés, {skipped_transversal} transversal")
    
    return lianes


def analyze_lianes(lianes, centroids):
    """Analyse détaillée des lianes par paire de continents."""
    
    # Compter par paire
    pair_counts = Counter()
    pair_scores = defaultdict(list)
    
    for l in lianes:
        pair = tuple(sorted([l['home'], l['alien']]))
        pair_counts[pair] += 1
        pair_scores[pair].append(l['score'])
    
    print(f"\n📊 LIANES PAR PAIRE DE CONTINENTS:")
    print(f"{'Paire':<30s} {'Count':>6s} {'Score moy':>10s} {'Score max':>10s} {'Portée':>8s}")
    print("─" * 70)
    
    for pair, count in pair_counts.most_common():
        c1, c2 = pair
        scores = pair_scores[pair]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        icon1 = CONTINENTS[c1]['icon']
        icon2 = CONTINENTS[c2]['icon']
        # Calculate actual portee
        actual_portee = 0
        for l in lianes:
            p = tuple(sorted([l['home'], l['alien']]))
            if p == pair:
                actual_portee = l['portee']
                break
        
        tag = "🔥" if actual_portee > 0.8 else ("📐" if actual_portee > 0.4 else "  ")
        print(f"  {icon1}{c1:11s}↔{icon2}{c2:11s} {count:>6d}   {avg_score:>9.4f}   {max_score:>9.4f}   {actual_portee:>7.4f} {tag}")
    
    return pair_counts


def top_lianes(lianes, n=50):
    """Affiche les N meilleures lianes (vrais escaliers de secours)."""
    
    print(f"\n🏔️  TOP {n} ESCALIERS DE SECOURS (score le plus élevé):")
    print(f"{'#':>3s} {'Score':>7s} {'Symbole':<20s} {'Concept':<35s} {'Home→Alien':<25s} {'Ratio':>6s} {'Portée':>7s}")
    print("─" * 110)
    
    for i, l in enumerate(lianes[:n]):
        icon_h = CONTINENTS[l['home']]['icon']
        icon_a = CONTINENTS[l['alien']]['icon']
        route = f"{icon_h}{l['home'][:6]}→{icon_a}{l['alien'][:6]}"
        sym_display = l['s'][:18]
        from_display = l['from'][:33]
        
        print(f"  {i+1:>2d}  {l['score']:>6.4f}  {sym_display:<20s} {from_display:<35s} {route:<25s} {l['ratio']:>5.3f}  {l['portee']:>6.4f}")
    
    return lianes[:n]


def validate_against_known(lianes):
    """Validation croisée avec les lianes historiques connues."""
    
    known_lianes = {
        'exp': {'expected_alien': ['physique', 'bio', 'humaines', 'info'], 'discovery': 'GANs, AlphaFold, mRNA, CAR-T'},
        'ln': {'expected_alien': ['physique', 'bio', 'humaines'], 'discovery': 'Entropie, thermodynamique'},
        '∫': {'expected_alien': ['physique', 'ingenierie', 'humaines', 'bio'], 'discovery': 'Wiles/Fermat, Higgs'},
        'Σ': {'expected_alien': ['physique', 'ingenierie', 'humaines', 'info'], 'discovery': 'Wiles/Fermat, Transformers'},
        '∂': {'expected_alien': ['physique', 'ingenierie', 'humaines'], 'discovery': 'Higgs, Black-Scholes'},
        'W(t)': {'expected_alien': ['humaines', 'physique'], 'discovery': 'Black-Scholes'},
        'ζ': {'expected_alien': ['physique'], 'discovery': 'Wiles/Fermat'},
    }
    
    # Build lookup by symbol
    sym_lookup = defaultdict(list)
    for l in lianes:
        sym_lookup[l['s']].append(l)
    
    print(f"\n✅ VALIDATION CROISÉE (lianes historiques):")
    print(f"{'Symbole':<10s} {'Trouvé':>7s} {'Score':>7s} {'Route spectrale':<30s} {'Découverte associée':<40s}")
    print("─" * 100)
    
    found = 0
    for sym, info in known_lianes.items():
        matches = sym_lookup.get(sym, [])
        if matches:
            best = matches[0]  # highest score first
            icon_h = CONTINENTS[best['home']]['icon']
            icon_a = CONTINENTS[best['alien']]['icon']
            route = f"{icon_h}{best['home']}→{icon_a}{best['alien']}"
            print(f"  {sym:<10s}    ✅   {best['score']:>6.4f}  {route:<30s} {info['discovery']:<40s}")
            found += 1
        else:
            print(f"  {sym:<10s}    ❌   —      —                              {info['discovery']:<40s}")
    
    print(f"\n  Validation: {found}/{len(known_lianes)} lianes historiques retrouvées spectralement")
    return found, len(known_lianes)


def load_passepartout(base_path=None):
    """Charge les 69 lianes historiques (passe-partout multi-continents)."""
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    path = os.path.join(base_path, 'data', 'lianes', 'lianes_export.json')
    with open(path, encoding='utf-8') as f:
        old = json.load(f)
    
    lianes_old = old['lianes']
    
    print(f"\n🔑 PASSE-PARTOUT (lianes historiques multi-continents):")
    print(f"  Total: {len(lianes_old)} symboles")
    
    # Map old continent names to new IDs
    OLD_TO_NEW = {
        'Mathématiques Pures': 'math',
        'Physique Fondamentale': 'physique',
        'Ingénierie & Électricité': 'ingenierie',
        'Informatique & IA': 'info',
        'Finance & Économie': 'humaines',
        'Biologie & Médecine': 'bio',
        'Chimie': 'chimie',
    }
    
    passepartout = []
    for l in lianes_old:
        # Map continents to new IDs
        new_conts = set()
        for c in l['continents']:
            mapped = OLD_TO_NEW.get(c)
            if mapped:
                new_conts.add(mapped)
        
        passepartout.append({
            'symbol': l['symbol'],
            'domain': l.get('domain', ''),
            'n_continents': len(l['continents']),
            'continents': sorted(new_conts),
            'passepartout_score': len(l['continents']) / 7.0  # Normalize to [0, 1]
        })
    
    passepartout.sort(key=lambda x: -x['n_continents'])
    
    # Show top
    for p in passepartout[:10]:
        conts = ', '.join(p['continents'])
        print(f"  {p['symbol']:8s} [{p['n_continents']}C] score={p['passepartout_score']:.3f} → {conts}")
    
    return passepartout


def build_unified(symbols, lianes_geo, passepartout, centroids):
    """
    Fusionne lianes géographiques + passe-partout dans un export unifié.
    
    Deux couches distinctes:
    - layer 'geo': lianes géographiques (concepts entre 2 continents)
    - layer 'key': passe-partout (concepts chez eux mais utilisés partout)
    """
    # Build symbol lookup
    sym_lookup = {s['s']: s for s in symbols}
    
    # Geo lianes: already computed
    geo_layer = []
    for l in lianes_geo[:300]:  # Top 300
        geo_layer.append({
            's': l['s'],
            'from': l['from'],
            'px': l['px'],
            'pz': l['pz'],
            'home': l['home'],
            'alien': l['alien'],
            'score': l['score'],
            'ratio': l['ratio'],
            'type': 'geo'
        })
    
    # Passepartout: enrich with spectral positions
    key_layer = []
    for p in passepartout:
        sym_data = sym_lookup.get(p['symbol'])
        if sym_data is None:
            continue
        
        home_cont = DOM_TO_CONT.get(sym_data['domain'], 'transversal')
        
        key_layer.append({
            's': p['symbol'],
            'from': sym_data['from'],
            'px': sym_data['px'],
            'pz': sym_data['pz'],
            'home': home_cont,
            'continents': p['continents'],
            'n_continents': p['n_continents'],
            'score': p['passepartout_score'],
            'type': 'key'
        })
    
    print(f"\n🔗 UNIFIED ESCALIERS:")
    print(f"  🌿 Géographiques: {len(geo_layer)}")
    print(f"  🔑 Passe-partout: {len(key_layer)}")
    print(f"  Total: {len(geo_layer) + len(key_layer)}")
    
    return geo_layer, key_layer


def export_results(lianes, centroids, inter_dists, base_path=None):
    """Exporte les résultats pour la visualisation."""
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    output = {
        'meta': {
            'date': '2026-02-21',
            'total_lianes': len(lianes),
            'method': 'spectral_ratio_weighted_by_intercontinental_distance',
            'threshold': 0.8
        },
        'centroids': {k: {'px': v['px'], 'pz': v['pz'], 'n': v['n']}
                      for k, v in centroids.items()},
        'inter_distances': {f"{k[0]}↔{k[1]}": v
                           for k, v in inter_dists.items() if k[0] < k[1]},
        'lianes': lianes[:500]  # Top 500 pour la viz
    }
    
    path = os.path.join(base_path, 'data', 'topology', 'escaliers_spectraux.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Exporté: {path} ({len(lianes[:500])} lianes)")
    return path


def export_unified(geo_layer, key_layer, centroids, inter_dists, base_path=None):
    """Exporte le dataset unifié pour la visualisation."""
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    output = {
        'meta': {
            'date': '2026-02-21',
            'method': 'unified_geo+passepartout',
            'geo_count': len(geo_layer),
            'key_count': len(key_layer)
        },
        'centroids': {k: {'px': v['px'], 'pz': v['pz'], 'n': v['n']}
                      for k, v in centroids.items()},
        'inter_distances': {f"{k[0]}↔{k[1]}": round(v, 4)
                           for k, v in inter_dists.items() if k[0] < k[1]},
        'geo': geo_layer,
        'key': key_layer
    }
    
    path = os.path.join(base_path, 'data', 'topology', 'escaliers_unified.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Exporté: {path}")
    return path


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("🌿 ESCALIERS SPECTRAUX — Yggdrasil Engine")
    print("   Détection des lianes inter-continents dans l'espace spectral")
    print("=" * 80)
    
    # 1. Charger
    symbols = load_data()
    
    # 2. Centroïdes
    centroids = compute_centroids(symbols)
    
    # 3. Distances inter-centroïdes (clé pour le filtrage)
    inter_dists = compute_inter_centroid_distances(centroids)
    
    # 4. Détecter les lianes
    lianes = detect_lianes(symbols, centroids, inter_dists, ratio_threshold=0.8)
    
    # 5. Analyser par paire
    pair_counts = analyze_lianes(lianes, centroids)
    
    # 6. Top escaliers
    top = top_lianes(lianes, n=50)
    
    # 7. Validation croisée
    found, total = validate_against_known(lianes)
    
    # 8. Charger passe-partout (lianes historiques)
    passepartout = load_passepartout()
    
    # 9. Construire export unifié
    geo_layer, key_layer = build_unified(symbols, lianes, passepartout, centroids)
    
    # 10. Export brut
    export_path = export_results(lianes, centroids, inter_dists)
    
    # 11. Export unifié
    unified_path = export_unified(geo_layer, key_layer, centroids, inter_dists)
    
    print("\n" + "=" * 80)
    print("🌿 RÉSUMÉ")
    print(f"   {len(lianes)} lianes géographiques détectées")
    print(f"   {len(passepartout)} passe-partout historiques")
    print(f"   Validation historique: {found}/{total}")
    print(f"   Exports: {export_path}")
    print(f"            {unified_path}")
    print("=" * 80)
    
    return lianes, centroids, inter_dists, passepartout


if __name__ == '__main__':
    main()
