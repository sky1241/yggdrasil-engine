# 🛒 LISTE DE COURSE — Session 21 fév matin
# Sky × Claude — Versoix
# Pour communication entre cousins Claude

## ✅ FAIT

- [x] Clone repo + lecture SOL.md
- [x] Lecture LIANES.md (théorie escaliers de secours)
- [x] Calcul centroïdes 9 continents depuis strates_export_v2.json (21,249 concepts S0)
- [x] Matrice distances inter-centroïdes (36 paires)
- [x] Détection lianes géographiques: 4,548 trouvées (ratio spectral < 0.8, pondéré portée)
- [x] Analyse par paire: bruit BIO↔TERRE filtré naturellement (portée 0.208)
- [x] Top 50 escaliers de secours avec scores
- [x] Validation croisée lianes historiques: 2/7 retrouvées spectralement (W(t), ζ)
- [x] DÉCOUVERTE: 2 types d'escaliers (géographique 🌿 vs passe-partout 🔑)
- [x] Explication POURQUOI exp/∫/Σ sont invisibles en spectral (collés centroïde Math)
- [x] Chargement 69 passe-partout depuis lianes_export.json
- [x] Export unifié (200 geo + 69 key) → data/escaliers_unified.json
- [x] Viz HTML interactive → viz/escaliers_spectraux.html
- [x] Scan nettoyage S0: 39 suspects par mots-clés
- [x] Triage manuel: 26 faux positifs, 13 vrais suspects identifiés
- [x] 1 bug mapping trouvé: Hagen-Poiseuille = "droit" au lieu de "fluides"
- [x] Scan works_count: 8 concepts < 100 papers (tous légitimes sauf le bug)
- [x] Distribution works_count par domaine (94 domaines)
- [x] DÉCISION: tri vivant/musée par Q1 domaine ("PIB par habitant")
- [x] Résultat: 15,556 vivants (75%) / 5,144 musée (25%)
- [x] DÉCISION: 3 cubes (vivant / musée / fusion)
- [x] INSIGHT: contradictions works_count vs mycelium = vrai signal
- [x] Prompt handoff V2 écrit → docs/PROMPT_ESCALIERS_V2.md
- [x] Commit git (5 fichiers, 12,574 lignes)

## ❌ PAS FAIT (pour le prochain Claude)

- [ ] Push git (token expiré, Sky doit renouveler)
- [ ] Ajouter works_count dans strates_export_v2.json (croiser avec mined_concepts.json)
- [ ] Implémenter Q1 par domaine dans le code de La Pluie v3
- [ ] Rewire les checkboxes C1/C2/C3 Fusion → vivant/musée/fusion
- [ ] Virer les 13 suspects de S0 C1:
      - Black hole information paradox → S3 C2
      - Homotopy hypothesis → S3 C2
      - Non-standard cosmology → S0 C2
      - Unparticle physics → S0 C2
      - Multiple chemical sensitivity → S0 C2
      - Group selection → S0 C2
      - International Linear Collider → S0 C2
      - Neocolonialism → S0 C2
      - Creative class → S0 C2
      - Bertrand paradox (economics) → S0 C2
      - Ridge push → S0 C2
      - Phylogenetic nomenclature → S0 C2
      - Superselection → S0 C2
- [ ] Fix bug: Hagen-Poiseuille flow domain "droit" → "fluides"
- [ ] Déplacer 8 C2 de S0 vers leur vraie strate
- [ ] Poincaré conjecture: C2 → C1 (résolu par Perelman 2003)
- [ ] Croiser flux Physarum (mycelium) × works_count (nœuds) → lister contradictions
- [ ] Identifier: concepts isolés, ponts cachés, vides fertiles (P4)
- [ ] Intégrer escaliers spectraux dans La Pluie v3 (layer toggle)
- [ ] Viz 3D routes escaliers entre strates
- [ ] Mettre à jour SOL.md avec les nouvelles décisions

## 🧠 DÉCISIONS PRISES (ne pas remettre en question)

1. S0 = sol solide, 99.90% propre — on construit dessus
2. Vivant = works_count >= Q1 de son domaine (pas seuil fixe)
3. 2 types d'escaliers: géographique (position spectrale) + passe-partout (multi-continent)
4. Les contradictions entre couches = le vrai signal
5. Cube 1 vivant / Cube 2 musée / Cube 3 fusion
6. Le mycelium Physarum fait déjà le tri vivant/mort sur les CONNEXIONS — le works_count le fait sur les NŒUDS — garder les deux
