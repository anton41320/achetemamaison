# Estimo — Copilote Immobilier IA (Phase 1)

## Problème d'origine
App mobile (Expo + FastAPI + MongoDB) accompagnant un vendeur de l'estimation à la vente. Livraison par phases ;
**Phase 1 = estimation robuste par comparables DVF**, transparente, toujours avec fourchette + niveau de confiance.

## Choix utilisateur
- Zone : départements 41 (Loir-et-Cher), 37 (Indre-et-Loire), 45 (Loiret) — DVF 2021–2025
- Pas d'auth (mono-utilisateur local) · Nom : **Estimo**
- Élargissement automatique 500 m → quartier (1,5 km) → commune → secteur (5 km) avec mention explicite
- Fondations Phase 2 : champs hédoniques optionnels stockés (floor, has_elevator, has_parking, has_outdoor, dpe), non exposés en UI

## Architecture
- `backend/dvf_ingest.py` : téléchargement geo-dvf (files.data.gouv.fr), nettoyage pandas (Vente, 1 seul logement/mutation, prix unique, bornes prix/m²), stockage `dvf_sales` + index 2dsphere. Ingestion auto au démarrage si base vide, ou `POST /api/dvf/ingest`. ~110 k ventes.
- `backend/estimator.py` : comparables pondérés (récence ½-vie 2 ans, distance, similarité surface), médiane pondérée du prix/m², ajustements transparents (état, année, terrain), score de confiance 0–100 (nb comparables 40, dispersion 30, récence 20, proximité 10), fourchette ±(max(12 %, 0,7×IQR relatif)) élargie si confiance faible, ≥ ±25 % si données insuffisantes. Back-test `GET /api/validation?n=`.
- `backend/server.py` : `/api/health`, `/api/geocode` (proxy BAN), `/api/dvf/status|ingest`, `/api/properties` CRUD (soft delete) + `/reestimate`, `/api/estimate/preview`, `/api/validation`.
- Frontend expo-router (stack) : `index` (Mes biens), `new` (wizard 3 étapes), `property/[id]` (résultat), `property/[id]/comparables`, `data` (statut DVF + validation).
- Env backend : `DVF_DEPARTMENTS`, `DVF_YEARS`, `BAN_URL`.

## Implémenté (2026-06)
- [x] Ingestion DVF 41/37/45 (2021–2025) + statut
- [x] Autocomplétion adresse BAN avec indication zone couverte
- [x] Estimation comparables : valeur, fourchette, prix/m², confiance détaillée, notes, ajustements, marché local 3 rayons, 30 comparables
- [x] Règle « jamais un prix seul » + bannière données insuffisantes
- [x] Historique des biens, ré-estimation, suppression (soft)
- [x] Validation baseline (back-test sur ventes réelles) : erreur médiane ≈ 17 %, couverture fourchette ≈ 65 %, confiance élevée ≈ 13 % / faible ≈ 30 %
- [x] Phase 2 — `hedonic.py` : régression log(prix) à effets fixes commune (shrinkage vers le département), validation temporelle (train ≤ 2024 / test 2025 : erreur médiane ≈ 19,8 %, R² log ≈ 0,6). Section « Pourquoi cette estimation ? » : facteurs +/- (localisation, surface, pièces, terrain, déclaratifs état/année) vs bien type, valeur hédonique côte à côte avec les comparables, indicateur convergent / écart modéré / divergent. La fourchette affichée reste celle des comparables (baseline gagnante). Entraînement auto au démarrage, `GET/POST /api/models/hedonic[/train]`.
- [x] Rapport PDF (`report.py`, reportlab) : `GET /api/properties/{id}/report.pdf` — synthèse, confiance, calcul, marché, facteurs hédoniques, 10 comparables ; partage natif via expo-sharing (ouverture directe sur web).
- [x] Tendance marché : `GET /api/properties/{id}/trend` — prix/m² médian par année (commune + rayon 1,5 km), variation première→dernière année, graphique barres/points.

## Backlog priorisé
- P1 Phase 3 : LightGBM + validation temporelle + SHAP (gate : ne remplace la baseline que s'il la bat sur 2025)
- P1 Pondération finale comparables / hédonique / marché avec poids ajustables (Phase 3)
- P2 Phase 4 : générateur d'annonce IA · P2 Phase 5 : IA photo · P2 Phase 6 : dossier juridique
- P2 Ajout de départements / mise à jour trimestrielle planifiée du DVF
