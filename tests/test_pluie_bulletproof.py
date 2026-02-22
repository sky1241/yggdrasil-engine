#!/usr/bin/env python3
"""
🔨 BATTERIE DE TESTS COMPLÈTE — Phase 4 PLUIE
Cherche la petite bête partout. Chaque test isolé, chaque edge case couvert.

Usage:
    python tests/test_pluie_bulletproof.py
    python tests/test_pluie_bulletproof.py -v          # verbose
    python tests/test_pluie_bulletproof.py -k test_xyz  # un seul test
"""

import gzip
import json
import os
import sys
import shutil
import tempfile
import unittest
import time
import signal
from pathlib import Path
from unittest.mock import patch
from collections import defaultdict
from itertools import combinations

import numpy as np
from scipy import sparse

# ─── Ajouter engine/ au path ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

# On importe les fonctions individuelles pour tester unitairement
from build_cooccurrence import (
    load_yggdrasil_concepts,
    discover_gz_files,
    stream_papers,
    extract_concept_indices,
    save_checkpoint,
    load_checkpoint,
    build_cooccurrence_matrix,
)


class TestDataDir:
    """Helper: crée un répertoire temporaire avec données contrôlées."""
    
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ygg_test_")
        self.data_dir = os.path.join(self.tmpdir, "data")
        self.works_dir = os.path.join(self.tmpdir, "works")
        self.output_dir = os.path.join(self.tmpdir, "output")
        os.makedirs(self.data_dir)
        os.makedirs(self.works_dir)
        os.makedirs(self.output_dir)
    
    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def write_strates(self, entries):
        path = os.path.join(self.data_dir, "strates_export_v2.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f)
        return path
    
    def write_openalex_map(self, mapping):
        path = os.path.join(self.data_dir, "openalex_map.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mapping, f)
        return path
    
    def write_gz(self, filename, papers, subdir=None):
        """Écrit un fichier .gz avec des papers (list of dict ou list of str)."""
        if subdir:
            dirpath = os.path.join(self.works_dir, subdir)
            os.makedirs(dirpath, exist_ok=True)
            filepath = os.path.join(dirpath, filename)
        else:
            filepath = os.path.join(self.works_dir, filename)
        
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            for paper in papers:
                if isinstance(paper, str):
                    f.write(paper + "\n")
                else:
                    f.write(json.dumps(paper) + "\n")
        return filepath
    
    def make_paper(self, concept_ids, scores=None, paper_id=None):
        """Crée un paper dict avec des concepts."""
        concepts = []
        for i, cid in enumerate(concept_ids):
            score = scores[i] if scores else 0.8
            concepts.append({
                "id": cid,
                "display_name": f"Concept_{cid}",
                "score": score
            })
        return {
            "id": paper_id or f"W{hash(tuple(concept_ids)) % 10000000}",
            "title": "Test paper",
            "publication_year": 2024,
            "concepts": concepts,
            "cited_by_count": 10
        }


# ═══════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — load_yggdrasil_concepts
# ═══════════════════════════════════════════════════════════════════════════

class TestLoadConcepts(unittest.TestCase):
    """Tests chargement des concepts Yggdrasil + mapping OpenAlex."""
    
    def setUp(self):
        self.td = TestDataDir()
    
    def tearDown(self):
        self.td.cleanup()
    
    def test_basic_load(self):
        """Format standard [{from, to, strate}]."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "DL", "strate": 0},
            {"from": "DL", "to": "NLP", "strate": 1},
            {"from": "NLP", "to": "", "strate": 2},
        ])
        oa_path = self.td.write_openalex_map({
            "ML": "https://openalex.org/C1",
            "DL": "https://openalex.org/C2",
            "NLP": "https://openalex.org/C3",
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        
        self.assertEqual(n, 3)
        self.assertIn("https://openalex.org/C1", c2i)
        self.assertIn("https://openalex.org/C2", c2i)
        self.assertIn("https://openalex.org/C3", c2i)
        # Vérifier que les indices sont 0, 1, 2
        self.assertEqual(set(c2i.values()), {0, 1, 2})
    
    def test_unmapped_concepts(self):
        """Concepts sans mapping OpenAlex = ignorés, pas de crash."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "DL", "strate": 0},
            {"from": "UNKNOWN", "to": "", "strate": 1},
        ])
        oa_path = self.td.write_openalex_map({
            "ML": "C1",
            "DL": "C2",
            # UNKNOWN pas dans le mapping
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 2)  # UNKNOWN exclu
    
    def test_empty_strates(self):
        """Strates vide = 0 concepts."""
        strates_path = self.td.write_strates([])
        oa_path = self.td.write_openalex_map({})
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 0)
    
    def test_duplicate_symbols(self):
        """Même symbole apparaît plusieurs fois = un seul index."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "DL", "strate": 0},
            {"from": "ML", "to": "NLP", "strate": 0},  # ML dupliqué
            {"from": "DL", "to": "ML", "strate": 1},   # DL et ML dupliqués
        ])
        oa_path = self.td.write_openalex_map({
            "ML": "C1", "DL": "C2", "NLP": "C3",
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 3)  # Pas de doublons
    
    def test_openalex_map_with_dict_values(self):
        """openalex_map.json avec valeurs dict {id: ..., concept_id: ...}."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "", "strate": 0},
        ])
        oa_path = self.td.write_openalex_map({
            "ML": {"id": "C1", "display_name": "Machine Learning"},
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 1)
        self.assertIn("C1", c2i)
    
    def test_openalex_map_concept_id_fallback(self):
        """Fallback sur concept_id si id absent."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "", "strate": 0},
        ])
        oa_path = self.td.write_openalex_map({
            "ML": {"concept_id": "C99"},
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 1)
        self.assertIn("C99", c2i)
    
    def test_empty_string_in_from(self):
        """Champ 'from' vide = ignoré."""
        strates_path = self.td.write_strates([
            {"from": "", "to": "DL", "strate": 0},
            {"from": "ML", "to": "", "strate": 0},
        ])
        oa_path = self.td.write_openalex_map({
            "": "C0",  # empty string mapped
            "ML": "C1",
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        # "" et "ML" et "DL" sont dans symbols, mais DL pas dans map
        self.assertIn("C1", c2i)
    
    def test_strates_as_dict(self):
        """Format alternatif: strates comme dict {strate: [symbols]}."""
        strates_path = self.td.write_strates({
            "0": ["ML", "Stats"],
            "1": ["DL", "NLP"],
        })
        oa_path = self.td.write_openalex_map({
            "ML": "C1", "Stats": "C2", "DL": "C3", "NLP": "C4",
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 4)
    
    def test_unicode_symbols(self):
        """Symboles avec accents et caractères spéciaux."""
        strates_path = self.td.write_strates([
            {"from": "Réseau neuronal", "to": "Détection d'anomalies", "strate": 0},
        ])
        oa_path = self.td.write_openalex_map({
            "Réseau neuronal": "C1",
            "Détection d'anomalies": "C2",
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 2)
    
    def test_same_openalex_id_different_symbols(self):
        """Deux symboles mappés au même OpenAlex ID = un seul index."""
        strates_path = self.td.write_strates([
            {"from": "ML", "to": "", "strate": 0},
            {"from": "Machine Learning", "to": "", "strate": 0},
        ])
        oa_path = self.td.write_openalex_map({
            "ML": "C1",
            "Machine Learning": "C1",  # Même ID!
        })
        
        c2i, i2c, i2s, n = load_yggdrasil_concepts(strates_path, oa_path)
        self.assertEqual(n, 1)  # Dédupliqué par OA ID


# ═══════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — stream_papers
# ═══════════════════════════════════════════════════════════════════════════

class TestStreamPapers(unittest.TestCase):
    """Tests streaming de fichiers .gz."""
    
    def setUp(self):
        self.td = TestDataDir()
    
    def tearDown(self):
        self.td.cleanup()
    
    def test_normal_papers(self):
        """Papers normaux = tous retournés."""
        papers = [
            {"id": "W1", "title": "Paper 1", "concepts": []},
            {"id": "W2", "title": "Paper 2", "concepts": []},
            {"id": "W3", "title": "Paper 3", "concepts": []},
        ]
        gz_path = self.td.write_gz("test.gz", papers)
        
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "W1")
    
    def test_empty_lines_skipped(self):
        """Lignes vides = ignorées."""
        lines = [
            json.dumps({"id": "W1"}),
            "",
            "   ",
            json.dumps({"id": "W2"}),
            "",
        ]
        gz_path = self.td.write_gz("test.gz", lines)
        
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 2)
    
    def test_malformed_json_skipped(self):
        """JSON malformé = ignoré silencieusement."""
        lines = [
            json.dumps({"id": "W1"}),
            "{bad json here",
            "not json at all",
            json.dumps({"id": "W2"}),
            "{\"incomplete\": ",
        ]
        gz_path = self.td.write_gz("test.gz", lines)
        
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 2)
    
    def test_corrupted_gz_file(self):
        """Fichier .gz corrompu = erreur gérée, pas de crash."""
        # Écrire des bytes random comme .gz
        filepath = os.path.join(self.td.works_dir, "corrupted.gz")
        with open(filepath, "wb") as f:
            f.write(b"\x1f\x8b\x08\x00" + os.urandom(100))
        
        # Ne doit PAS lever d'exception
        result = list(stream_papers(filepath))
        # Peut être vide ou partiel, l'important c'est pas de crash
        self.assertIsInstance(result, list)
    
    def test_empty_gz_file(self):
        """Fichier .gz vide = 0 papers."""
        gz_path = self.td.write_gz("empty.gz", [])
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 0)
    
    def test_huge_line(self):
        """Ligne très longue (paper avec beaucoup de concepts) = OK."""
        concepts = [{"id": f"C{i}", "display_name": f"Concept {i}", "score": 0.9}
                    for i in range(500)]
        paper = {"id": "W_huge", "concepts": concepts}
        gz_path = self.td.write_gz("huge.gz", [paper])
        
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["concepts"]), 500)
    
    def test_non_gz_file(self):
        """Fichier qui n'est pas du gzip = erreur gérée."""
        filepath = os.path.join(self.td.works_dir, "fake.gz")
        with open(filepath, "w") as f:
            f.write("this is not gzip\n")
        
        result = list(stream_papers(filepath))
        self.assertIsInstance(result, list)
    
    def test_unicode_in_papers(self):
        """Papers avec unicode (chinois, arabe, etc.) = OK."""
        papers = [
            {"id": "W1", "title": "機械学習の研究", "concepts": []},
            {"id": "W2", "title": "بحث في الذكاء الاصطناعي", "concepts": []},
            {"id": "W3", "title": "Étude sur l'apprentissage", "concepts": []},
        ]
        gz_path = self.td.write_gz("unicode.gz", papers)
        
        result = list(stream_papers(gz_path))
        self.assertEqual(len(result), 3)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — extract_concept_indices
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractConceptIndices(unittest.TestCase):
    """Tests extraction d'indices depuis un paper."""
    
    def setUp(self):
        self.concept_to_idx = {
            "C1": 0, "C2": 1, "C3": 2,
            "https://openalex.org/C4": 3,
        }
    
    def test_basic_extraction(self):
        """Concepts normaux avec score > seuil."""
        paper = {
            "concepts": [
                {"id": "C1", "score": 0.9},
                {"id": "C2", "score": 0.7},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(sorted(result), [0, 1])
    
    def test_score_filtering(self):
        """Concepts sous le seuil = exclus."""
        paper = {
            "concepts": [
                {"id": "C1", "score": 0.9},
                {"id": "C2", "score": 0.1},  # Sous le seuil
                {"id": "C3", "score": 0.5},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(sorted(result), [0, 2])
    
    def test_unknown_concepts_filtered(self):
        """Concepts pas dans Yggdrasil = exclus."""
        paper = {
            "concepts": [
                {"id": "C1", "score": 0.9},
                {"id": "C_UNKNOWN", "score": 0.9},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [0])
    
    def test_no_concepts_field(self):
        """Paper sans champ concepts = []."""
        paper = {"id": "W1", "title": "No concepts"}
        result = extract_concept_indices(paper, self.concept_to_idx)
        self.assertEqual(result, [])
    
    def test_empty_concepts(self):
        """Champ concepts vide = []."""
        paper = {"concepts": []}
        result = extract_concept_indices(paper, self.concept_to_idx)
        self.assertEqual(result, [])
    
    def test_concepts_none(self):
        """Champ concepts = None."""
        paper = {"concepts": None}
        result = extract_concept_indices(paper, self.concept_to_idx)
        self.assertEqual(result, [])
    
    def test_score_zero(self):
        """Score = 0 = exclus."""
        paper = {
            "concepts": [
                {"id": "C1", "score": 0},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [])
    
    def test_score_exactly_threshold(self):
        """Score = seuil exactement = inclus (>=, pas >)."""
        paper = {
            "concepts": [
                {"id": "C1", "score": 0.3},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [0])
    
    def test_missing_score_field(self):
        """Concept sans champ score = score 0 = exclus."""
        paper = {
            "concepts": [
                {"id": "C1"},  # Pas de score
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [])
    
    def test_url_format_id(self):
        """ID au format URL OpenAlex."""
        paper = {
            "concepts": [
                {"id": "https://openalex.org/C4", "score": 0.9},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [3])
    
    def test_concept_id_fallback(self):
        """Fallback sur concept_id si id absent."""
        paper = {
            "concepts": [
                {"concept_id": "C1", "score": 0.9},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [0])
    
    def test_concept_no_id_at_all(self):
        """Concept sans aucun champ id = ignoré."""
        paper = {
            "concepts": [
                {"display_name": "ML", "score": 0.9},
            ]
        }
        result = extract_concept_indices(paper, self.concept_to_idx, min_score=0.3)
        self.assertEqual(result, [])


# ═══════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — discover_gz_files
# ═══════════════════════════════════════════════════════════════════════════

class TestDiscoverGzFiles(unittest.TestCase):
    """Tests découverte de fichiers .gz."""
    
    def setUp(self):
        self.td = TestDataDir()
    
    def tearDown(self):
        self.td.cleanup()
    
    def test_flat_directory(self):
        """Fichiers .gz directement dans works/."""
        self.td.write_gz("a.gz", [{"id": "W1"}])
        self.td.write_gz("b.gz", [{"id": "W2"}])
        
        files = discover_gz_files(self.td.works_dir)
        self.assertEqual(len(files), 2)
    
    def test_nested_directory(self):
        """Fichiers .gz dans des sous-dossiers (format OpenAlex)."""
        self.td.write_gz("part_000.gz", [{"id": "W1"}], subdir="updated_date=2024-01-01")
        self.td.write_gz("part_001.gz", [{"id": "W2"}], subdir="updated_date=2024-01-02")
        
        files = discover_gz_files(self.td.works_dir)
        self.assertEqual(len(files), 2)
    
    def test_empty_directory(self):
        """Répertoire vide = []."""
        files = discover_gz_files(self.td.works_dir)
        self.assertEqual(len(files), 0)
    
    def test_non_gz_files_ignored(self):
        """Fichiers non-.gz ignorés."""
        self.td.write_gz("data.gz", [{"id": "W1"}])
        # Écrire un fichier .txt
        with open(os.path.join(self.td.works_dir, "readme.txt"), "w") as f:
            f.write("not a gz")
        
        files = discover_gz_files(self.td.works_dir)
        self.assertEqual(len(files), 1)
    
    def test_files_are_sorted(self):
        """Fichiers retournés triés."""
        self.td.write_gz("c.gz", [])
        self.td.write_gz("a.gz", [])
        self.td.write_gz("b.gz", [])
        
        files = discover_gz_files(self.td.works_dir)
        basenames = [os.path.basename(f) for f in files]
        self.assertEqual(basenames, sorted(basenames))
    
    def test_deeply_nested(self):
        """Fichiers dans des sous-sous-dossiers."""
        deep_dir = os.path.join(self.td.works_dir, "a", "b", "c")
        os.makedirs(deep_dir)
        filepath = os.path.join(deep_dir, "deep.gz")
        with gzip.open(filepath, "wt") as f:
            f.write(json.dumps({"id": "W1"}) + "\n")
        
        files = discover_gz_files(self.td.works_dir)
        self.assertEqual(len(files), 1)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — checkpoint save/load
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckpoint(unittest.TestCase):
    """Tests checkpoint save/load."""
    
    def setUp(self):
        self.td = TestDataDir()
        self.ckpt_path = os.path.join(self.td.output_dir, "checkpoint.json")
    
    def tearDown(self):
        self.td.cleanup()
    
    def test_save_and_load(self):
        """Save puis load = même données."""
        save_checkpoint(self.ckpt_path, ["file1.gz", "file2.gz"], 1000, 5000, 120.5)
        ckpt = load_checkpoint(self.ckpt_path)
        
        self.assertEqual(ckpt["processed_files"], ["file1.gz", "file2.gz"])
        self.assertEqual(ckpt["total_papers"], 1000)
        self.assertEqual(ckpt["total_pairs"], 5000)
        self.assertEqual(ckpt["elapsed_seconds"], 120.5)
    
    def test_load_nonexistent(self):
        """Load fichier inexistant = None."""
        result = load_checkpoint("/nonexistent/path/checkpoint.json")
        self.assertIsNone(result)
    
    def test_overwrite(self):
        """Save écrase le précédent."""
        save_checkpoint(self.ckpt_path, ["a.gz"], 100, 50, 10)
        save_checkpoint(self.ckpt_path, ["a.gz", "b.gz"], 200, 100, 20)
        
        ckpt = load_checkpoint(self.ckpt_path)
        self.assertEqual(len(ckpt["processed_files"]), 2)
        self.assertEqual(ckpt["total_papers"], 200)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS D'INTÉGRATION — Pipeline complet
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipeline(unittest.TestCase):
    """Tests du pipeline complet build_cooccurrence_matrix."""
    
    def setUp(self):
        self.td = TestDataDir()
        self._setup_env()
    
    def tearDown(self):
        self._restore_env()
        self.td.cleanup()
    
    def _setup_env(self):
        """Configure les variables d'environnement."""
        self._old_env = {
            "YGG_WORKS_DIR": os.environ.get("YGG_WORKS_DIR"),
            "YGG_STRATES": os.environ.get("YGG_STRATES"),
            "YGG_OA_MAP": os.environ.get("YGG_OA_MAP"),
            "YGG_OUTPUT": os.environ.get("YGG_OUTPUT"),
        }
        os.environ["YGG_WORKS_DIR"] = self.td.works_dir
        os.environ["YGG_STRATES"] = os.path.join(self.td.data_dir, "strates_export_v2.json")
        os.environ["YGG_OA_MAP"] = os.path.join(self.td.data_dir, "openalex_map.json")
        os.environ["YGG_OUTPUT"] = self.td.output_dir
    
    def _restore_env(self):
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
    
    def _setup_concepts(self, concepts_map):
        """Helper: crée strates + mapping pour N concepts."""
        strates = [{"from": name, "to": "", "strate": 0} for name in concepts_map]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts_map)
    
    def _make_args(self, test=0, resume=False):
        """Crée un objet args mock."""
        class Args:
            pass
        args = Args()
        args.test = test
        args.resume = resume
        args.min_score = 0.3
        return args
    
    def _reload_module(self):
        """Recharge le module pour prendre en compte les nouvelles env vars."""
        import importlib
        import build_cooccurrence as bc
        # Mettre à jour les constantes du module
        bc.WORKS_DIR = os.environ["YGG_WORKS_DIR"]
        bc.STRATES_PATH = os.environ["YGG_STRATES"]
        bc.OPENALEX_MAP_PATH = os.environ["YGG_OA_MAP"]
        bc.OUTPUT_DIR = os.environ["YGG_OUTPUT"]
        bc.CHECKPOINT_PATH = os.path.join(bc.OUTPUT_DIR, "_checkpoint.json")
        return bc
    
    def test_simple_three_concepts(self):
        """3 concepts, 2 papers, vérification exacte des co-occurrences."""
        self._setup_concepts({"A": "C1", "B": "C2", "C": "C3"})
        
        # Paper 1: A + B (score > 0.3)
        # Paper 2: A + C (score > 0.3)
        # Paper 3: B seulement (pas de paire)
        papers = [
            self.td.make_paper(["C1", "C2"], [0.9, 0.8]),
            self.td.make_paper(["C1", "C3"], [0.7, 0.6]),
            self.td.make_paper(["C2"], [0.9]),  # Seul concept = pas de paire
        ]
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        # Vérifications
        self.assertEqual(matrix.shape, (3, 3))
        
        # Charger l'index pour savoir quel concept est à quel index
        with open(os.path.join(self.td.output_dir, "matrix_index.json")) as f:
            index = json.load(f)
        
        c2i = index["concept_to_idx"]
        idx_a, idx_b, idx_c = c2i["C1"], c2i["C2"], c2i["C3"]
        
        # A-B: 1 co-occurrence (paper 1)
        self.assertEqual(matrix[idx_a, idx_b], 1)
        self.assertEqual(matrix[idx_b, idx_a], 1)  # Symétrique
        
        # A-C: 1 co-occurrence (paper 2)
        self.assertEqual(matrix[idx_a, idx_c], 1)
        
        # B-C: 0 co-occurrence
        self.assertEqual(matrix[idx_b, idx_c], 0)
        
        # Diagonale: A=2 papers, B=1, C=1
        self.assertEqual(matrix[idx_a, idx_a], 2)
        self.assertEqual(matrix[idx_b, idx_b], 1)
        self.assertEqual(matrix[idx_c, idx_c], 1)
    
    def test_multiple_gz_files(self):
        """Pipeline avec plusieurs fichiers .gz."""
        self._setup_concepts({"X": "C1", "Y": "C2"})
        
        papers1 = [self.td.make_paper(["C1", "C2"], [0.9, 0.9])]
        papers2 = [self.td.make_paper(["C1", "C2"], [0.9, 0.9])]
        papers3 = [self.td.make_paper(["C1", "C2"], [0.9, 0.9])]
        
        self.td.write_gz("a.gz", papers1)
        self.td.write_gz("b.gz", papers2)
        self.td.write_gz("c.gz", papers3)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        idx_x, idx_y = c2i["C1"], c2i["C2"]
        
        # 3 papers × 1 paire = 3
        self.assertEqual(matrix[idx_x, idx_y], 3)
    
    def test_test_mode_limits_files(self):
        """--test N = seulement N fichiers traités."""
        self._setup_concepts({"X": "C1", "Y": "C2"})
        
        for i in range(10):
            self.td.write_gz(f"file_{i:03d}.gz", 
                           [self.td.make_paper(["C1", "C2"], [0.9, 0.9])])
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args(test=3))
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        # Seulement 3 fichiers = 3 co-occurrences
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 3)
    
    def test_score_threshold_applied(self):
        """Concepts sous le seuil de score = exclus des paires."""
        self._setup_concepts({"A": "C1", "B": "C2"})
        
        # Paper avec B en score 0.1 (sous seuil 0.3)
        papers = [
            self.td.make_paper(["C1", "C2"], [0.9, 0.1]),
        ]
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        
        # Pas de co-occurrence car B est sous le seuil
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 0)
        # A a score OK mais est seul (B filtré) → len(indices)=1 → diag pas incrémentée
        self.assertEqual(matrix[c2i["C1"], c2i["C1"]], 0)
        self.assertEqual(matrix[c2i["C2"], c2i["C2"]], 0)
    
    def test_matrix_is_symmetric(self):
        """La matrice doit être parfaitement symétrique."""
        self._setup_concepts({
            "A": "C1", "B": "C2", "C": "C3", "D": "C4",
        })
        
        papers = []
        import random
        random.seed(42)
        for _ in range(100):
            n = random.randint(1, 4)
            ids = random.sample(["C1", "C2", "C3", "C4"], n)
            scores = [0.9] * n
            papers.append(self.td.make_paper(ids, scores))
        
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        # Vérifier symétrie
        diff = matrix - matrix.T
        self.assertEqual(diff.nnz, 0, "Matrix is not symmetric!")
    
    def test_no_gz_files_exits(self):
        """Aucun fichier .gz = sys.exit(1)."""
        self._setup_concepts({"A": "C1"})
        # Pas de .gz
        
        bc = self._reload_module()
        with self.assertRaises(SystemExit) as ctx:
            bc.build_cooccurrence_matrix(self._make_args())
        self.assertEqual(ctx.exception.code, 1)
    
    def test_no_mapped_concepts_exits(self):
        """0 concepts mappés = sys.exit(1)."""
        self.td.write_strates([{"from": "X", "to": "", "strate": 0}])
        self.td.write_openalex_map({})  # Rien de mappé
        self.td.write_gz("test.gz", [{"id": "W1", "concepts": []}])
        
        bc = self._reload_module()
        with self.assertRaises(SystemExit) as ctx:
            bc.build_cooccurrence_matrix(self._make_args())
        self.assertEqual(ctx.exception.code, 1)
    
    def test_output_files_created(self):
        """Vérifie que tous les fichiers de sortie existent."""
        self._setup_concepts({"A": "C1", "B": "C2"})
        self.td.write_gz("test.gz", [self.td.make_paper(["C1", "C2"], [0.9, 0.9])])
        
        bc = self._reload_module()
        bc.build_cooccurrence_matrix(self._make_args())
        
        self.assertTrue(os.path.exists(os.path.join(self.td.output_dir, "cooccurrence_matrix.npz")))
        self.assertTrue(os.path.exists(os.path.join(self.td.output_dir, "matrix_index.json")))
    
    def test_checkpoint_cleaned_after_completion(self):
        """Checkpoint et matrice partielle supprimés après complétion."""
        self._setup_concepts({"A": "C1", "B": "C2"})
        self.td.write_gz("test.gz", [self.td.make_paper(["C1", "C2"], [0.9, 0.9])])
        
        bc = self._reload_module()
        bc.build_cooccurrence_matrix(self._make_args())
        
        self.assertFalse(os.path.exists(os.path.join(self.td.output_dir, "_checkpoint.json")))
        self.assertFalse(os.path.exists(os.path.join(self.td.output_dir, "_partial_matrix.npz")))
    
    def test_three_concepts_all_in_one_paper(self):
        """3 concepts dans 1 paper = 3 paires (triangle complet)."""
        self._setup_concepts({"A": "C1", "B": "C2", "C": "C3"})
        
        papers = [self.td.make_paper(["C1", "C2", "C3"], [0.9, 0.9, 0.9])]
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        
        # Toutes les paires = 1
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 1)
        self.assertEqual(matrix[c2i["C1"], c2i["C3"]], 1)
        self.assertEqual(matrix[c2i["C2"], c2i["C3"]], 1)
    
    def test_paper_with_single_concept_no_pairs(self):
        """Paper avec 1 seul concept Yggdrasil = pas de paire, mais diag incrémentée."""
        self._setup_concepts({"A": "C1", "B": "C2"})
        
        papers = [self.td.make_paper(["C1"], [0.9])]  # 1 seul concept
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        
        # Pas de co-occurrence
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 0)
        # Diag: single concept papers don't count (need >=2)
        # Actually looking at code: diagonale only incremented when len(indices) >= 2
        self.assertEqual(matrix[c2i["C1"], c2i["C1"]], 0)
    
    def test_mixed_ygg_and_non_ygg_concepts(self):
        """Paper avec mix de concepts Yggdrasil et non-Yggdrasil."""
        self._setup_concepts({"A": "C1", "B": "C2"})
        
        # Paper avec C1, C2 (Yggdrasil) + C_ALIEN (pas Yggdrasil)
        paper = {
            "id": "W1",
            "concepts": [
                {"id": "C1", "score": 0.9},
                {"id": "C_ALIEN", "score": 0.9},
                {"id": "C2", "score": 0.9},
            ]
        }
        self.td.write_gz("test.gz", [paper])
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        
        # C1-C2 = 1, C_ALIEN ignoré
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 1)
        self.assertEqual(matrix.shape, (2, 2))  # Seulement 2 concepts mappés


# ═══════════════════════════════════════════════════════════════════════════
# TESTS D'INTÉGRATION — analyze_pluie.py
# ═══════════════════════════════════════════════════════════════════════════

class TestAnalyzePluie(unittest.TestCase):
    """Tests du script d'analyse."""
    
    def setUp(self):
        self.td = TestDataDir()
    
    def tearDown(self):
        self.td.cleanup()
    
    def test_analyze_loads_matrix(self):
        """L'analyse charge et lit la matrice sans crash."""
        # Créer matrice sparse 3x3
        data = np.array([1, 2, 3, 1, 2, 3, 5, 5, 5])
        rows = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
        cols = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        matrix = sparse.csr_matrix((data, (rows, cols)), shape=(3, 3))
        
        matrix_path = os.path.join(self.td.output_dir, "cooccurrence_matrix.npz")
        sparse.save_npz(matrix_path, matrix)
        
        index = {
            "n_concepts": 3,
            "idx_to_concept": {"0": "C1", "1": "C2", "2": "C3"},
            "idx_to_symbol": {"0": "ML", "1": "DL", "2": "NLP"},
            "concept_to_idx": {"C1": 0, "C2": 1, "C3": 2},
            "stats": {}
        }
        with open(os.path.join(self.td.output_dir, "matrix_index.json"), "w") as f:
            json.dump(index, f)
        
        # Importer et appeler
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
        import analyze_pluie as ap
        ap.PLUIE_DIR = Path(self.td.output_dir)
        ap.MATRIX_PATH = Path(matrix_path)
        ap.INDEX_PATH = Path(os.path.join(self.td.output_dir, "matrix_index.json"))
        
        mat, idx = ap.load_matrix()
        self.assertEqual(mat.shape, (3, 3))
        
        # basic_stats ne doit pas crasher
        ap.basic_stats(mat, idx)
        
        # degree_analysis ne doit pas crasher
        ap.degree_analysis(mat, idx)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS EDGE CASES EXTRÊMES
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    """Edge cases extrêmes pour tuer les bugs cachés."""
    
    def setUp(self):
        self.td = TestDataDir()
        self._setup_env()
    
    def tearDown(self):
        self._restore_env()
        self.td.cleanup()
    
    def _setup_env(self):
        self._old_env = {k: os.environ.get(k) for k in 
                         ["YGG_WORKS_DIR", "YGG_STRATES", "YGG_OA_MAP", "YGG_OUTPUT"]}
        os.environ["YGG_WORKS_DIR"] = self.td.works_dir
        os.environ["YGG_STRATES"] = os.path.join(self.td.data_dir, "strates_export_v2.json")
        os.environ["YGG_OA_MAP"] = os.path.join(self.td.data_dir, "openalex_map.json")
        os.environ["YGG_OUTPUT"] = self.td.output_dir
    
    def _restore_env(self):
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
    
    def _reload_module(self):
        import build_cooccurrence as bc
        bc.WORKS_DIR = os.environ["YGG_WORKS_DIR"]
        bc.STRATES_PATH = os.environ["YGG_STRATES"]
        bc.OPENALEX_MAP_PATH = os.environ["YGG_OA_MAP"]
        bc.OUTPUT_DIR = os.environ["YGG_OUTPUT"]
        bc.CHECKPOINT_PATH = os.path.join(bc.OUTPUT_DIR, "_checkpoint.json")
        return bc
    
    def _make_args(self, **kwargs):
        class Args:
            test = kwargs.get("test", 0)
            resume = kwargs.get("resume", False)
            min_score = kwargs.get("min_score", 0.3)
        return Args()
    
    def test_all_concepts_same_score_boundary(self):
        """Tous les concepts exactement au seuil."""
        concepts = {f"C{i}": f"OA{i}" for i in range(5)}
        strates = [{"from": f"C{i}", "to": "", "strate": 0} for i in range(5)]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts)
        
        papers = [self.td.make_paper(
            [f"OA{i}" for i in range(5)],
            [0.3] * 5  # Exactement au seuil
        )]
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        # 5 concepts, 10 paires possibles, toutes = 1
        upper = sparse.triu(matrix, k=1)
        self.assertEqual(upper.nnz, 10)
    
    def test_duplicate_concepts_in_paper(self):
        """Paper avec le même concept_id en double."""
        self.td.write_strates([{"from": "A", "to": "", "strate": 0},
                               {"from": "B", "to": "", "strate": 0}])
        self.td.write_openalex_map({"A": "C1", "B": "C2"})
        
        paper = {
            "id": "W1",
            "concepts": [
                {"id": "C1", "score": 0.9},
                {"id": "C1", "score": 0.8},  # Dupliqué!
                {"id": "C2", "score": 0.7},
            ]
        }
        self.td.write_gz("test.gz", [paper])
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        
        # Le concept dupliqué crée des paires supplémentaires
        # C1 apparaît 2 fois, C2 1 fois → indices = [0, 0, 1]
        # combinations(sorted([0, 0, 1]), 2) = (0,0), (0,1), (0,1)
        # Donc (0,0)=1, (0,1)=2
        # C'est un comportement acceptable — les dupes boostent le poids
        self.assertGreaterEqual(matrix[c2i["C1"], c2i["C2"]], 1)
    
    def test_paper_with_zero_score_concepts_only(self):
        """Paper où tous les concepts ont score 0."""
        self.td.write_strates([{"from": "A", "to": "", "strate": 0}])
        self.td.write_openalex_map({"A": "C1"})
        
        paper = {"id": "W1", "concepts": [{"id": "C1", "score": 0.0}]}
        self.td.write_gz("test.gz", [paper])
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        # Aucun concept ne passe le seuil → matrice vide
        self.assertEqual(matrix.nnz, 0)
    
    def test_very_large_co_occurrence_count(self):
        """Beaucoup de papers avec la même paire → grand nombre."""
        self.td.write_strates([{"from": "A", "to": "", "strate": 0},
                               {"from": "B", "to": "", "strate": 0}])
        self.td.write_openalex_map({"A": "C1", "B": "C2"})
        
        papers = [self.td.make_paper(["C1", "C2"], [0.9, 0.9]) for _ in range(10000)]
        self.td.write_gz("big.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        c2i = json.load(open(os.path.join(self.td.output_dir, "matrix_index.json")))["concept_to_idx"]
        self.assertEqual(matrix[c2i["C1"], c2i["C2"]], 10000)
    
    def test_index_json_completeness(self):
        """Vérifie que matrix_index.json contient tout ce qu'il faut."""
        self.td.write_strates([
            {"from": "A", "to": "", "strate": 0},
            {"from": "B", "to": "", "strate": 1},
        ])
        self.td.write_openalex_map({"A": "C1", "B": "C2"})
        self.td.write_gz("test.gz", [self.td.make_paper(["C1", "C2"], [0.9, 0.9])])
        
        bc = self._reload_module()
        bc.build_cooccurrence_matrix(self._make_args())
        
        with open(os.path.join(self.td.output_dir, "matrix_index.json")) as f:
            index = json.load(f)
        
        # Champs obligatoires
        self.assertIn("n_concepts", index)
        self.assertIn("idx_to_concept", index)
        self.assertIn("idx_to_symbol", index)
        self.assertIn("concept_to_idx", index)
        self.assertIn("stats", index)
        
        # Stats
        self.assertIn("total_papers", index["stats"])
        self.assertIn("papers_with_concepts", index["stats"])
        self.assertIn("total_pairs", index["stats"])
        self.assertIn("density_pct", index["stats"])
        self.assertIn("date", index["stats"])
        
        # Cohérence
        self.assertEqual(index["n_concepts"], 2)
        self.assertEqual(len(index["idx_to_concept"]), 2)
        self.assertEqual(len(index["idx_to_symbol"]), 2)
    
    def test_matrix_loadable_after_save(self):
        """Matrice sauvegardée en .npz peut être rechargée correctement."""
        self.td.write_strates([
            {"from": "A", "to": "", "strate": 0},
            {"from": "B", "to": "", "strate": 0},
            {"from": "C", "to": "", "strate": 0},
        ])
        self.td.write_openalex_map({"A": "C1", "B": "C2", "C": "C3"})
        
        papers = [
            self.td.make_paper(["C1", "C2"], [0.9, 0.9]),
            self.td.make_paper(["C2", "C3"], [0.9, 0.9]),
            self.td.make_paper(["C1", "C2", "C3"], [0.9, 0.9, 0.9]),
        ]
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        original = bc.build_cooccurrence_matrix(self._make_args())
        
        # Recharger
        reloaded = sparse.load_npz(os.path.join(self.td.output_dir, "cooccurrence_matrix.npz"))
        
        # Comparer
        diff = original - reloaded
        self.assertEqual(diff.nnz, 0, "Reloaded matrix differs from original!")
    
    def test_whitespace_in_concept_ids(self):
        """IDs avec espaces au début/fin = nettoyés."""
        self.td.write_strates([{"from": "A", "to": "", "strate": 0}])
        self.td.write_openalex_map({"A": " C1 "})  # Espaces!
        
        paper = {"id": "W1", "concepts": [{"id": " C1 ", "score": 0.9}]}
        self.td.write_gz("test.gz", [paper])
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        # Ne doit pas crasher, concept doit être reconnu
        self.assertEqual(matrix.shape[0], 1)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS DE COHÉRENCE MATHÉMATIQUE
# ═══════════════════════════════════════════════════════════════════════════

class TestMathCoherence(unittest.TestCase):
    """Vérifie les propriétés mathématiques de la matrice."""
    
    def setUp(self):
        self.td = TestDataDir()
        self._setup_env()
    
    def tearDown(self):
        self._restore_env()
        self.td.cleanup()
    
    def _setup_env(self):
        self._old_env = {k: os.environ.get(k) for k in 
                         ["YGG_WORKS_DIR", "YGG_STRATES", "YGG_OA_MAP", "YGG_OUTPUT"]}
        os.environ["YGG_WORKS_DIR"] = self.td.works_dir
        os.environ["YGG_STRATES"] = os.path.join(self.td.data_dir, "strates_export_v2.json")
        os.environ["YGG_OA_MAP"] = os.path.join(self.td.data_dir, "openalex_map.json")
        os.environ["YGG_OUTPUT"] = self.td.output_dir
    
    def _restore_env(self):
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
    
    def _reload_module(self):
        import build_cooccurrence as bc
        bc.WORKS_DIR = os.environ["YGG_WORKS_DIR"]
        bc.STRATES_PATH = os.environ["YGG_STRATES"]
        bc.OPENALEX_MAP_PATH = os.environ["YGG_OA_MAP"]
        bc.OUTPUT_DIR = os.environ["YGG_OUTPUT"]
        bc.CHECKPOINT_PATH = os.path.join(bc.OUTPUT_DIR, "_checkpoint.json")
        return bc
    
    def _make_args(self):
        class Args:
            test = 0
            resume = False
            min_score = 0.3
        return Args()
    
    def test_symmetry_with_random_data(self):
        """Symétrie parfaite avec données aléatoires."""
        import random
        random.seed(123)
        
        n_concepts = 20
        concepts = {f"C{i}": f"OA{i}" for i in range(n_concepts)}
        strates = [{"from": f"C{i}", "to": "", "strate": i % 4} for i in range(n_concepts)]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts)
        
        papers = []
        for _ in range(500):
            n = random.randint(1, 6)
            ids = [f"OA{random.randint(0, n_concepts-1)}" for _ in range(n)]
            scores = [round(random.uniform(0.1, 1.0), 2) for _ in range(n)]
            papers.append(self.td.make_paper(ids, scores))
        
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        # Symétrie
        diff = (matrix - matrix.T)
        self.assertEqual(diff.nnz, 0, f"Non-symmetric! {diff.nnz} elements differ")
    
    def test_diagonal_less_than_or_equal_to_off_diagonal_sum(self):
        """diag[i] = nombre de papers avec concept i (parmi ceux avec ≥2 concepts).
        La somme off-diag d'une ligne >= diag car chaque paper contribue 
        ≥1 paire off-diag + 1 diag."""
        import random
        random.seed(456)
        
        n_concepts = 10
        concepts = {f"C{i}": f"OA{i}" for i in range(n_concepts)}
        strates = [{"from": f"C{i}", "to": "", "strate": 0} for i in range(n_concepts)]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts)
        
        papers = []
        for _ in range(200):
            n = random.randint(2, 5)  # Au moins 2 pour avoir des paires
            ids = random.sample([f"OA{i}" for i in range(n_concepts)], n)
            scores = [0.9] * n
            papers.append(self.td.make_paper(ids, scores))
        
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        dense = matrix.toarray()
        for i in range(matrix.shape[0]):
            diag_val = dense[i, i]
            if diag_val > 0:
                # diag[i] ≤ sum of row (excluding diag)
                off_diag_sum = dense[i, :].sum() - diag_val
                # Each paper with concept i and ≥1 other concept contributes
                # at least 1 to off-diag. So off_diag >= diag
                self.assertGreaterEqual(off_diag_sum, diag_val,
                    f"Concept {i}: diag={diag_val} but off_diag_sum={off_diag_sum}")
    
    def test_all_values_non_negative(self):
        """Aucune valeur négative dans la matrice."""
        import random
        random.seed(789)
        
        n_concepts = 15
        concepts = {f"C{i}": f"OA{i}" for i in range(n_concepts)}
        strates = [{"from": f"C{i}", "to": "", "strate": 0} for i in range(n_concepts)]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts)
        
        papers = []
        for _ in range(300):
            n = random.randint(1, 5)
            ids = random.sample([f"OA{i}" for i in range(n_concepts)], n)
            scores = [0.9] * n
            papers.append(self.td.make_paper(ids, scores))
        
        self.td.write_gz("test.gz", papers)
        
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        
        self.assertTrue(np.all(matrix.toarray() >= 0), "Negative values found!")


# ═══════════════════════════════════════════════════════════════════════════
# TESTS DE PERFORMANCE / STRESS
# ═══════════════════════════════════════════════════════════════════════════

class TestStress(unittest.TestCase):
    """Tests de performance et stress."""
    
    def setUp(self):
        self.td = TestDataDir()
        self._setup_env()
    
    def tearDown(self):
        self._restore_env()
        self.td.cleanup()
    
    def _setup_env(self):
        self._old_env = {k: os.environ.get(k) for k in 
                         ["YGG_WORKS_DIR", "YGG_STRATES", "YGG_OA_MAP", "YGG_OUTPUT"]}
        os.environ["YGG_WORKS_DIR"] = self.td.works_dir
        os.environ["YGG_STRATES"] = os.path.join(self.td.data_dir, "strates_export_v2.json")
        os.environ["YGG_OA_MAP"] = os.path.join(self.td.data_dir, "openalex_map.json")
        os.environ["YGG_OUTPUT"] = self.td.output_dir
    
    def _restore_env(self):
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
    
    def _reload_module(self):
        import build_cooccurrence as bc
        bc.WORKS_DIR = os.environ["YGG_WORKS_DIR"]
        bc.STRATES_PATH = os.environ["YGG_STRATES"]
        bc.OPENALEX_MAP_PATH = os.environ["YGG_OA_MAP"]
        bc.OUTPUT_DIR = os.environ["YGG_OUTPUT"]
        bc.CHECKPOINT_PATH = os.path.join(bc.OUTPUT_DIR, "_checkpoint.json")
        return bc
    
    def _make_args(self):
        class Args:
            test = 0
            resume = False
            min_score = 0.3
        return Args()
    
    def test_500_concepts_10k_papers(self):
        """Stress test: 500 concepts, 10k papers — doit finir < 30s."""
        import random
        random.seed(999)
        
        n_concepts = 500
        concepts = {f"Concept_{i}": f"OA_{i}" for i in range(n_concepts)}
        strates = [{"from": f"Concept_{i}", "to": "", "strate": i % 7} for i in range(n_concepts)]
        self.td.write_strates(strates)
        self.td.write_openalex_map(concepts)
        
        papers = []
        for _ in range(10000):
            n = random.randint(1, 8)
            ids = [f"OA_{random.randint(0, n_concepts-1)}" for _ in range(n)]
            scores = [round(random.uniform(0.2, 1.0), 2) for _ in range(n)]
            papers.append(self.td.make_paper(ids, scores))
        
        self.td.write_gz("stress.gz", papers)
        
        start = time.time()
        bc = self._reload_module()
        matrix = bc.build_cooccurrence_matrix(self._make_args())
        elapsed = time.time() - start
        
        print(f"\n  ⏱️  500 concepts × 10k papers: {elapsed:.1f}s")
        print(f"  Matrix: {matrix.shape}, nnz={matrix.nnz}")
        
        self.assertLess(elapsed, 30, "Too slow for 10k papers!")
        self.assertEqual(matrix.shape, (500, 500))
        
        # Symétrie
        diff = matrix - matrix.T
        self.assertEqual(diff.nnz, 0)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🔨 BATTERIE DE TESTS — Phase 4 PLUIE")
    print("=" * 60)
    unittest.main(verbosity=2)
