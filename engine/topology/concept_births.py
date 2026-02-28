"""
YGGDRASIL ENGINE — Concept Births
Scanne les 581 chunks (activity uniquement) pour trouver la première
apparition de chaque concept. Output: data/scan/concept_births.json

Format output: { "concept_name": birth_period, ... }
+ un array JS-ready: { "births_by_name": {...}, "births_by_idx": [...] }
"""
import gzip, json, os, time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_period_sort_key(period):
    """Clé de tri pour les périodes (ex: '2007-06' → (2007, '2007-06'))."""
    if '-' in period:
        return (int(period.split('-')[0]), period)
    return (int(period), period)


def main():
    print('=== CONCEPT BIRTHS SCANNER ===', flush=True)

    # Load concept names
    concepts_path = os.path.join(BASE, 'data', 'scan', 'concepts_65k.json')
    with open(concepts_path, encoding='utf-8') as f:
        c65 = json.load(f)

    idx_to_name = {}
    for cid, info in c65['concepts'].items():
        idx_to_name[info['idx']] = info['name']
    print(f'{len(idx_to_name)} concepts chargés', flush=True)

    # Scan all chunks — activity only (skip cooc)
    chunks_dir = os.path.join(BASE, 'data', 'scan', 'chunks')
    chunk_list = sorted(os.listdir(chunks_dir))
    n_chunks = len(chunk_list)

    # For each concept idx: earliest period
    birth = {}  # idx → period string

    t0 = time.time()
    for ci, chunk_name in enumerate(chunk_list):
        act_path = os.path.join(chunks_dir, chunk_name, 'activity.json.gz')
        if not os.path.exists(act_path):
            continue
        with gzip.open(act_path, 'rt', encoding='utf-8') as f:
            act_data = json.load(f)
        for period, concepts in act_data.items():
            for cidx in concepts:
                cidx = int(cidx)
                if cidx not in birth:
                    birth[cidx] = period
                else:
                    # Keep earliest
                    if parse_period_sort_key(period) < parse_period_sort_key(birth[cidx]):
                        birth[cidx] = period

        if (ci + 1) % 100 == 0:
            dt = time.time() - t0
            print(f'  chunk {ci+1}/{n_chunks} ({dt:.0f}s)', flush=True)

    dt = time.time() - t0
    print(f'{n_chunks} chunks scannés en {dt:.0f}s', flush=True)
    print(f'{len(birth)} concepts avec date de naissance', flush=True)

    # Build name → birth_year mapping
    births_by_name = {}
    births_by_idx = [None] * (max(idx_to_name.keys()) + 1)
    for idx, period in birth.items():
        name = idx_to_name.get(idx, f'concept_{idx}')
        year = int(period.split('-')[0]) if '-' in period else int(period)
        births_by_name[name] = year
        if idx < len(births_by_idx):
            births_by_idx[idx] = year

    # Stats
    years = sorted(set(births_by_name.values()))
    print(f'\nPremier concept: {min(years)}')
    print(f'Dernier concept: {max(years)}')
    print(f'Concepts avant 1100: {sum(1 for y in births_by_name.values() if y < 1100)}')
    print(f'Concepts 1100-1800: {sum(1 for y in births_by_name.values() if 1100 <= y < 1800)}')
    print(f'Concepts 1800-1950: {sum(1 for y in births_by_name.values() if 1800 <= y < 1950)}')
    print(f'Concepts 1950-2000: {sum(1 for y in births_by_name.values() if 1950 <= y < 2000)}')
    print(f'Concepts 2000+: {sum(1 for y in births_by_name.values() if y >= 2000)}')

    # Save
    output_path = os.path.join(BASE, 'data', 'scan', 'concept_births.json')
    result = {
        'meta': {
            'total_concepts': len(births_by_name),
            'method': 'first appearance in activity.json.gz across 581 chunks',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        },
        'births_by_name': births_by_name,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f'\nSauvé: {output_path} ({file_size:.1f} MB)')


if __name__ == '__main__':
    main()
