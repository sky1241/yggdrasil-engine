#!/usr/bin/env python3
"""Check OpenAlex Works snapshot completeness."""
import json, os, glob

WORKS_DIR = "D:/openalex/data/works/"

with open(os.path.join(WORKS_DIR, "manifest"), encoding="utf-8") as f:
    m = json.load(f)

expected = {}
for e in m["entries"]:
    path = e["url"].replace("s3://openalex/data/works/", "")
    expected[path] = e["meta"]

print(f"Expected sample: '{list(expected.keys())[0]}'")

local = set()
for gz in glob.glob(os.path.join(WORKS_DIR, "**", "*.gz"), recursive=True):
    rel = os.path.relpath(gz, WORKS_DIR)
    rel = rel.replace("\\", "/")
    local.add(rel)

print(f"Local sample: '{list(local)[0] if local else 'NONE'}'")

missing = set(expected.keys()) - local
matched = set(expected.keys()) & local
extra = local - set(expected.keys())
print(f"\nAttendus: {len(expected)}")
print(f"Locaux: {len(local)}")
print(f"Matches: {len(matched)}")
print(f"Manquants: {len(missing)}")
print(f"En trop: {len(extra)}")

missing_records = sum(expected[p]["record_count"] for p in missing)
missing_size = sum(expected[p]["content_length"] for p in missing)
matched_records = sum(expected[p]["record_count"] for p in matched)
total_records = missing_records + matched_records

print(f"\nRecords telecharges: {matched_records:,}")
print(f"Records manquants: {missing_records:,}")
print(f"Taille manquante: {missing_size / 1e9:.1f} GB")
print(f"Couverture: {100*matched_records/total_records:.1f}%")

if missing:
    missing_dates = sorted(set(p.split("/")[0].replace("updated_date=", "") for p in missing))
    print(f"\nDates manquantes: {len(missing_dates)}")
    print(f"  De: {missing_dates[0]}")
    print(f"  A: {missing_dates[-1]}")
    years = {}
    for d in missing_dates:
        y = d[:4]
        years[y] = years.get(y, 0) + 1
    for y in sorted(years):
        print(f"  {y}: {years[y]} dates")

    parts_count = {}
    for p in missing:
        d = p.split("/")[0]
        parts_count[d] = parts_count.get(d, 0) + 1
    print(f"\nTop dates manquantes par nb parts:")
    for d in sorted(parts_count, key=lambda x: parts_count[x], reverse=True)[:10]:
        print(f"  {d}: {parts_count[d]} parts")

    print(f"\nEspace dispo D: ~468 GB")
    print(f"Marge apres download: ~{468 - missing_size/1e9:.0f} GB")
    hours_50 = missing_size / (50e6 * 3600)
    hours_20 = missing_size / (20e6 * 3600)
    print(f"Temps estime a 50 MB/s: ~{hours_50:.0f}h")
    print(f"Temps estime a 20 MB/s: ~{hours_20:.0f}h")
