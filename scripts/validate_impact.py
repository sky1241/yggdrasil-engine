import sys, json, sqlite3, os
sys.stdout.reconfigure(encoding='utf-8')

impact = sqlite3.connect('d:/ygg/yggdrasil-engine/data/impact_scale.db')
wt3 = sqlite3.connect('d:/ygg/yggdrasil-engine/data/wt3.db')
ic = impact.cursor()
wc = wt3.cursor()

# Tier distribution
ic.execute('SELECT tier, COUNT(*) FROM paper_scale GROUP BY tier ORDER BY COUNT(*) DESC')
tier_dist = {r[0]: r[1] for r in ic.fetchall()}
total = sum(tier_dist.values())

# Score stats per tier
ic.execute('SELECT tier, MIN(score), MAX(score), AVG(score) FROM paper_scale GROUP BY tier')
tier_stats = {}
for r in ic.fetchall():
    tier_stats[r[0]] = {'min': round(r[1],2), 'max': round(r[2],2), 'avg': round(r[3],2)}

# Top 30 extinction papers
ic.execute("""SELECT paper_id, score, domain, n_concepts, z_spread, author_names, year,
    rarity_density, spread_rare, weight_rare
    FROM paper_scale WHERE tier = 'extinction' ORDER BY score DESC LIMIT 30""")
extinction_rows = ic.fetchall()

wc.execute("PRAGMA table_info(papers)")
cols = [r[1] for r in wc.fetchall()]

papers = []
for row in extinction_rows:
    pid, score, domain, n_concepts, z_spread, authors_str, year, rarity_d, spread_r, weight_r = row

    wc.execute("SELECT * FROM papers WHERE paper_id = ? LIMIT 1", (pid,))
    wt3_row = wc.fetchone()
    title = None
    if wt3_row:
        col_map = {cols[i]: wt3_row[i] for i in range(len(cols))}
        title = col_map.get('title')

    try:
        authors = json.loads(authors_str) if authors_str else []
    except:
        authors = [authors_str] if authors_str else []

    # Assessment logic
    assessment = "unknown"
    reason = ""

    known_landmarks = {
        'cond-mat/0012123': ('legitimate_niche', 'Neaton & Ashcroft sodium under pressure - well-cited condensed matter paper'),
        '1010.5100': ('legitimate_niche', 'Katsnelson flexuron - notable theoretical prediction by a top physicist'),
        '1510.01304': ('legitimate_niche', 'Chiral magnetic effect - topical Weyl semimetal physics'),
    }

    if pid in known_landmarks:
        assessment, reason = known_landmarks[pid]
    elif n_concepts <= 4:
        assessment = "likely_artifact"
        reason = f"Only {n_concepts} concepts - extreme rarity may be from sparse concept assignment, not true paradigm shift"
    elif n_concepts == 5 and z_spread > 4.5:
        assessment = "suspect_artifact"
        reason = f"Low concept count ({n_concepts}) with extreme z_spread ({z_spread:.2f}) - rarity-driven score inflation"
    elif n_concepts >= 10:
        assessment = "plausible"
        reason = f"High concept count ({n_concepts}) suggests genuine cross-domain breadth"
    elif title and any(w in title.lower() for w in ['comment on', 'reply to', 'erratum', 'corrigendum']):
        assessment = "artifact"
        reason = "Comment/reply/erratum - not a paradigm shift"
    elif title and any(w in title.lower() for w in ['standalone version', 'software', 'package']):
        assessment = "artifact_software"
        reason = "Software tool paper, not a paradigm shift"
    else:
        assessment = "unclear"
        reason = f"Moderate concept count ({n_concepts}), would need citation/impact data to verify"

    papers.append({
        'rank': len(papers) + 1,
        'paper_id': pid,
        'arxiv_url': f'https://arxiv.org/abs/{pid}',
        'title': title,
        'authors': authors[:5],
        'year': year,
        'score': round(score, 2),
        'domain': domain,
        'n_concepts': n_concepts,
        'z_spread': round(z_spread, 2),
        'rarity_density': round(rarity_d, 4) if rarity_d else None,
        'spread_rare': round(spread_r, 4) if spread_r else None,
        'weight_rare': round(weight_r, 4) if weight_r else None,
        'assessment': assessment,
        'assessment_reason': reason
    })

# Count assessments
from collections import Counter
assess_counts = Counter(p['assessment'] for p in papers)

# Domain distribution in extinctions
ic.execute("SELECT domain, COUNT(*) FROM paper_scale WHERE tier='extinction' GROUP BY domain ORDER BY COUNT(*) DESC")
ext_by_domain = {r[0]: r[1] for r in ic.fetchall()}

# Year distribution in extinctions
ic.execute("SELECT year, COUNT(*) FROM paper_scale WHERE tier='extinction' GROUP BY year ORDER BY year")
ext_by_year = {str(r[0]): r[1] for r in ic.fetchall()}

# Overall assessment
n_artifact = assess_counts.get('likely_artifact', 0) + assess_counts.get('artifact', 0) + assess_counts.get('artifact_software', 0) + assess_counts.get('suspect_artifact', 0)
n_legit = assess_counts.get('legitimate_niche', 0) + assess_counts.get('plausible', 0)
n_unclear = assess_counts.get('unclear', 0) + assess_counts.get('unknown', 0)

overall = {
    'verdict': 'SCALE_NEEDS_CALIBRATION',
    'summary': (
        f"Of the top 30 extinction papers, {n_artifact} show signs of scoring artifacts "
        f"(low concept count inflating rarity), {n_legit} look like legitimate niche contributions, "
        f"and {n_unclear} are unclear without citation data. "
        "The main issue: the score heavily rewards papers that touch very few but very rare concepts, "
        "producing extreme z_spread values. A paper touching 5 rare concepts scores higher than "
        "a genuinely cross-disciplinary paper touching 13 concepts. "
        "None of the top 30 are obvious paradigm shifts (no Hawking radiation, no graphene Nobel, "
        "no CRISPR, no deep learning breakthroughs). The extinction tier is capturing statistical "
        "outliers in concept rarity, not scientific impact."
    ),
    'recommendations': [
        "Add citation count as a multiplier or filter (papers with < 50 citations should not be extinction)",
        "Penalize papers with n_concepts <= 5 -- rarity on few concepts is noise, not signal",
        "Consider a floor on concept count for extinction tier (e.g., >= 8)",
        "Cross-validate against known landmark papers (graphene, LIGO, Higgs, etc.) to check if they appear",
        "The z_spread metric dominates the score -- consider capping its contribution or using log(z_spread)"
    ]
}

report = {
    'generated': '2026-03-29',
    'description': 'Validation of top extinction-tier papers from impact_scale.db',
    'tier_distribution': tier_dist,
    'tier_percentages': {k: round(100*v/total, 2) for k, v in tier_dist.items()},
    'tier_score_ranges': tier_stats,
    'extinction_by_domain': ext_by_domain,
    'extinction_by_year': ext_by_year,
    'assessment_summary': dict(assess_counts),
    'top_30_extinction_papers': papers,
    'overall_assessment': overall
}

out_path = 'd:/ygg/yggdrasil-engine/data/results/scan_impact_validation.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"Report written to {out_path}")
print(f"\nTier distribution: {json.dumps(tier_dist, indent=2)}")
print(f"\nExtinction total: {tier_dist.get('extinction', 0)} / {total} ({100*tier_dist.get('extinction',0)/total:.3f}%)")
print(f"\nAssessment breakdown: {dict(assess_counts)}")
print(f"\nVerdict: {overall['verdict']}")
print(f"\nTop 5 extinction papers:")
for p in papers[:5]:
    print(f"  {p['rank']}. [{p['score']}] {p['paper_id']} -- {p['title']}")
    print(f"     {p['assessment']}: {p['assessment_reason']}")

impact.close()
wt3.close()
