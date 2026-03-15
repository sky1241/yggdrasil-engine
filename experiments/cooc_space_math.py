"""
Co-occurrence analysis: SPACE x MATH x BRIDGE concepts
Aggregates from 581 chunks in data/scan/chunks/
Uses zlib streaming decompressor to handle single-line JSON without OOM.
"""
import gzip, json, os, math, sys, re, zlib
from collections import defaultdict
sys.stdout.reconfigure(line_buffering=True)

CHUNKS_DIR = "d:/ygg/yggdrasil-engine/data/scan/chunks"

# --- Concept sets ---
SPACE = {
    13175: "Holographic principle",
    58726: "Black hole information paradox",
    59430: "Black hole thermodynamics",
    54903: "Hawking radiation",
    5556: "Scale invariance",
    54881: "Fractal",
    17805: "Fractal dimension",
    10434: "Cosmological constant",
    62881: "Hawking",
    7542: "Event horizon",
    2400: "Black hole complementarity",
    3102: "Self-similarity",
}

MATH = {
    23664: "Cayley graph",
    46674: "Symmetric group",
    35836: "Permutation group",
    37132: "Group theory",
    50134: "Spectral gap",
    48541: "Expander graph",
    60347: "Boolean satisfiability",
    10745: "Satisfiability",
    1997: "Ramsey theory",
    55433: "Ramsey's theorem",
    12499: "Computational complexity theory",
    15276: "PSPACE",
    3609: "NP-complete",
    57247: "Combinatorial optimization",
}

BRIDGE = {
    65006: "Statistical mechanics",
    56807: "Ising model",
    7678: "Phase transition",
    7925: "Spin glass",
    2489: "Percolation theory",
    3888: "Configuration entropy",
    57221: "Information theory",
    34208: "Kolmogorov complexity",
    63770: "Quantum complexity theory",
    933: "Proof complexity",
}

ALL_IDS = set(SPACE) | set(MATH) | set(BRIDGE)
ALL_IDS_STR = {str(x) for x in ALL_IDS}

cooc = defaultdict(float)
activity = defaultdict(float)

chunk_dirs = sorted([
    os.path.join(CHUNKS_DIR, d)
    for d in os.listdir(CHUNKS_DIR)
    if d.startswith("chunk_")
])

print(f"Processing {len(chunk_dirs)} chunks...")

# Regex to match "A|B": 0.123 patterns
pair_re = re.compile(rb'"(\d+)\|(\d+)":\s*([\d.eE+\-]+)')

COMPRESSED_BLOCK = 8 * 1024  # 8KB compressed = small output chunks
MAX_OUTPUT = 512 * 1024  # 512KB max decompressed output per call

def stream_cooc_pairs(filepath):
    """Stream-decompress a gzip file in tiny blocks and extract matching pairs."""
    found = []
    with open(filepath, 'rb') as raw_f:
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)  # gzip format
        leftover = b""
        while True:
            compressed = raw_f.read(COMPRESSED_BLOCK)
            if not compressed:
                # Final flush
                try:
                    chunk = dec.flush()
                    data = leftover + chunk
                    for m in pair_re.finditer(data):
                        a_s = m.group(1).decode()
                        b_s = m.group(2).decode()
                        if a_s in ALL_IDS_STR and b_s in ALL_IDS_STR:
                            found.append((int(a_s), int(b_s), float(m.group(3))))
                except:
                    pass
                break

            # Decompress in limited chunks to control memory
            to_process = compressed
            while to_process:
                try:
                    decompressed = dec.decompress(to_process, MAX_OUTPUT)
                except zlib.error:
                    to_process = b""
                    break

                data = leftover + decompressed
                # Find last comma to avoid splitting a pair entry
                last_comma = data.rfind(b',')
                if last_comma > 0 and last_comma > len(data) - 100:
                    process = data[:last_comma]
                    leftover = data[last_comma:]
                else:
                    process = data
                    leftover = b""

                for m in pair_re.finditer(process):
                    a_s = m.group(1).decode()
                    b_s = m.group(2).decode()
                    if a_s in ALL_IDS_STR and b_s in ALL_IDS_STR:
                        found.append((int(a_s), int(b_s), float(m.group(3))))

                # Keep leftover small
                if len(leftover) > 200:
                    leftover = leftover[-200:]

                # Check for unconsumed data
                to_process = dec.unconsumed_tail
                if not to_process:
                    break

    return found

errors = 0
for ci, cdir in enumerate(chunk_dirs):
    cooc_path = os.path.join(cdir, "cooc.json.gz")
    act_path = os.path.join(cdir, "activity.json.gz")

    if not os.path.exists(cooc_path):
        continue

    # Activity: load as JSON (smaller files, usually < 5MB uncompressed)
    try:
        with gzip.open(act_path, 'rt', encoding='utf-8') as f:
            act_data = json.load(f)
        for period, concepts in act_data.items():
            for cid_str, count in concepts.items():
                if cid_str in ALL_IDS_STR:
                    activity[int(cid_str)] += count
        del act_data
    except Exception:
        pass

    # Cooc: streaming decompress + regex
    try:
        pairs = stream_cooc_pairs(cooc_path)
        for a, b, w in pairs:
            key = (min(a, b), max(a, b))
            cooc[key] += w
    except Exception as e:
        errors += 1
        if errors <= 10:
            print(f"  WARN: cooc error on chunk {ci+1}: {type(e).__name__}: {e}")

    if (ci + 1) % 100 == 0:
        print(f"  {ci+1}/{len(chunk_dirs)} chunks done, {len(cooc)} pairs found so far")

print(f"\nDone: {len(chunk_dirs)} chunks processed ({errors} errors)")
print(f"Total co-occurrence pairs found: {len(cooc)}")
print(f"Concepts with activity: {len(activity)}")

# --- Helper ---
def get_cooc(a, b):
    key = (min(a, b), max(a, b))
    return cooc.get(key, 0.0)

total_activity = sum(activity.values())
all_names = {**SPACE, **MATH, **BRIDGE}

def short(name, maxlen=18):
    return name[:maxlen]

math_ids = sorted(MATH.keys())
space_ids = sorted(SPACE.keys())
bridge_ids = sorted(BRIDGE.keys())

# ==========================================
# SPACE x MATH
# ==========================================
print(f"\n{'='*120}")
print("SPACE x MATH CO-OCCURRENCE MATRIX")
print(f"{'='*120}")

print(f"\n{'SPACE concept':<30s}", end="")
for mid in math_ids:
    print(f" {short(MATH[mid],14):>14s}", end="")
print(f" {'ROW_ACTIVITY':>14s}")
print("-" * (30 + 15 * (len(math_ids) + 1)))

nonzero_sm = []
for sid in space_ids:
    print(f"{short(SPACE[sid],29):<30s}", end="")
    for mid in math_ids:
        val = get_cooc(sid, mid)
        if val > 0:
            print(f" {val:>14.4f}", end="")
            nonzero_sm.append((sid, mid, val))
        else:
            print(f" {'·':>14s}", end="")
    print(f" {activity.get(sid,0):>14.1f}")

print(f"\n{'MATH activity':<30s}", end="")
for mid in math_ids:
    print(f" {activity.get(mid,0):>14.1f}", end="")
print()

# ==========================================
# SPACE x BRIDGE
# ==========================================
print(f"\n{'='*120}")
print("SPACE x BRIDGE CO-OCCURRENCE MATRIX")
print(f"{'='*120}")

print(f"\n{'SPACE concept':<30s}", end="")
for bid in bridge_ids:
    print(f" {short(BRIDGE[bid],14):>14s}", end="")
print(f" {'ROW_ACTIVITY':>14s}")
print("-" * (30 + 15 * (len(bridge_ids) + 1)))

nonzero_sb = []
for sid in space_ids:
    print(f"{short(SPACE[sid],29):<30s}", end="")
    for bid in bridge_ids:
        val = get_cooc(sid, bid)
        if val > 0:
            print(f" {val:>14.4f}", end="")
            nonzero_sb.append((sid, bid, val))
        else:
            print(f" {'·':>14s}", end="")
    print(f" {activity.get(sid,0):>14.1f}")

print(f"\n{'BRIDGE activity':<30s}", end="")
for bid in bridge_ids:
    print(f" {activity.get(bid,0):>14.1f}", end="")
print()

# ==========================================
# MATH x BRIDGE
# ==========================================
print(f"\n{'='*120}")
print("MATH x BRIDGE CO-OCCURRENCE MATRIX")
print(f"{'='*120}")

print(f"\n{'MATH concept':<30s}", end="")
for bid in bridge_ids:
    print(f" {short(BRIDGE[bid],14):>14s}", end="")
print(f" {'ROW_ACTIVITY':>14s}")
print("-" * (30 + 15 * (len(bridge_ids) + 1)))

nonzero_mb = []
for mid in math_ids:
    print(f"{short(MATH[mid],29):<30s}", end="")
    for bid in bridge_ids:
        val = get_cooc(mid, bid)
        if val > 0:
            print(f" {val:>14.4f}", end="")
            nonzero_mb.append((mid, bid, val))
        else:
            print(f" {'·':>14s}", end="")
    print(f" {activity.get(mid,0):>14.1f}")

# ==========================================
# SUMMARY: NON-ZERO BRIDGES
# ==========================================
print(f"\n{'='*120}")
print("NON-ZERO CO-OCCURRENCES (EXISTING BRIDGES)")
print(f"{'='*120}")

print(f"\n--- SPACE-MATH bridges ({len(nonzero_sm)} found) ---")
for sid, mid, val in sorted(nonzero_sm, key=lambda x: -x[2]):
    print(f"  {SPACE[sid]:<35s} <-> {MATH[mid]:<35s} = {val:.4f}")

print(f"\n--- SPACE-BRIDGE bridges ({len(nonzero_sb)} found) ---")
for sid, bid, val in sorted(nonzero_sb, key=lambda x: -x[2]):
    print(f"  {SPACE[sid]:<35s} <-> {BRIDGE[bid]:<35s} = {val:.4f}")

print(f"\n--- MATH-BRIDGE bridges ({len(nonzero_mb)} found) ---")
for mid, bid, val in sorted(nonzero_mb, key=lambda x: -x[2]):
    print(f"  {MATH[mid]:<35s} <-> {BRIDGE[bid]:<35s} = {val:.4f}")

# ==========================================
# STRUCTURAL HOLES
# ==========================================
print(f"\n{'='*120}")
print("STRUCTURAL HOLES (zero co-occurrence between concepts that SHOULD connect)")
print(f"{'='*120}")

should_connect = [
    ("Holographic principle", 13175, "Comp. complexity theory", 12499, "AdS/CFT complexity"),
    ("Holographic principle", 13175, "Cayley graph", 23664, "boundary structure"),
    ("Holographic principle", 13175, "Spectral gap", 50134, "mass gap duality"),
    ("BH info paradox", 58726, "Comp. complexity theory", 12499, "complexity of information"),
    ("BH thermodynamics", 59430, "Combinatorial optim.", 57247, "entropy optimization"),
    ("Scale invariance", 5556, "Cayley graph", 23664, "self-similar graphs"),
    ("Scale invariance", 5556, "Expander graph", 48541, "expansion at all scales"),
    ("Fractal", 54881, "Cayley graph", 23664, "fractal Cayley graphs"),
    ("Fractal", 54881, "Ramsey theory", 1997, "fractal Ramsey structures"),
    ("Fractal dimension", 17805, "Spectral gap", 50134, "spectral dimension"),
    ("Self-similarity", 3102, "Symmetric group", 46674, "symmetry self-similarity"),
    ("Self-similarity", 3102, "Cayley graph", 23664, "self-similar Cayley"),
    ("Hawking radiation", 54903, "PSPACE", 15276, "decoding complexity"),
    ("Event horizon", 7542, "Boolean satisfiability", 60347, "horizon SAT"),
    ("Cosmological constant", 10434, "Group theory", 37132, "symmetry of spacetime"),
]

print()
for name_a, id_a, name_b, id_b, reason in should_connect:
    val = get_cooc(id_a, id_b)
    status = f"BRIDGE EXISTS ({val:.4f})" if val > 0 else "*** STRUCTURAL HOLE ***"
    print(f"  {name_a:<35s} <-> {name_b:<35s} [{reason}] => {status}")

# ==========================================
# P4 STRUCTURAL HOLE SCORES
# ==========================================
print(f"\n{'='*120}")
print("P4 STRUCTURAL HOLE SCORES (for all non-zero cross-group pairs)")
print(f"{'='*120}")
print("P4 = activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|")
print()

all_nonzero = nonzero_sm + nonzero_sb + nonzero_mb
p4_scores = []

for id_a, id_b, val in all_nonzero:
    act_a = activity.get(id_a, 0)
    act_b = activity.get(id_b, 0)
    if act_a == 0 or act_b == 0:
        continue

    cooc_norm = val / min(act_a, act_b)
    cooc_norm = min(cooc_norm, 1.0)

    expected = act_a * act_b / total_activity if total_activity > 0 else 0
    std = math.sqrt(expected) if expected > 0 else 1e-10
    z_uzzi = (val - expected) / std

    p4 = act_a * act_b * (1 - cooc_norm) * abs(z_uzzi)
    p4_scores.append((id_a, id_b, val, act_a, act_b, cooc_norm, z_uzzi, p4))

p4_scores.sort(key=lambda x: -x[7])

print(f"{'Concept A':<35s} {'Concept B':<35s} {'cooc':>10s} {'act_A':>10s} {'act_B':>10s} {'norm':>8s} {'z_uzzi':>10s} {'P4':>14s}")
print("-" * 140)
for id_a, id_b, val, act_a, act_b, cn, zu, p4 in p4_scores:
    name_a = all_names.get(id_a, str(id_a))
    name_b = all_names.get(id_b, str(id_b))
    print(f"{short(name_a,34):<35s} {short(name_b,34):<35s} {val:>10.4f} {act_a:>10.1f} {act_b:>10.1f} {cn:>8.4f} {zu:>10.4f} {p4:>14.2f}")

# ==========================================
# ACTIVITY SUMMARY
# ==========================================
print(f"\n{'='*120}")
print("ACTIVITY SUMMARY")
print(f"{'='*120}")
print(f"\n--- SPACE ---")
for sid in space_ids:
    print(f"  [{sid:>5d}] {SPACE[sid]:<35s} activity = {activity.get(sid,0):.1f}")
print(f"\n--- MATH ---")
for mid in math_ids:
    print(f"  [{mid:>5d}] {MATH[mid]:<35s} activity = {activity.get(mid,0):.1f}")
print(f"\n--- BRIDGE ---")
for bid in bridge_ids:
    print(f"  [{bid:>5d}] {BRIDGE[bid]:<35s} activity = {activity.get(bid,0):.1f}")

print(f"\nTotal activity (tracked concepts): {total_activity:.1f}")

# Bonus: intra-group
print(f"\n{'='*120}")
print("INTRA-GROUP CO-OCCURRENCES (bonus)")
print(f"{'='*120}")

print(f"\n--- SPACE-SPACE ---")
for i, sid1 in enumerate(space_ids):
    for sid2 in space_ids[i+1:]:
        val = get_cooc(sid1, sid2)
        if val > 0:
            print(f"  {SPACE[sid1]:<35s} <-> {SPACE[sid2]:<35s} = {val:.4f}")

print(f"\n--- MATH-MATH ---")
for i, mid1 in enumerate(math_ids):
    for mid2 in math_ids[i+1:]:
        val = get_cooc(mid1, mid2)
        if val > 0:
            print(f"  {MATH[mid1]:<35s} <-> {MATH[mid2]:<35s} = {val:.4f}")

print(f"\n--- BRIDGE-BRIDGE ---")
for i, bid1 in enumerate(bridge_ids):
    for bid2 in bridge_ids[i+1:]:
        val = get_cooc(bid1, bid2)
        if val > 0:
            print(f"  {BRIDGE[bid1]:<35s} <-> {BRIDGE[bid2]:<35s} = {val:.4f}")
