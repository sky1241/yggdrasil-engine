"""YGGDRASIL ENGINE — Core modules (Phase 0-1 : fondations)"""
from .symbols import SymbolDatabase, Symbol, load, STRATE_COLORS, STRATE_NAMES, STRATE_CENTERS
from .holes import HoleDetector, score_technical, score_conceptual, score_perceptual, CONTINENTS, map_symbol_to_continents
from .scisci import fitness_wang_barabasi, disruption_index, uzzi_zscore, q_factor_sinatra, co_occurrence_strength
from .openalex import search_structural_hole
