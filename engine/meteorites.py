"""
YGGDRASIL ENGINE — Météorites V3
=================================
Blast Sedov-Taylor adapté au mycelium + bougies OHLC + 7 deltas.

Chaque percée majeure = une météorite qui frappe le sol (S-2→S0).
Le blast se propage dans le mycelium. On mesure l'impact avec 7 indicateurs.

Formules sourcées:
- Sedov 1946, Taylor 1950, von Neumann 1947: blast wave
- Holsapple 1993: crater scaling (référence, pas implémenté ici)
- Bebber 2007: meshedness α
- Freeman 1977: betweenness centrality
- Tero 2010: Physarum
- Chung 1997: spectral layout

Voir docs/formulas.tex pour les sources complètes avec DOI.

Auteur: Sky × Claude (Opus 4.6) — Session 7, 24 fév 2026
"""
import numpy as np
import networkx as nx
from dataclasses import dataclass, field
from typing import Optional
from scipy.optimize import curve_fit


# =============================================================================
# CONSTANTES PHYSIQUES (Sedov-Taylor)
# =============================================================================

# β pour différents γ (adiabatic index)
# Source: Kamm 2000 / Sedov 1959
BETA_TABLE = {
    1.2:   1.237,
    7/5:   1.033,   # air diatomique (γ=1.4)
    5/3:   1.152,   # gaz monoatomique (γ≈1.667)
    2.0:   1.268,
}

# Strate heights (pour le calcul d'énergie d'impact)
STRATE_HEIGHT = {
    "S-2": -2,  # glyphes
    "S-1": -1,  # métiers
    "S0":   0,  # formules prouvées
    "S1":   1,  # structures récursives
    "S2":   2,  # récursion²
    "S3":   3,  # conjectures
    "S4":   4,  # logique supérieure
    "S5":   5,  # presque indécidable
    "S6":   6,  # indécidable
}


# =============================================================================
# SEDOV-TAYLOR — Formules de blast
# =============================================================================

def blast_radius(E: float, rho0: float, t: float, beta: float = 1.033) -> float:
    """
    Rayon du front de choc Sedov-Taylor.

    R(t) = β × (E × t² / ρ₀)^(1/5)

    Source: Taylor 1950, Sedov 1946.

    Args:
        E:     énergie d'impact (strate_height × continents_touchés)
        rho0:  densité du milieu = meshedness α locale avant impact
        t:     temps depuis l'impact (mois)
        beta:  constante sans dimension (~1.033 pour γ=7/5)

    Returns:
        R(t) = nombre de concepts affectés à t mois
    """
    if E <= 0 or rho0 <= 0 or t <= 0:
        return 0.0
    return beta * (E * t**2 / rho0) ** 0.2


def blast_velocity(E: float, rho0: float, t: float, beta: float = 1.033) -> float:
    """
    Vitesse du front de choc (dérivée de R).

    Ṙ(t) = (2/5) × β × (E / ρ₀)^(1/5) × t^(-3/5)

    Le choc décélère en t^(-3/5).

    Args:
        E, rho0, t, beta: mêmes que blast_radius

    Returns:
        Ṙ(t) = taux de nouveaux concepts affectés / mois
    """
    if E <= 0 or rho0 <= 0 or t <= 0:
        return 0.0
    return (2.0 / 5.0) * beta * (E / rho0) ** 0.2 * t ** (-0.6)


def impact_energy(strate: str, continents_touched: int) -> float:
    """
    Énergie d'impact d'une météorite.

    E = strate_height × continents_touchés

    Exemples:
        Shannon (S1 × 7 continents) = 7
        Poincaré (S3 × 1) = 3
        Gödel (S6 × 9) = 54

    Args:
        strate:              ex. "S1", "S3", "S6"
        continents_touched:  nombre de continents affectés (1-9)
    """
    height = STRATE_HEIGHT.get(strate, 0)
    if height <= 0:
        height = 1  # minimum pour S0 et en-dessous
    return float(height * continents_touched)


def post_shock_density(gamma: float = 1.4) -> float:
    """
    Ratio de compression post-choc (Rankine-Hugoniot).

    G(1) = (γ+1) / (γ-1)

    Pour γ=7/5 (air): compression = 6×
    Pour γ=5/3 (mono): compression = 4×

    Source: Rankine 1870, Hugoniot 1889.
    """
    if gamma <= 1.0:
        return float('inf')
    return (gamma + 1) / (gamma - 1)


def energy_partition(gamma: float = 1.4) -> tuple[float, float]:
    """
    Partition de l'énergie: cinétique vs thermique.

    Pour γ=7/5: ~28% cinétique (nouveaux ponts), ~72% thermique (renforcement)
    Pour γ=5/3: ~22% cinétique, ~78% thermique

    HYPOTHÈSE: cette partition s'applique au mycelium.
    À vérifier avec les boîtes de météorites.

    Valeurs exactes tirées de l'intégration numérique de la solution de similitude
    de Sedov (Kamm 2000, Table 4). Interpolation linéaire entre points connus.

    Returns:
        (fraction_kinetic, fraction_thermal)
    """
    # Valeurs exactes connues (intégration numérique, Kamm 2000)
    # Source: Kamm, J. R. (2000). "Evaluation of the Sedov-von Neumann-Taylor
    #         Blast Wave Solution." LA-UR-00-6055, Los Alamos.
    known = {
        1.2:   0.35,
        7/5:   0.28,   # γ=1.4 (air)
        5/3:   0.22,   # γ≈1.667 (monoatomique)
        2.0:   0.17,
    }
    gammas = sorted(known.keys())
    if gamma <= gammas[0]:
        kinetic = known[gammas[0]]
    elif gamma >= gammas[-1]:
        kinetic = known[gammas[-1]]
    else:
        for i in range(len(gammas) - 1):
            if gammas[i] <= gamma <= gammas[i + 1]:
                t = (gamma - gammas[i]) / (gammas[i + 1] - gammas[i])
                kinetic = known[gammas[i]] * (1 - t) + known[gammas[i + 1]] * t
                break
        else:
            kinetic = 0.28
    return kinetic, 1.0 - kinetic


# =============================================================================
# FRAMES — Snapshot du mycelium à un instant t
# =============================================================================

@dataclass
class Frame:
    """
    Snapshot du mycelium à un instant donné.
    Produit par V2 step 2B (frames cumulatives).
    """
    period: str                              # "YYYY" ou "YYYY-MM"
    n_concepts: int = 0                      # concepts actifs
    n_edges: int = 0                         # arêtes co-occurrence
    meshedness: float = 0.0                  # α (brique 1)
    bc: dict = field(default_factory=dict)   # {concept_id: BC_value}
    spectral_pos: dict = field(default_factory=dict)  # {concept_id: (x, z)}
    physarum_alive: int = 0                  # hyphes vivantes
    physarum_dead: int = 0                   # hyphes mortes
    p4_holes: list = field(default_factory=list)  # liste de trous ouverts
    concept_ids: set = field(default_factory=set)  # concepts présents


# =============================================================================
# 7 DELTAS — Indicateurs techniques sous chaque bougie
# =============================================================================

@dataclass
class Deltas:
    """
    7 indicateurs techniques entre frame_avant et frame_après.
    Calculés comme DELTA (après - avant).
    """
    volume: int = 0         # Δ1: nouvelles arêtes co-occurrence
    amplitude: float = 0.0  # Δ2: déplacement spectral des centroïdes
    bc_delta: float = 0.0   # Δ3: delta betweenness centrality
    alpha_delta: float = 0.0  # Δ4: delta meshedness
    p4_delta: int = 0       # Δ5: trous fermés - trous ouverts (net)
    physarum: int = 0       # Δ6: hyphes créées - hyphes mortes
    births: int = 0         # Δ7: concepts nés - concepts morts

    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "amplitude": round(self.amplitude, 4),
            "bc_delta": round(self.bc_delta, 4),
            "alpha_delta": round(self.alpha_delta, 4),
            "p4_delta": self.p4_delta,
            "physarum": self.physarum,
            "births": self.births,
        }

    def magnitude(self) -> float:
        """Norme L2 des 7 deltas (normalisés)."""
        v = np.array([
            self.volume / max(abs(self.volume), 1),
            self.amplitude,
            self.bc_delta,
            self.alpha_delta,
            self.p4_delta / max(abs(self.p4_delta), 1),
            self.physarum / max(abs(self.physarum), 1),
            self.births / max(abs(self.births), 1),
        ], dtype=float)
        return float(np.linalg.norm(v))


def compute_deltas(before: Frame, after: Frame) -> Deltas:
    """
    Calcule les 7 deltas entre deux frames.

    Args:
        before: frame AVANT l'impact de la météorite
        after:  frame APRÈS l'impact
    """
    d = Deltas()

    # Δ1 — Volume: nouvelles arêtes
    d.volume = after.n_edges - before.n_edges

    # Δ2 — Amplitude: déplacement spectral moyen des centroïdes
    common = before.spectral_pos.keys() & after.spectral_pos.keys()
    if common:
        displacements = []
        for cid in common:
            x0, z0 = before.spectral_pos[cid]
            x1, z1 = after.spectral_pos[cid]
            displacements.append(np.sqrt((x1 - x0)**2 + (z1 - z0)**2))
        d.amplitude = float(np.mean(displacements))

    # Δ3 — BC delta: somme des changements de betweenness centrality
    all_nodes = before.bc.keys() | after.bc.keys()
    if all_nodes:
        bc_changes = []
        for node in all_nodes:
            bc_before = before.bc.get(node, 0.0)
            bc_after = after.bc.get(node, 0.0)
            bc_changes.append(bc_after - bc_before)
        d.bc_delta = float(np.sum(np.abs(bc_changes)))

    # Δ4 — Alpha delta: meshedness
    d.alpha_delta = after.meshedness - before.meshedness

    # Δ5 — P4 delta: trous fermés vs ouverts
    holes_before = set(map(tuple, before.p4_holes)) if before.p4_holes else set()
    holes_after = set(map(tuple, after.p4_holes)) if after.p4_holes else set()
    closed = holes_before - holes_after
    opened = holes_after - holes_before
    d.p4_delta = len(closed) - len(opened)  # positif = net fermeture

    # Δ6 — Physarum: hyphes nettes
    alive_delta = after.physarum_alive - before.physarum_alive
    dead_delta = after.physarum_dead - before.physarum_dead
    d.physarum = alive_delta - dead_delta

    # Δ7 — Births: concepts nés - concepts morts
    born = after.concept_ids - before.concept_ids
    died = before.concept_ids - after.concept_ids
    d.births = len(born) - len(died)

    return d


# =============================================================================
# BOUGIE OHLC — Candlestick scientifique
# =============================================================================

@dataclass
class Candle:
    """
    Bougie OHLC d'une météorite scientifique.

    Open  = date d'ÉMISSION du paper
    High  = pic de reconfiguration maximale du mycelium
    Low   = creux (résistance paradigme / stabilisation)
    Close = date de VALIDATION (prouvé, répliqué, explosion citations)
    """
    name: str                    # ex. "Shannon 1948"
    strate: str                  # ex. "S1"
    continents_touched: int      # 1-9
    open_date: str               # "YYYY" ou "YYYY-MM"
    close_date: str = ""         # rempli quand on connaît la validation
    high_date: str = ""          # pic de reconfiguration
    low_date: str = ""           # creux de résistance
    E: float = 0.0               # énergie d'impact
    rho0: float = 0.0            # meshedness locale avant impact
    deltas_series: list = field(default_factory=list)  # [(period, Deltas), ...]

    def __post_init__(self):
        self.E = impact_energy(self.strate, self.continents_touched)

    @property
    def length(self) -> Optional[int]:
        """Longueur de la bougie en mois (temps de résistance du paradigme)."""
        if not self.close_date or not self.open_date:
            return None
        return _period_diff(self.open_date, self.close_date)

    @property
    def predicted_radius(self) -> list[tuple[int, float]]:
        """Rayon Sedov-Taylor prédit à chaque mois."""
        if self.E <= 0 or self.rho0 <= 0:
            return []
        results = []
        for t_months in range(1, 121):  # 10 ans max
            r = blast_radius(self.E, self.rho0, t_months)
            results.append((t_months, r))
        return results

    def find_high_low(self):
        """Trouve High (pic) et Low (creux) dans la série de deltas."""
        if not self.deltas_series:
            return
        magnitudes = [(p, d.magnitude()) for p, d in self.deltas_series]
        if magnitudes:
            self.high_date = max(magnitudes, key=lambda x: x[1])[0]
            self.low_date = min(magnitudes, key=lambda x: x[1])[0]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "strate": self.strate,
            "continents": self.continents_touched,
            "E": self.E,
            "rho0": round(self.rho0, 4),
            "open": self.open_date,
            "close": self.close_date,
            "high": self.high_date,
            "low": self.low_date,
            "length_months": self.length,
            "n_measures": len(self.deltas_series),
        }


# =============================================================================
# BOÎTES DE MESURE — Accumulation des météorites
# =============================================================================

@dataclass
class MeteoriteBox:
    """
    Boîte de mesure d'une météorite.
    On accumule les boîtes pour construire la SIGNATURE TYPE.
    """
    candle: Candle
    measured_radii: list = field(default_factory=list)  # [(t_months, R_observed)]
    deltas_at_peak: Optional[Deltas] = None

    def to_dict(self) -> dict:
        d = self.candle.to_dict()
        d["measured_radii"] = self.measured_radii
        if self.deltas_at_peak:
            d["deltas_at_peak"] = self.deltas_at_peak.to_dict()
        return d


class MeteoriteRegistry:
    """
    Registre de toutes les météorites mesurées.
    Accumule les boîtes → calcule la signature moyenne → calibre β et γ.
    """

    def __init__(self):
        self.boxes: list[MeteoriteBox] = []

    def add_box(self, box: MeteoriteBox):
        self.boxes.append(box)

    def signature(self) -> Optional[Deltas]:
        """
        Signature moyenne d'impact: moyenne des deltas au pic (high) de chaque boîte.
        """
        peaks = [b.deltas_at_peak for b in self.boxes if b.deltas_at_peak]
        if not peaks:
            return None

        avg = Deltas()
        n = len(peaks)
        avg.volume = sum(p.volume for p in peaks) // n
        avg.amplitude = sum(p.amplitude for p in peaks) / n
        avg.bc_delta = sum(p.bc_delta for p in peaks) / n
        avg.alpha_delta = sum(p.alpha_delta for p in peaks) / n
        avg.p4_delta = sum(p.p4_delta for p in peaks) // n
        avg.physarum = sum(p.physarum for p in peaks) // n
        avg.births = sum(p.births for p in peaks) // n
        return avg

    def fit_sedov(self) -> dict:
        """
        Calibre β (et optionnellement l'exposant) depuis les boîtes accumulées.

        Fit R(t) = β × (E × t² / ρ₀)^(1/5) sur les données mesurées.

        Returns:
            {"beta": float, "exponent": float, "r_squared": float, "n_points": int}
        """
        # Rassembler tous les points (E, ρ₀, t, R_observed)
        points = []
        for box in self.boxes:
            E = box.candle.E
            rho0 = box.candle.rho0
            if E <= 0 or rho0 <= 0:
                continue
            for t, R_obs in box.measured_radii:
                if t > 0 and R_obs > 0:
                    points.append((E, rho0, t, R_obs))

        if len(points) < 3:
            return {"beta": 1.033, "exponent": 0.2, "r_squared": 0.0,
                    "n_points": len(points), "status": "insufficient_data"}

        E_arr = np.array([p[0] for p in points])
        rho_arr = np.array([p[1] for p in points])
        t_arr = np.array([p[2] for p in points])
        R_obs = np.array([p[3] for p in points])

        # x = (E * t² / ρ₀) → R = β * x^α avec α théorique = 0.2
        x = E_arr * t_arr**2 / rho_arr

        def sedov_model(x, beta, alpha):
            return beta * np.power(x, alpha)

        try:
            popt, pcov = curve_fit(
                sedov_model, x, R_obs,
                p0=[1.0, 0.2],
                bounds=([0.01, 0.05], [10.0, 0.5]),
                maxfev=5000,
            )
            beta_fit, alpha_fit = popt

            # R²
            R_pred = sedov_model(x, *popt)
            ss_res = np.sum((R_obs - R_pred)**2)
            ss_tot = np.sum((R_obs - np.mean(R_obs))**2)
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

            return {
                "beta": round(float(beta_fit), 4),
                "exponent": round(float(alpha_fit), 4),
                "r_squared": round(float(r_squared), 4),
                "n_points": len(points),
                "status": "ok",
            }
        except Exception as e:
            return {
                "beta": 1.033,
                "exponent": 0.2,
                "r_squared": 0.0,
                "n_points": len(points),
                "status": f"fit_failed: {e}",
            }

    def predict_godel(self, beta: float = 1.033) -> dict:
        """
        Test Gödel: prédire l'impact de Gödel 1931 à partir de la signature moyenne.

        Gödel = première météorite. Avant lui: tout S0, plat, ρ₀ ≈ très bas.
        UNE seule mesure, pas de moyenne possible.
        → On applique la signature moyenne des autres météorites.

        Returns:
            {"predicted_R": [...], "signature": Deltas, "E": float}
        """
        sig = self.signature()
        E_godel = impact_energy("S6", 9)  # S6 × 9 continents = 54

        # ρ₀ pour Gödel: le sol en 1931 est très peu maillé
        # On ne peut pas le calculer sans la frame 1931 → placeholder
        rho0_godel = 0.01  # sera remplacé par la vraie valeur du winter tree

        predicted = []
        for t in range(1, 121):
            r = blast_radius(E_godel, rho0_godel, t, beta)
            predicted.append((t, round(r, 2)))

        return {
            "name": "Gödel 1931",
            "E": E_godel,
            "rho0_placeholder": rho0_godel,
            "predicted_R": predicted[:24],  # 2 ans
            "signature": sig.to_dict() if sig else None,
        }

    def summary(self) -> dict:
        return {
            "n_boxes": len(self.boxes),
            "meteorites": [b.candle.name for b in self.boxes],
            "fit": self.fit_sedov(),
            "signature": self.signature().to_dict() if self.signature() else None,
        }


# =============================================================================
# CATALOGUE — Météorites connues (à remplir avec les vraies dates)
# =============================================================================

KNOWN_METEORITES = [
    # (nom, strate, continents, open_date, close_date_approx)
    ("Shannon 1948",          "S1", 7, "1948",    "1950"),
    ("ADN Watson-Crick 1953", "S0", 5, "1953",    "1953"),
    ("Transistor 1947",       "S0", 6, "1947",    "1950"),
    ("Laser 1960",            "S0", 5, "1960",    "1964"),
    ("Gödel 1931",            "S6", 9, "1931",    "1931"),
    ("Turing 1936",           "S6", 4, "1936",    "1936"),
    ("CRISPR 2012",           "S0", 4, "2012",    "2020"),
    ("AlphaFold 2020",        "S0", 3, "2020",    "2021"),
    ("Gravitational waves 2016", "S1", 2, "2016", "2016"),
    ("Higgs boson 2012",      "S1", 2, "2012",    "2013"),
    ("mRNA vaccines 2020",    "S0", 4, "1990",    "2020"),  # Karikó 1990 → COVID 2020
    ("Internet TCP/IP 1974",  "S0", 7, "1974",    "1983"),
    ("Poincaré-Perelman 2003","S3", 1, "2003",    "2006"),
]


def build_catalog() -> list[Candle]:
    """Construit le catalogue de bougies à partir des météorites connues."""
    candles = []
    for name, strate, conts, open_d, close_d in KNOWN_METEORITES:
        c = Candle(
            name=name,
            strate=strate,
            continents_touched=conts,
            open_date=open_d,
            close_date=close_d,
        )
        candles.append(c)
    return candles


# =============================================================================
# MESURE — Mesurer l'impact d'une météorite sur le winter tree
# =============================================================================

def measure_impact(frames: dict[str, Frame], candle: Candle,
                   window_months: int = 60) -> MeteoriteBox:
    """
    Mesure l'impact d'une météorite en comparant les frames avant/après.

    Pour chaque mois t dans [open, open + window]:
        1. Récupérer frame(open) et frame(open + t)
        2. Calculer les 7 deltas
        3. Compter R(t) = concepts affectés (Δ7 cumulé)

    Args:
        frames:         {period: Frame} — toutes les frames disponibles
        candle:         la bougie à mesurer
        window_months:  fenêtre de mesure en mois (défaut 60 = 5 ans)

    Returns:
        MeteoriteBox avec mesures
    """
    open_p = candle.open_date
    frame_before = frames.get(open_p)
    if frame_before is None:
        # Chercher la frame la plus proche avant
        sorted_periods = sorted(frames.keys())
        candidates = [p for p in sorted_periods if p <= open_p]
        if candidates:
            frame_before = frames[candidates[-1]]
        else:
            return MeteoriteBox(candle=candle)

    candle.rho0 = frame_before.meshedness

    box = MeteoriteBox(candle=candle)

    # Générer les périodes à mesurer
    periods_to_check = _generate_periods(open_p, window_months)

    for t_months, period in enumerate(periods_to_check, 1):
        # Chercher frame: d'abord "YYYY-MM", sinon "YYYY" (avant 1980)
        frame_after = frames.get(period)
        if frame_after is None:
            frame_after = frames.get(period[:4])  # fallback yearly key
        if frame_after is None:
            continue

        # deltas sont TOUJOURS relatifs à frame_before (pré-impact)
        # → births = total concepts nés depuis l'impact, pas un delta incrémental
        deltas = compute_deltas(frame_before, frame_after)
        candle.deltas_series.append((period, deltas))

        # R(t) = concepts affectés = births cumulés (déjà cumulé par compute_deltas)
        box.measured_radii.append((t_months, abs(deltas.births)))

    # Trouver High/Low
    candle.find_high_low()

    # Delta au pic
    if candle.high_date:
        for period, d in candle.deltas_series:
            if period == candle.high_date:
                box.deltas_at_peak = d
                break

    return box


def measure_all(frames: dict[str, Frame],
                window_months: int = 60) -> MeteoriteRegistry:
    """
    Mesure toutes les météorites connues sur les frames du winter tree.

    Args:
        frames:         {period: Frame} — du V2 step 2B
        window_months:  fenêtre de mesure (défaut 5 ans)

    Returns:
        MeteoriteRegistry avec toutes les boîtes
    """
    registry = MeteoriteRegistry()
    catalog = build_catalog()

    for candle in catalog:
        box = measure_impact(frames, candle, window_months)
        if box.measured_radii:
            registry.add_box(box)

    return registry


# =============================================================================
# UTILITAIRES
# =============================================================================

def _period_diff(p1: str, p2: str) -> int:
    """Différence en mois entre deux périodes ("YYYY" ou "YYYY-MM")."""
    y1, m1 = _parse_period(p1)
    y2, m2 = _parse_period(p2)
    return (y2 - y1) * 12 + (m2 - m1)


def _parse_period(p: str) -> tuple[int, int]:
    """Parse "YYYY" → (year, 6) ou "YYYY-MM" → (year, month)."""
    parts = p.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 6  # milieu d'année par défaut
    return year, month


def _generate_periods(start: str, n_months: int) -> list[str]:
    """Génère n_months périodes mensuelles à partir de start."""
    y, m = _parse_period(start)
    periods = []
    for _ in range(n_months):
        m += 1
        if m > 12:
            m = 1
            y += 1
        periods.append(f"{y:04d}-{m:02d}")
    return periods


# =============================================================================
# CORRÉLATION BOUGIE ↔ TYPE DE TROU
# =============================================================================

def classify_candle(candle: Candle) -> str:
    """
    Prédit le type de trou d'après la bougie (hypothèse Sedov-Taylor + ρ₀).

    - ρ₀ élevé + bougie moyenne → Trou Technique (A)
    - ρ₀ faible + bougie courte → Trou Conceptuel (B)
    - ρ₀ élevé + bougie longue  → Trou Perceptuel (C)

    HYPOTHÈSE à vérifier avec les boîtes accumulées.
    """
    length = candle.length
    if length is None:
        return "unknown"

    rho = candle.rho0

    if rho > 0.15 and length > 120:     # > 10 ans + sol dense
        return "C_perceptual"
    elif rho < 0.05 and length < 24:     # < 2 ans + sol vide
        return "B_conceptual"
    elif rho > 0.10 and 24 <= length <= 120:  # 2-10 ans + sol dense
        return "A_technical"
    else:
        return "mixed"


# =============================================================================
# ENTRY POINT — Pour test rapide
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  YGGDRASIL — MODULE MÉTÉORITES V3")
    print("=" * 60)

    # Test des formules de base
    print("\n--- Sedov-Taylor (test unitaire) ---")
    E_test = impact_energy("S1", 7)  # Shannon
    print(f"Shannon 1948: E = {E_test}")
    print(f"  R(12 mois, ρ₀=0.15) = {blast_radius(E_test, 0.15, 12):.2f}")
    print(f"  R(60 mois, ρ₀=0.15) = {blast_radius(E_test, 0.15, 60):.2f}")
    print(f"  Ṙ(12 mois, ρ₀=0.15) = {blast_velocity(E_test, 0.15, 12):.4f}")

    E_godel = impact_energy("S6", 9)
    print(f"\nGödel 1931: E = {E_godel}")
    print(f"  R(12 mois, ρ₀=0.01) = {blast_radius(E_godel, 0.01, 12):.2f}")
    print(f"  R(60 mois, ρ₀=0.01) = {blast_radius(E_godel, 0.01, 60):.2f}")

    print("\n--- Partition énergie ---")
    k, th = energy_partition(1.4)
    print(f"  γ=7/5: {k:.1%} cinétique, {th:.1%} thermique")
    k, th = energy_partition(5/3)
    print(f"  γ=5/3: {k:.1%} cinétique, {th:.1%} thermique")

    print("\n--- Compression post-choc ---")
    print(f"  γ=7/5: {post_shock_density(1.4):.1f}× (attendu: 6.0×)")
    print(f"  γ=5/3: {post_shock_density(5/3):.1f}× (attendu: 4.0×)")

    print("\n--- Catalogue météorites ---")
    catalog = build_catalog()
    for c in catalog:
        length = c.length
        l_str = f"{length:>4}" if length is not None else "   ?"
        print(f"  {c.name:30s} E={c.E:5.0f}  bougie={l_str} mois")

    print("\n--- Corrélation bougie ↔ trou (placeholder ρ₀) ---")
    for c in catalog:
        c.rho0 = 0.12  # placeholder
        t = classify_candle(c)
        print(f"  {c.name:30s} → {t}")

    print("\n" + "=" * 60)
    print("  MODULE OK — En attente des frames V2 pour mesure réelle")
    print("=" * 60)
