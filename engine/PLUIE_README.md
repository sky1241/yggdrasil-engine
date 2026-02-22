# 🌧️ Phase 4 — PLUIE LOCALE

Co-occurrence matrix from OpenAlex full snapshot (~478M papers).

## What it does

Streams all OpenAlex `.gz` files, extracts concept pairs present in Yggdrasil's
5,459 symbols, and builds a sparse co-occurrence matrix. This matrix IS the rain
of Yggdrasil — the real connections between scientific domains measured across
all published research.

## Scripts

| Script | Purpose |
|--------|---------|
| `engine/build_cooccurrence.py` | Main pipeline — streams .gz, builds sparse matrix |
| `engine/analyze_pluie.py` | Post-analysis — stats, degrees, strates, structural holes |
| `tests/generate_mock_data.py` | Mock data generator for testing |
| `tests/test_pluie_bulletproof.py` | 63 tests — unit, integration, edge cases, stress |

## Usage

```bash
# 1. Test with mock data
python tests/generate_mock_data.py
YGG_WORKS_DIR="/tmp/mock_openalex/works" python engine/build_cooccurrence.py --test 5
python engine/analyze_pluie.py

# 2. Real run (Windows, ~6-12h for 400GB)
python engine/build_cooccurrence.py

# 3. Interrupted? Resume from checkpoint
python engine/build_cooccurrence.py --resume

# 4. Analyze results
python engine/analyze_pluie.py
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `YGG_WORKS_DIR` | `D:\openalex\data\works` | Path to OpenAlex .gz files |
| `YGG_STRATES` | `data\strates_export_v2.json` | Yggdrasil symbols export |
| `YGG_OA_MAP` | `data\openalex_map.json` | Symbol → OpenAlex ID mapping |
| `YGG_OUTPUT` | `data\pluie` | Output directory for matrix + index |

## Output Files

```
data/pluie/
├── cooccurrence_matrix.npz   # scipy sparse CSR matrix (N×N)
├── matrix_index.json         # idx↔concept mapping + stats
├── structural_holes.json     # top 200 under-connected pairs (PREDICTIONS)
├── _checkpoint.json          # resume state (cleaned after completion)
└── _partial_matrix.npz       # partial matrix (cleaned after completion)
```

## Key Design Decisions

- **Streaming**: never loads a full .gz in RAM — line by line with `gzip.open()`
- **Sparse accumulation**: `defaultdict(int)` for building, `scipy.sparse.csr_matrix` for storage
- **Checkpoint every 50 files**: Ctrl+C triggers clean save, `--resume` picks up
- **Concept score threshold**: 0.3 (configurable via `--min-score`)
- **Symmetric matrix**: `matrix[i,j] == matrix[j,i]`, diagonal = paper count per concept
- **Structural holes**: pairs where `observed / expected < 0.1` = future discovery candidates

## Tests

```bash
python -m pytest tests/test_pluie_bulletproof.py -v
```

63 tests covering:
- **LoadConcepts** (10): formats, duplicates, unicode, empty, dict values, fallbacks
- **StreamPapers** (8): normal, empty lines, malformed JSON, corrupted .gz, unicode, huge lines
- **ExtractConcepts** (11): score thresholds, missing fields, URL formats, fallbacks
- **DiscoverFiles** (6): flat, nested, deeply nested, sorting, non-gz filtering
- **Checkpoint** (3): save/load/overwrite
- **FullPipeline** (11): 3-concept exact counts, symmetry, multi-gz, score threshold, exit conditions
- **AnalyzePluie** (1): load + stats + degrees
- **EdgeCases** (7): boundary scores, duplicate concepts, whitespace IDs, 10k co-occurrences
- **MathCoherence** (3): symmetry, non-negative, diagonal invariant
- **Stress** (1): 500 concepts × 10k papers < 30s

Bugs found by tests:
- `zlib.error` not caught on corrupted .gz → fixed
- Diagonal counting only when ≥2 concepts → confirmed correct behavior

## Validated

Mock test (31 concepts, 2,500 papers): ✅ pipeline, ✅ analysis, ✅ strate clustering
Stress test (500 concepts, 10,000 papers): ✅ 2.9s, symmetric, non-negative
Full test suite: 63/63 ✅
