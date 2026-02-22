"""Backward-compatibility shim. Real module at engine.core.scisci"""
from engine.core.scisci import *  # noqa: F401,F403
from engine.core.scisci import (
    fitness_wang_barabasi, disruption_index, uzzi_zscore,
    q_factor_sinatra, co_occurrence_strength
)
