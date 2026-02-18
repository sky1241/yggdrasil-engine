"""YGGDRASIL ENGINE — Moteur de détection de trous structurels"""
from .symbols import SymbolDatabase, load
from .holes import HoleDetector, score_technical, score_conceptual, score_perceptual
from .scisci import (
    fitness_wang_barabasi, disruption_index, uzzi_zscore,
    q_factor_sinatra, co_occurrence_strength
)

__version__ = "0.1.0"
