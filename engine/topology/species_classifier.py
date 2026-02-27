"""
YGGDRASIL ENGINE — Species Classifier
Classifie les 65,026 concepts OpenAlex en 9 espèces de mycélium
à partir de ZÉRO — uniquement les co-occurrences brutes des 581 chunks.

Méthode: Spectral Clustering (Laplacien normalisé + KMeans K=9)

V2: Memory-efficient — construit la matrice sparse chunk par chunk,
    pas de dict intermédiaire.
"""
import gzip, json, os, time
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh
from sklearn.cluster import KMeans

K = 9  # nombre d'espèces


def load_chunk_as_sparse(cooc_path, N):
    """Charge un chunk et retourne directement une matrice sparse COO."""
    with gzip.open(cooc_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)

    rows = []
    cols = []
    vals = []
    for period, pairs in data.items():
        for pair_key, weight in pairs.items():
            parts = pair_key.split('|')
            i, j = int(parts[0]), int(parts[1])
            rows.append(i)
            cols.append(j)
            vals.append(weight)

    if not rows:
        return sparse.csr_matrix((N, N))

    return sparse.coo_matrix(
        (np.array(vals, dtype=np.float32),
         (np.array(rows, dtype=np.int32), np.array(cols, dtype=np.int32))),
        shape=(N, N)
    ).tocsr()


def main():
    print('=== CLASSIFICATION 65K CONCEPTS → 9 ESPÈCES ===', flush=True)
    print('From scratch — co-occurrences brutes uniquement', flush=True)
    print('V2: memory-efficient (sparse chunk-by-chunk)', flush=True)
    print()

    # 1. Load concepts
    print('[1/5] Chargement concepts_65k.json...', flush=True)
    with open('data/scan/concepts_65k.json', encoding='utf-8') as f:
        c65 = json.load(f)
    concepts = c65['concepts']
    N = len(concepts)
    print(f'  {N} concepts chargés', flush=True)

    idx_to_info = {}
    for cid, info in concepts.items():
        idx_to_info[info['idx']] = {'id': cid, 'name': info['name'], 'level': info['level']}

    # 2. Aggregate: build sparse matrix chunk by chunk
    print(f'[2/5] Agrégation chunk-by-chunk → matrice sparse {N}x{N}...', flush=True)
    t0 = time.time()

    W = sparse.csr_matrix((N, N), dtype=np.float32)
    chunks_dir = 'data/scan/chunks'
    chunk_list = sorted(os.listdir(chunks_dir))
    n_chunks = len(chunk_list)

    for ci, chunk_name in enumerate(chunk_list):
        cooc_path = os.path.join(chunks_dir, chunk_name, 'cooc.json.gz')
        if not os.path.exists(cooc_path):
            continue

        chunk_sparse = load_chunk_as_sparse(cooc_path, N)
        W = W + chunk_sparse

        if (ci + 1) % 50 == 0:
            dt = time.time() - t0
            print(f'  chunk {ci+1}/{n_chunks} ({dt:.0f}s, nnz={W.nnz:,})...', flush=True)

    dt = time.time() - t0
    print(f'  581 chunks agrégés en {dt:.0f}s, {W.nnz:,} non-zeros', flush=True)

    # 3. Symmetrize
    print('[3/5] Symétrisation + stats...', flush=True)
    W = W + W.T
    W = W.tocsr()
    print(f'  Matrice {N}x{N}, {W.nnz:,} non-zeros (symétrique)', flush=True)

    degrees = np.array(W.sum(axis=1)).flatten()
    connected = int(np.sum(degrees > 0))
    isolated = N - connected
    print(f'  {connected:,} connectés, {isolated:,} isolés', flush=True)

    # 4. Spectral clustering
    print(f'[4/5] Laplacien normalisé + {K} eigenvectors...', flush=True)
    t1 = time.time()

    d_inv_sqrt = np.zeros(N, dtype=np.float64)
    mask = degrees > 0
    d_inv_sqrt[mask] = 1.0 / np.sqrt(degrees[mask])

    D_inv_sqrt = sparse.diags(d_inv_sqrt)
    L_sym = D_inv_sqrt @ W.astype(np.float64) @ D_inv_sqrt

    eigenvalues, eigenvectors = eigsh(L_sym, k=K, which='LM')
    dt2 = time.time() - t1
    print(f'  Eigenvalues: {np.round(eigenvalues, 4)}', flush=True)
    print(f'  Calculé en {dt2:.1f}s', flush=True)

    # 5. KMeans
    print(f'[5/5] KMeans clustering K={K}...', flush=True)

    norms = np.linalg.norm(eigenvectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    eigvec_normed = eigenvectors / norms

    kmeans = KMeans(n_clusters=K, n_init=20, random_state=42)
    labels = kmeans.fit_predict(eigvec_normed)

    # Results
    print()
    print('=' * 70)
    print(f'RÉSULTAT: {K} ESPÈCES (from scratch, {N} concepts)')
    print('=' * 70)
    for k in range(K):
        mask_k = labels == k
        count = int(np.sum(mask_k))
        indices = np.where(mask_k)[0]
        degs = [(idx, degrees[idx]) for idx in indices]
        degs.sort(key=lambda x: -x[1])
        top_names = []
        for d in degs[:10]:
            if d[0] in idx_to_info:
                top_names.append(idx_to_info[d[0]]['name'])
        top_str = ', '.join(top_names)
        print(f'  Espèce {k}: {count:>6} concepts | Top: {top_str}')

    # Save
    result = {}
    for idx in range(N):
        if idx in idx_to_info:
            info = idx_to_info[idx]
            result[info['id']] = {
                'name': info['name'],
                'level': info['level'],
                'species': int(labels[idx]),
                'degree': float(degrees[idx])
            }

    output_path = 'data/scan/species_65k.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'meta': {
                'total': len(result),
                'k': K,
                'method': 'spectral_clustering_from_zero_v2',
                'eigenvalues': eigenvalues.tolist(),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'concepts': result
        }, f, ensure_ascii=False)

    total_time = time.time() - t0
    print(f'\nTotal: {total_time:.0f}s')
    print(f'Sauvé dans {output_path}')


if __name__ == '__main__':
    main()
