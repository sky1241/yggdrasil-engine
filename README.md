# 🌳 YGGDRASIL ENGINE

**Moteur de détection de trous structurels dans les réseaux scientifiques**

794 symboles × 7 strates de complexité × 3 types de trous × 3 systèmes de circulation

## Architecture

```
CIEL (S6) ─── BB(n), Ω ─── incompressible
    │
    │   ☁️ conjectures flottent ici
    │
SOL (S0) ─── 549 outils prouvés ─── le vrai terrain de jeu
    │
MYCELIUM ─── connexions invisibles entre domaines
```

## Structure

```
yggdrasil-engine/
├── engine/
│   ├── symbols.py       ← 794 symboles, 7 strates
│   ├── strata.py        ← définitions des strates
│   ├── continents.py    ← 7 métiers × symboles
│   ├── holes.py         ← détection 3 types de trous
│   ├── scisci.py        ← formules Wang-Barabási, Uzzi, Wu-Evans
│   └── openalex.py      ← API OpenAlex (250M papers)
├── data/
│   └── strates_export.json
├── viz/
│   └── index.html       ← cube 3D Three.js
├── tests/
│   └── test_engine.py
└── server.py            ← lance tout
```

## 3 Types de Trous Structurels

| Type | Mécanisme | Détection |
|------|-----------|-----------|
| **A — Technique** | Tout le monde SAIT où aller, personne ne PEUT | fitness stagnante, D-index bas |
| **B — Conceptuel** | Personne n'a l'IDÉE de connecter | co-occurrence = 0, z-score << 0 |
| **C — Perceptuel** | L'outil EXISTE, personne n'y CROIT | fitness haute, citations basses |

## Lancer

```bash
pip install flask numpy
python server.py
# → http://localhost:5000
```

## Données

- 794 symboles mathématiques classifiés en 7 strates (S0-S6)
- Strates basées sur la hiérarchie arithmétique (Post 1944)
- Validé sur 32 découvertes 2010-2025
- Données OpenAlex: 250M papers académiques

## Auteur

Sky — Versoix, CH — 2025-2026


---

## 🌿 LIANES — Les Escaliers de Secours

> "Perelman n'a pas pris l'ascenseur central. Il a pris la liane entropie."

Les symboles S0 utilisés par PLUSIEURS corps de métier sont les **lianes** — les escaliers de secours vers S3.

### Distribution

| Type | Count | Description |
|------|-------|-------------|
| 🌿🌿🌿 Universelle | 5 | 6+ continents (=, exp, ln, Σ, ∫) |
| 🌿🌿 Majeure | 29 | 4-5 continents |
| 🌿 Liane | 26 | 3 continents |
| 🌱 Pont | 9 | 2 continents |
| · Local | 480 | 1 continent |

### Validation: 9/10 découvertes S3 utilisent des lianes multi-continents

Seule exception: CRISPR (pont biologique pur, pas mathématique).

```bash
python engine/lianes.py
# → Analyse complète + export JSON
```
