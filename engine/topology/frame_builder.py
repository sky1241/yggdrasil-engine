"""
YGGDRASIL ENGINE — Frame Builder
Construit le film du mycélium: de la graine S-2 (t=0) à 2015.

Phase 1: Timeline historique (graines S-2 → an 1000)
  - Chaque graine apparaît à son t=0 prouvé
  - Pas de data OpenAlex, juste les dates historiques

Phase 2: Timeline data-driven (an 1000 → 2024)
  - Scan des 581 chunks par période
  - Pour chaque frame: concepts actifs, co-occurrences, matrice 9×9 inter-espèces
  - Cumulatif: chaque frame = état total du mycélium à cet instant

Output: data/scan/frames.json
"""
import gzip, json, os, time
import numpy as np
from collections import defaultdict

K = 9  # nombre d'espèces
SPECIES_NAMES = {0:'ChiMat', 1:'TerGeo', 2:'BioCli', 3:'HumEco',
                 4:'InfMat', 5:'TerBio', 6:'HumArt', 7:'BioLab', 8:'Physiq'}

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_species_map():
    """Charge le mapping concept_idx → species_id."""
    path = os.path.join(BASE, 'data', 'scan', 'species_65k.json')
    with open(path, encoding='utf-8') as f:
        sp = json.load(f)

    concepts_path = os.path.join(BASE, 'data', 'scan', 'concepts_65k.json')
    with open(concepts_path, encoding='utf-8') as f:
        c65 = json.load(f)

    # Build idx → species
    idx_to_species = {}
    for cid, info in c65['concepts'].items():
        idx = info['idx']
        if cid in sp['concepts']:
            idx_to_species[idx] = sp['concepts'][cid]['species']

    return idx_to_species


def build_phase1():
    """Phase 1: Timeline historique des graines S-2."""
    seeds_path = os.path.join(BASE, 'data', 'core', 'seeds_s2.json')
    with open(seeds_path, encoding='utf-8') as f:
        seeds_data = json.load(f)

    frames = []
    # Group seeds by t0_year
    by_year = defaultdict(list)
    for seed in seeds_data['seeds']:
        by_year[seed['t0_year']].append(seed)

    cumulative_glyphs = []
    for year in sorted(by_year.keys()):
        new_seeds = by_year[year]
        cumulative_glyphs.extend(new_seeds)
        frames.append({
            'period': str(year),
            'year': year,
            'phase': 'historical',
            'new_glyphs': [s['glyph'] for s in new_seeds],
            'new_names': [s['name'] for s in new_seeds],
            'total_glyphs': len(cumulative_glyphs),
            'all_glyphs': [s['glyph'] for s in cumulative_glyphs],
            'concepts_active': 0,
            'edges': 0,
            'species_matrix': [[0]*K for _ in range(K)]
        })

    print(f'Phase 1: {len(frames)} frames historiques', flush=True)
    for f in frames:
        print(f"  {f['year']:>8} | +{len(f['new_glyphs'])} glyphes → {f['total_glyphs']} total | {', '.join(f['new_glyphs'])}", flush=True)

    return frames


def parse_period_year(period):
    """Extrait l'année d'une période (ex: '2007-06' → 2007, '1500' → 1500)."""
    if '-' in period:
        return int(period.split('-')[0])
    return int(period)


def build_phase2(idx_to_species):
    """Phase 2: Scan des 581 chunks, agrégation par période."""
    chunks_dir = os.path.join(BASE, 'data', 'scan', 'chunks')
    chunk_list = sorted(os.listdir(chunks_dir))
    n_chunks = len(chunk_list)

    # Per-period accumulators
    # activity: period → set of concept indices
    # cooc: period → 9×9 matrix (inter-species weights)
    period_concepts = defaultdict(set)
    period_matrix = defaultdict(lambda: np.zeros((K, K), dtype=np.float64))
    period_edges = defaultdict(int)

    t0 = time.time()
    for ci, chunk_name in enumerate(chunk_list):
        # Activity
        act_path = os.path.join(chunks_dir, chunk_name, 'activity.json.gz')
        if os.path.exists(act_path):
            with gzip.open(act_path, 'rt', encoding='utf-8') as f:
                act_data = json.load(f)
            for period, concepts in act_data.items():
                for cidx in concepts:
                    period_concepts[period].add(int(cidx))

        # Co-occurrences → 9×9 inter-species matrix
        cooc_path = os.path.join(chunks_dir, chunk_name, 'cooc.json.gz')
        if os.path.exists(cooc_path):
            with gzip.open(cooc_path, 'rt', encoding='utf-8') as f:
                cooc_data = json.load(f)
            for period, pairs in cooc_data.items():
                mat = period_matrix[period]
                edge_count = 0
                for pair_key, weight in pairs.items():
                    parts = pair_key.split('|')
                    i, j = int(parts[0]), int(parts[1])
                    si = idx_to_species.get(i, -1)
                    sj = idx_to_species.get(j, -1)
                    if si >= 0 and sj >= 0:
                        mat[si, sj] += weight
                        mat[sj, si] += weight
                    edge_count += 1
                period_edges[period] += edge_count

        if (ci + 1) % 50 == 0:
            dt = time.time() - t0
            print(f'  chunk {ci+1}/{n_chunks} ({dt:.0f}s, {len(period_concepts)} périodes)', flush=True)

    dt = time.time() - t0
    print(f'  {n_chunks} chunks scannés en {dt:.0f}s', flush=True)
    print(f'  {len(period_concepts)} périodes distinctes', flush=True)

    # Build cumulative frames
    print('Construction des frames cumulatives...', flush=True)
    all_periods = sorted(period_concepts.keys(), key=lambda p: (parse_period_year(p), p))

    # Filter: only keep periods up to 2025 (remove 2030+, 2040+, 2050+ noise)
    all_periods = [p for p in all_periods if parse_period_year(p) <= 2025]

    frames = []
    cumulative_concepts = set()
    cumulative_matrix = np.zeros((K, K), dtype=np.float64)
    cumulative_edges = 0

    for pi, period in enumerate(all_periods):
        new_concepts = period_concepts[period] - cumulative_concepts
        cumulative_concepts |= period_concepts[period]
        cumulative_matrix += period_matrix[period]
        cumulative_edges += period_edges[period]

        # Count by species
        species_counts = [0] * K
        for cidx in cumulative_concepts:
            si = idx_to_species.get(cidx, -1)
            if si >= 0:
                species_counts[si] += 1

        # New concepts by species
        new_by_species = [0] * K
        for cidx in new_concepts:
            si = idx_to_species.get(cidx, -1)
            if si >= 0:
                new_by_species[si] += 1

        frame = {
            'period': period,
            'year': parse_period_year(period),
            'phase': 'data',
            'concepts_active': len(cumulative_concepts),
            'concepts_new': len(new_concepts),
            'concepts_by_species': species_counts,
            'new_by_species': new_by_species,
            'edges_cumulative': cumulative_edges,
            'edges_period': period_edges[period],
            'species_matrix': cumulative_matrix.tolist(),
        }
        frames.append(frame)

        if (pi + 1) % 200 == 0:
            yr = parse_period_year(period)
            print(f'  frame {pi+1}/{len(all_periods)} (year {yr}, {len(cumulative_concepts):,} concepts, {cumulative_edges:,} edges)', flush=True)

    print(f'Phase 2: {len(frames)} frames data-driven', flush=True)
    return frames


def main():
    print('=== YGGDRASIL FRAME BUILDER ===', flush=True)
    print(f'Building mycelium film: seeds → 2015', flush=True)
    print()

    t_total = time.time()

    # Phase 1: Historical timeline
    print('[PHASE 1] Timeline historique (graines S-2)...', flush=True)
    historical_frames = build_phase1()
    print()

    # Load species mapping
    print('Chargement mapping espèces...', flush=True)
    idx_to_species = load_species_map()
    print(f'  {len(idx_to_species)} concepts mappés à une espèce', flush=True)
    print()

    # Phase 2: Data-driven timeline
    print('[PHASE 2] Scan des 581 chunks...', flush=True)
    data_frames = build_phase2(idx_to_species)
    print()

    # Combine
    all_frames = historical_frames + data_frames

    # Summary stats
    last = data_frames[-1] if data_frames else None
    print('=' * 70)
    print(f'FILM COMPLET: {len(all_frames)} frames')
    print(f'  Phase 1 (historique): {len(historical_frames)} frames')
    print(f'  Phase 2 (data):       {len(data_frames)} frames')
    if last:
        print(f'  Concepts finaux:      {last["concepts_active"]:,}')
        print(f'  Edges finaux:         {last["edges_cumulative"]:,}')
        print(f'  Par espèce:')
        for si in range(K):
            print(f'    {SPECIES_NAMES[si]:>6}: {last["concepts_by_species"][si]:>6}')

    # Save
    output_path = os.path.join(BASE, 'data', 'scan', 'frames.json')
    result = {
        'meta': {
            'total_frames': len(all_frames),
            'historical_frames': len(historical_frames),
            'data_frames': len(data_frames),
            'species_names': SPECIES_NAMES,
            'species_order': list(range(K)),
            'method': 'frame_builder_v1',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'note': 'species_matrix est cumulatif et symétrique (9x9)'
        },
        'frames': all_frames
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    total_time = time.time() - t_total
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f'\nSauvé: {output_path} ({file_size:.1f} MB)')
    print(f'Temps total: {total_time:.0f}s')


if __name__ == '__main__':
    main()
