"""Backward-compatibility shim. Real module at engine.core.symbols"""
from engine.core.symbols import *  # noqa: F401,F403
from engine.core.symbols import SymbolDatabase, Symbol, load, SymbolDatabase as _SD
from engine.core.symbols import DATA_DIR, STRATE_COLORS, STRATE_NAMES, STRATE_CENTERS
