#!/usr/bin/env python3
"""
Predictions 2025 — Step 4: Human-Readable Report
=================================================
Generates prediction reports from P4 results.

Input:
  predictions_2025/p4_predictions_INTER.json
  predictions_2025/p4_predictions_INTRA.json
  predictions_2025/species_full.json

Output:
  predictions_2025/PREDICTIONS_2025.json              (top 1000 each, machine)
  predictions_2025/PREDICTIONS_2025_INTER_TOP1000.txt (human readable)
  predictions_2025/PREDICTIONS_2025_INTRA_TOP1000.txt (human readable)
"""
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
TOP_N = 1000


def load_json(filename):
    with open(os.path.join(BASE, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def build_species_names(species_data):
    """Determine species names from top concepts per species."""
    concepts = species_data["concepts"]

    # Group by species, sort by degree
    species_tops = {}
    for url, info in concepts.items():
        sp = info["species"]
        deg = info.get("degree", 0)
        if sp not in species_tops:
            species_tops[sp] = []
        species_tops[sp].append((info["name"], deg, info["level"]))

    names = {}
    for sp, entries in species_tops.items():
        entries.sort(key=lambda x: -x[1])
        # Take top 3 level-0 or level-1 concepts as species name
        top_names = [e[0] for e in entries if e[2] <= 1][:3]
        if not top_names:
            top_names = [e[0] for e in entries[:3]]
        names[sp] = "/".join(top_names[:2])

    return names


def format_predictions_txt(predictions, species_names, layer_name):
    """Generate human-readable text for predictions."""
    lines = []
    lines.append(f"YGGDRASIL ENGINE — PREDICTIONS 2025+")
    lines.append(f"Layer: {layer_name}")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Top {len(predictions)} predictions by P4 score")
    lines.append("=" * 120)
    lines.append("")

    if layer_name == "INTER-SPECIES":
        lines.append("These are BRIDGES between scientific continents.")
        lines.append("Each pair represents two concepts from DIFFERENT species")
        lines.append("that collaborate LESS than expected — a structural hole")
        lines.append("where future discoveries are most likely to emerge.")
    else:
        lines.append("These are REVOLUTIONS within scientific continents.")
        lines.append("Each pair represents two concepts from the SAME species")
        lines.append("that collaborate LESS than expected — an internal gap")
        lines.append("where a within-field breakthrough may occur.")

    lines.append("")
    lines.append(f"{'Rank':>5s}  {'P4':>10s}  {'z-score':>8s}  "
                 f"{'Species A':>20s}  {'Species B':>20s}  "
                 f"{'Concept A':>30s}  {'Concept B':>30s}")
    lines.append("-" * 140)

    for p in predictions:
        sp_a = species_names.get(p["species_a"], f"S{p['species_a']}")
        sp_b = species_names.get(p["species_b"], f"S{p['species_b']}")
        lines.append(
            f"{p['rank']:5d}  {p['p4_score']:10.4f}  {p['z_score']:+8.1f}  "
            f"{sp_a:>20s}  {sp_b:>20s}  "
            f"{p['concept_a_name'][:30]:>30s}  {p['concept_b_name'][:30]}"
        )

    lines.append("")
    lines.append("=" * 120)
    lines.append(f"Total: {len(predictions)} predictions")
    lines.append(f"\"Les champignons voient l'avenir.\" — Sky, Versoix, {time.strftime('%Y')}")

    return "\n".join(lines)


def main():
    t0 = time.time()
    print("Predictions 2025 — Step 4: Human-Readable Report")
    print("=" * 60)

    # Load data
    inter_data = load_json("p4_predictions_INTER.json")
    intra_data = load_json("p4_predictions_INTRA.json")
    species_data = load_json("species_full.json")

    inter_preds = inter_data["predictions"][:TOP_N]
    intra_preds = intra_data["predictions"][:TOP_N]

    species_names = build_species_names(species_data)
    print(f"  Species names:")
    for sp, name in sorted(species_names.items()):
        count = species_data["species_counts"].get(str(sp), "?")
        print(f"    S{sp}: {name} ({count} concepts)")

    # Add species names to predictions
    for p in inter_preds + intra_preds:
        p["species_a_name"] = species_names.get(p["species_a"], f"S{p['species_a']}")
        p["species_b_name"] = species_names.get(p["species_b"], f"S{p['species_b']}")

    # === Machine-readable JSON ===
    combined = {
        "meta": {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": "P4 = activity_A * activity_B * (1 - cooc_norm) * |z_uzzi|",
            "n_inter": len(inter_preds),
            "n_intra": len(intra_preds),
            "species_names": species_names,
            "inter_meta": inter_data["meta"],
            "intra_meta": intra_data["meta"],
        },
        "predictions_inter": inter_preds,
        "predictions_intra": intra_preds,
    }

    json_path = os.path.join(BASE, "PREDICTIONS_2025.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    sz = os.path.getsize(json_path) / 1024
    print(f"\n  Saved: PREDICTIONS_2025.json ({sz:.0f} KB)")

    # === Human-readable TXT — INTER ===
    inter_txt = format_predictions_txt(inter_preds, species_names, "INTER-SPECIES")
    inter_path = os.path.join(BASE, "PREDICTIONS_2025_INTER_TOP1000.txt")
    with open(inter_path, 'w', encoding='utf-8') as f:
        f.write(inter_txt)
    print(f"  Saved: PREDICTIONS_2025_INTER_TOP1000.txt")

    # === Human-readable TXT — INTRA ===
    intra_txt = format_predictions_txt(intra_preds, species_names, "INTRA-SPECIES")
    intra_path = os.path.join(BASE, "PREDICTIONS_2025_INTRA_TOP1000.txt")
    with open(intra_path, 'w', encoding='utf-8') as f:
        f.write(intra_txt)
    print(f"  Saved: PREDICTIONS_2025_INTRA_TOP1000.txt")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"TOP 10 INTER-SPECIES (bridges between continents):")
    for p in inter_preds[:10]:
        print(f"  #{p['rank']:3d}  P4={p['p4_score']:.2f}  "
              f"{p['species_a_name'][:12]:12s} × {p['species_b_name'][:12]:12s}  "
              f"{p['concept_a_name'][:25]} × {p['concept_b_name'][:25]}")

    print(f"\nTOP 10 INTRA-SPECIES (revolutions within continents):")
    for p in intra_preds[:10]:
        print(f"  #{p['rank']:3d}  P4={p['p4_score']:.2f}  "
              f"[{p['species_a_name'][:15]}]  "
              f"{p['concept_a_name'][:25]} × {p['concept_b_name'][:25]}")

    total_time = time.time() - t0
    print(f"\nStep 4 DONE — {total_time:.1f}s")


if __name__ == "__main__":
    main()
