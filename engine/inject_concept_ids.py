"""
Inject concept_id into strates_export_v2.json from two sources:
  1. data/openalex_map.json  (794 original symbols, key: "from" -> "concept_id")
  2. data/mined_concepts.json (20,730 mined symbols, key: "name" -> "concept_id")

Also builds data/concept_index.json (inverse index: concept_id -> symbol info).
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def build_name_to_cid():
    """Build a name -> concept_id dict from both sources."""
    mapping = {}

    # Source 1: mined_concepts.json (20,730 entries)
    mined = load_json(os.path.join(DATA, "mined_concepts.json"))
    for c in mined["concepts"]:
        name = c["name"]
        cid = c["concept_id"]
        mapping[name] = cid
    print(f"  mined_concepts: {len(mined['concepts'])} entries loaded")

    # Source 2: openalex_map.json (794 originals — override mined if conflict)
    omap = load_json(os.path.join(DATA, "openalex_map.json"))
    orig_count = 0
    for m in omap["mappings"]:
        cid = m.get("concept_id")
        if not cid:
            continue
        name = m["from"]
        mapping[name] = cid
        orig_count += 1
    print(f"  openalex_map:   {orig_count} entries loaded (override)")

    print(f"  total unique names: {len(mapping)}")
    return mapping


def inject(v2, name_to_cid):
    """Inject concept_id into every symbol in v2. Returns stats."""
    matched = 0
    missed = 0
    missed_names = []

    for strate in v2["strates"]:
        for sym in strate["symbols"]:
            name = sym["from"]
            cid = name_to_cid.get(name)
            if cid:
                sym["concept_id"] = cid
                matched += 1
            else:
                missed += 1
                missed_names.append(name)

    return matched, missed, missed_names


def build_concept_index(v2):
    """Build inverse index: concept_id -> {symbol, from, domain, strate}."""
    index = {}
    for strate in v2["strates"]:
        sid = strate["id"]
        for sym in strate["symbols"]:
            cid = sym.get("concept_id")
            if not cid:
                continue
            index[cid] = {
                "symbol": sym["s"],
                "from": sym["from"],
                "domain": sym["domain"],
                "strate": sid,
            }
    return index


def main():
    print("=== Inject concept_id into strates_export_v2.json ===\n")

    # 1. Build mapping
    print("Building name -> concept_id mapping...")
    name_to_cid = build_name_to_cid()

    # 2. Load v2
    v2_path = os.path.join(DATA, "strates_export_v2.json")
    print(f"\nLoading {v2_path}...")
    v2 = load_json(v2_path)

    total_symbols = sum(len(s["symbols"]) for s in v2["strates"])
    print(f"  {total_symbols} symbols across {len(v2['strates'])} strates")

    # 3. Inject
    print("\nInjecting concept_id...")
    matched, missed, missed_names = inject(v2, name_to_cid)
    print(f"  matched: {matched}/{total_symbols} ({100*matched/total_symbols:.1f}%)")
    print(f"  missed:  {missed}/{total_symbols}")

    if missed_names:
        print(f"\n  First 20 missed names:")
        for n in missed_names[:20]:
            print(f"    - {n}")

    # 4. Update meta
    v2["meta"]["concept_ids_injected"] = True
    v2["meta"]["concept_id_matched"] = matched
    v2["meta"]["concept_id_missed"] = missed

    # 5. Save v2
    print(f"\nSaving {v2_path}...")
    save_json(v2_path, v2)
    print("  done.")

    # 6. Build & save concept_index.json
    print("\nBuilding concept_index.json...")
    index = build_concept_index(v2)
    idx_path = os.path.join(DATA, "concept_index.json")
    save_json(idx_path, index)
    print(f"  {len(index)} entries -> {idx_path}")

    print(f"\n=== DONE: {matched}/{total_symbols} symbols with concept_id ===")


if __name__ == "__main__":
    main()
