#!/usr/bin/env python3
"""
Scan OpenAlex works — count papers per year.
329 folders × N gz files. Stream line by line, extract publication_year only.
Checkpoint after each folder.

Output: data/results/openalex_papers_per_year.json
"""
import gzip, json, sys, os, time, glob
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

WORKS_DIR = "E:/openalex/data/works"
OUTPUT = "D:/ygg/yggdrasil-engine/data/results/openalex_papers_per_year.json"
CHECKPOINT = "D:/ygg/yggdrasil-engine/data/results/_openalex_year_checkpoint.json"

def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, 'r') as f:
            return json.load(f)
    return {"done_folders": [], "counts": {}}

def save_checkpoint(ck):
    with open(CHECKPOINT, 'w') as f:
        json.dump(ck, f)

print("=" * 80)
print("SCAN OPENALEX — Papers per year")
print("=" * 80)

ck = load_checkpoint()
done = set(ck["done_folders"])
counts = Counter(ck["counts"])

folders = sorted(glob.glob(os.path.join(WORKS_DIR, "updated_date=*")))
print(f"  {len(folders)} folders, {len(done)} already done")

total_papers = sum(counts.values())
t_start = time.time()

for fi, folder in enumerate(folders):
    folder_name = os.path.basename(folder)
    if folder_name in done:
        continue

    gz_files = sorted(glob.glob(os.path.join(folder, "*.gz")))
    folder_count = 0

    for gz_path in gz_files:
        try:
            with gzip.open(gz_path, 'rt', encoding='utf-8', errors='replace') as f:
                for line in f:
                    # Fast extraction — find publication_year without full JSON parse
                    idx = line.find('"publication_year"')
                    if idx >= 0:
                        # Extract the value after the key
                        rest = line[idx + 19:idx + 30]  # "publication_year": YYYY
                        rest = rest.strip().strip(':').strip()
                        try:
                            year = int(rest.split(',')[0].split('}')[0].strip())
                            if 1000 <= year <= 2030:
                                counts[str(year)] += 1
                                folder_count += 1
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"    ERROR {gz_path}: {e}", flush=True)

    total_papers += folder_count
    done.add(folder_name)
    ck["done_folders"] = list(done)
    ck["counts"] = dict(counts)
    save_checkpoint(ck)

    elapsed = time.time() - t_start
    rate = total_papers / max(elapsed, 1)
    print(f"  [{fi+1}/{len(folders)}] {folder_name}: +{folder_count:,} papers "
          f"(total {total_papers:,}, {rate:,.0f}/s)", flush=True)

# Save final
result = {
    "scan": "openalex_papers_per_year",
    "date": time.strftime("%Y-%m-%d"),
    "total_papers": total_papers,
    "n_years": len(counts),
    "counts": dict(sorted(counts.items())),
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w') as f:
    json.dump(result, f, indent=2)

print(f"\nTotal: {total_papers:,} papers across {len(counts)} years")
print(f"Saved: {OUTPUT}")
print("DONE.")
