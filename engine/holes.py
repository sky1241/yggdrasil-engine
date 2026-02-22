"""Backward-compatibility shim. Real module at engine.core.holes"""
from engine.core.holes import *  # noqa: F401,F403
from engine.core.holes import (
    HoleDetector, DomainPair, CONTINENTS,
    score_technical, score_conceptual, score_perceptual,
    map_symbol_to_continents
)
