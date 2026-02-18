"""
YGGDRASIL ENGINE — Symbols Module
794 symboles mathématiques × 7 strates de complexité
"""
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Couleurs des strates (RGB)
STRATE_COLORS = {
    0: (74, 222, 128),    # SOL — vert
    1: (96, 165, 250),    # HALTING — bleu
    2: (167, 139, 250),   # LIMITE — violet
    3: (244, 114, 182),   # MOTIF — rose
    4: (251, 191, 36),    # CIEL — jaune
    5: (251, 146, 60),    # HYP — orange
    6: (239, 68, 68),     # PLAFOND — rouge
}

STRATE_NAMES = {
    0: "SOL · Δ⁰₀ · Décidable",
    1: "NUAGE 1 · Σ⁰₁ · Halting",
    2: "NUAGE 2 · Σ⁰₂ · Limite",
    3: "NUAGE n · Σ⁰ₙ · Motif",
    4: "CIEL · AH · Arithmétique",
    5: "HYPERARITHMÉTIQUE · ω₁ᶜᵏ",
    6: "PLAFOND · Turing 1936",
}

STRATE_CENTERS = {
    0: "=",
    1: "K",
    2: "∅'",
    3: "PH",
    4: "ω",
    5: "ω₁ᶜᵏ",
    6: "BB(n)",
}


class Symbol:
    """Un symbole mathématique avec sa position dans Yggdrasil."""
    
    def __init__(self, s: str, from_name: str, domain: str, strate: int, 
                 px: float = 0, pz: float = 0):
        self.s = s
        self.from_name = from_name
        self.domain = domain
        self.strate = strate
        self.px = px
        self.pz = pz
    
    @property
    def color(self):
        return STRATE_COLORS[self.strate]
    
    @property
    def is_center(self):
        return self.s == STRATE_CENTERS.get(self.strate)
    
    def to_dict(self):
        return {
            "s": self.s,
            "from": self.from_name,
            "domain": self.domain,
            "strate": self.strate,
            "px": self.px,
            "pz": self.pz,
            "color": list(self.color),
            "is_center": self.is_center,
        }
    
    def __repr__(self):
        return f"Symbol('{self.s}', S{self.strate}, {self.domain})"


class SymbolDatabase:
    """Base de données des 794 symboles."""
    
    def __init__(self, filepath=None):
        self.symbols: list[Symbol] = []
        self._by_strate: dict[int, list[Symbol]] = {i: [] for i in range(7)}
        self._by_domain: dict[str, list[Symbol]] = {}
        
        if filepath is None:
            filepath = DATA_DIR / "strates_export.json"
        
        self.load(filepath)
    
    def load(self, filepath):
        """Charge les symboles depuis le JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.symbols = []
        self._by_strate = {i: [] for i in range(7)}
        self._by_domain = {}
        
        for strate_data in data.get("strates", []):
            strate_id = strate_data["id"]
            for sym_data in strate_data.get("symbols", []):
                sym = Symbol(
                    s=sym_data["s"],
                    from_name=sym_data.get("from", ""),
                    domain=sym_data.get("domain", ""),
                    strate=strate_id,
                    px=sym_data.get("px", 0),
                    pz=sym_data.get("pz", 0),
                )
                self.symbols.append(sym)
                self._by_strate[strate_id].append(sym)
                
                if sym.domain not in self._by_domain:
                    self._by_domain[sym.domain] = []
                self._by_domain[sym.domain].append(sym)
        
        print(f"[YGGDRASIL] Loaded {len(self.symbols)} symbols across {len(self._by_strate)} strata")
    
    def strate(self, n: int) -> list[Symbol]:
        """Retourne tous les symboles d'une strate."""
        return self._by_strate.get(n, [])
    
    def domain(self, name: str) -> list[Symbol]:
        """Retourne tous les symboles d'un domaine."""
        return self._by_domain.get(name, [])
    
    @property
    def domains(self) -> list[str]:
        """Liste tous les domaines."""
        return sorted(self._by_domain.keys())
    
    @property
    def sol(self) -> list[Symbol]:
        """Symboles S0 — les outils prouvés."""
        return self._by_strate[0]
    
    def stats(self) -> dict:
        """Statistiques globales."""
        return {
            "total": len(self.symbols),
            "by_strate": {f"S{i}": len(self._by_strate[i]) for i in range(7)},
            "by_domain": {d: len(syms) for d, syms in sorted(self._by_domain.items())},
            "domains_count": len(self._by_domain),
        }
    
    def export_viz_json(self, filepath=None) -> dict:
        """Exporte les données pour la visualisation 3D.
        Garde les positions px/pz originales (spectrales) et ajoute le continent."""
        from engine.holes import CONTINENTS

        # Build domain -> continent lookup
        continent_order = [
            ("Mathématiques Pures", "#1e3a8a"),
            ("Physique Fondamentale", "#7c3aed"),
            ("Ingénierie & Électricité", "#ea580c"),
            ("Informatique & IA", "#06b6d4"),
            ("Finance & Économie", "#eab308"),
            ("Biologie & Médecine", "#84cc16"),
            ("Chimie", "#f43f5e"),
        ]
        domain_to_continent = {}
        for ci, (cname, _color) in enumerate(continent_order):
            for dom in CONTINENTS.get(cname, []):
                domain_to_continent[dom] = ci

        viz_data = {
            "meta": {
                "total": len(self.symbols),
                "strate_counts": [len(self._by_strate[i]) for i in range(7)],
            },
            "strates": [],
            "continents": [
                {"name": name, "color": color}
                for name, color in continent_order
            ],
            "symbols": [],
        }

        for i in range(7):
            viz_data["strates"].append({
                "id": i,
                "name": STRATE_NAMES[i],
                "center": STRATE_CENTERS[i],
                "color": list(STRATE_COLORS[i]),
                "count": len(self._by_strate[i]),
                "y": -1.4 + i * 0.4,
            })

        for sym in self.symbols:
            d = sym.to_dict()
            d["continent"] = domain_to_continent.get(sym.domain, -1)
            viz_data["symbols"].append(d)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(viz_data, f, ensure_ascii=False, indent=2)
            print(f"[YGGDRASIL] Exported viz data to {filepath}")

        return viz_data


# Quick access
def load() -> SymbolDatabase:
    """Charge la base de symboles."""
    return SymbolDatabase()


if __name__ == "__main__":
    db = load()
    stats = db.stats()
    print(f"\n=== YGGDRASIL — {stats['total']} SYMBOLES ===\n")
    for strate, count in stats["by_strate"].items():
        print(f"  {strate}: {count} symboles")
    print(f"\n  {stats['domains_count']} domaines")
    print(f"\n  SOL (S0): {len(db.sol)} outils prouvés")
