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
- [x] Phase 3 — `ml_model.py` : LightGBM (features surface, pièces, terrain, type, lat/lon, encodage cible commune/département, période), validation temporelle train ≤ 2024 / test 2025 (erreur médiane ≈ 19,3 %), SHAP TreeExplainer groupé par facteur. **Gate** : sur 300 mêmes ventes 2025, ML 21,7 % vs comparables 18,1 % → **non promu** (visible, poids 0). `GET/POST /api/models/ml[/train]`. Ré-entraînement possible depuis l'écran Données.
- [x] Poids ajustables (`blend.py`) : curseurs comparables / hédonique / marché / ML (désactivé si non promu), réglage global `GET/PUT /api/settings/weights` (défaut 50/30/20/0), `GET /api/properties/{id}/final`, calcul miroir côté client pour réactivité, section dans le PDF. `market_estimate` = prix/m² médian du meilleur rayon × surface + ajustements.
- [x] Signal « Bon moment pour vendre ? » (`GET /api/properties/{id}/market-signal`) : tendance 12 mois (40), volume vs 2 ans (30), liquidité (30) → score/verdict favorable/neutre/attentiste, calculé au dernier point DVF.
- [x] Annonce IA (`listing.py`, Claude Sonnet 4.6 via EMERGENT_LLM_KEY) : styles Sobre/Chaleureux/Premium/Familial, faits + précisions vendeur, option fourchette, garde-fou strict (aucune invention, état repris tel quel, pas d'adjectif sur le quartier). CRUD `/api/properties/{id}/listings` (soft delete), écran `property/[id]/listing` avec copie presse-papiers.
- [x] Phase 5 — IA Photo (retouche uniquement) : `storage.py` (Emergent Object Storage, chemins `estimo/properties/{pid}/{uuid}.jpg`), `photos.py` (normalisation JPEG 1600 px + EXIF strip, retouche Gemini `gemini-3.1-flash-image-preview` avec interdiction d'ajouter des éléments). Endpoints `POST/GET /api/properties/{id}/photos`, `POST /api/photos/{id}/retouch`, `DELETE /api/photos/{id}` (soft), `GET /api/files/{path}`. Écran `property/[id]/photos` : galerie/appareil photo avec flux de permissions (réglages si bloqué), bascule original/retouchée, badge « Visuel retouché par IA · non contractuel ». Permissions déclarées dans app.json.

- [x] Phase 6 — Dossier de vente (`dossier.py`) : checklist dynamique (19 éléments : obligatoires, conditionnels, copropriété, recommandés) adaptée au type, à l'année de construction, au terrain et au DPE ; import photo/galerie/fichier PDF → Object Storage (`estimo/documents/{pid}/…`) ; OCR Gemini 3 Flash (`gemini-3-flash-preview`, FileContentWithMimeType) → champs structurés (type, émetteur, dates, champs clés, alertes) ; validation obligatoire par le vendeur (champs éditables) ; expiration calculée par type (DPE 10 ans, élec/gaz 3 ans, ERP 6 mois…) ; statuts manquant / à vérifier / validé / expiré / non applicable ; progression. Endpoints `GET /api/properties/{id}/dossier`, `PUT …/dossier/{item_key}`, `POST /api/properties/{id}/documents`, `GET/PUT(validate)/POST(reocr)/DELETE /api/documents/{id}`. Écrans `property/[id]/dossier` et `property/[id]/document/[docId]`.

## Backlog priorisé
- P2 Home staging IA (mobilier virtuel dans pièce vide, styles) — différé sur demande utilisateur
- P2 Photos et dossier dans le rapport PDF · export du dossier de vente (ZIP/PDF) pour le notaire
- P2 Rappels d'expiration des diagnostics
- P2 Améliorer le ML pour passer la gate · ajout de départements / mise à jour trimestrielle DVF
