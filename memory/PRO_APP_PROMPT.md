# Achète ma maison PRO — prompt de démarrage (à coller dans un NOUVEAU projet Emergent)

## Comment procéder (recommandation)
1. Pousser ce projet sur GitHub (bouton « Save to GitHub » dans Emergent) pour garder le moteur d'estimation (DVF, hédonique, LightGBM), le dossier environnement, les documents/OCR et les pages web.
2. Créer un **nouveau projet Emergent** (type « Expo mobile + FastAPI ») et, dans le premier message, coller le prompt ci-dessous en remplaçant `<URL_GITHUB>` par l'adresse du dépôt.
3. Laisser l'agent poser ses dernières questions (nom de la marque PRO, identité visuelle).

---

## PROMPT

Tu vas créer **« Achète ma maison PRO »**, une application mobile (iOS/Android, Expo + FastAPI + MongoDB) destinée aux **professionnels de l'immobilier** (agents, mandataires, négociateurs). Elle est dérivée de l'application grand public « Achète ma maison » dont le code source est ici : `<URL_GITHUB>`. Commence par cloner ce dépôt dans le projet et réutilise tel quel : moteur d'estimation (DVF + hédonique + LightGBM), dossier environnement, génération d'annonce IA, retouche photo IA, checklist documents + OCR, génération PDF. Réponds toujours en français.

### 1. Ce qui change par rapport à l'app grand public
- **Public** : professionnels uniquement. Suppression du mode « vendeur particulier », du Pack 49 € à l'unité et du parcours en 3 étapes (Estimation / Mise en vente / Vendu).
- **Adhésion** : **abonnement 79 € TTC / mois par agent** via RevenueCat (identifiant produit `pro_monthly_79`), avec **essai gratuit 14 jours**, résiliable à tout moment. Variante annuelle `pro_yearly_790` (790 €/an, soit 2 mois offerts). Sur le web, Stripe Billing (abonnement). Pas d'achat à l'acte.
- **Inscription** : e-mail + mot de passe, puis fiche professionnelle obligatoire (nom de l'agence, numéro de carte T ou attestation de collaborateur, téléphone, logo). Un **compte agence** peut inviter plusieurs agents (rôles : responsable / agent) ; les biens et clients sont partagés au sein de l'agence.
- **Structure de l'app (onglets)** : Accueil (agenda des visites du jour) · Biens (mandats) · Clients (acquéreurs & vendeurs) · Enregistreur · Compte.
- **Modèle de données** : `agencies`, `agents`, `properties` (mandats, avec estimation réutilisée), `contacts` (acquéreur/vendeur : budget, critères, statut), `visits` (bien + contact + date + enregistrement), `recordings`, `transcripts`, `visit_summaries`, `tasks`.

### 2. Fonction phare : l'enregistreur de visite (pipeline complet)
**Côté mobile**
1. Bouton « Démarrer la visite » : choix du bien et du client, puis **consentement explicite** : l'app affiche un écran « Informer le client que la visite est enregistrée » avec une case à cocher obligatoire (RGPD / article 226-1 Code pénal) ; la date/heure du consentement est stockée avec l'enregistrement.
2. **Capture audio** avec `expo-audio`, en **segments de 30 s** (fichiers m4a/AAC 32 kbps mono) pour tolérer les coupures. Minuteur visible, pause/reprise, indicateur de niveau sonore. Enregistrement en arrière-plan / écran verrouillé (nécessite un build natif, à signaler).
3. **Stockage local hors ligne** : segments écrits dans `FileSystem.documentDirectory/recordings/<visit_id>/`, index des segments dans AsyncStorage (statut : local / envoyé / échec).
4. **File d'envoi** : dès que le réseau revient (`@react-native-community/netinfo`), envoi des segments non transmis en HTTPS via `uploadForm` (jamais `FormData` avec `uri` brute), reprise automatique, barre de progression. Les segments sont supprimés du téléphone après confirmation serveur.

**Côté serveur (FastAPI)**
5. `POST /api/visits/{id}/segments` : authentification de l'agent (JWT), contrôle de taille/type, stockage de l'audio dans **Emergent Object Storage** (chiffré au repos, hébergement UE), enregistrement du segment en base.
6. `POST /api/visits/{id}/finish` : empile une tâche de traitement en arrière-plan (file de jobs dans Mongo + worker asyncio, avec reprise si redémarrage) ; l'app interroge `GET /api/visits/{id}/status` (progression par étapes).
7. **Transcription** : OpenAI Speech-to-Text via la clé Emergent (modèle de transcription le plus récent disponible dans le playbook), segment par segment, en français, avec horodatage ; concaténation en un transcript unique. Pas de Deepgram : la **séparation des voix** (Agent / Client) est faite par Claude à l'étape suivante, à partir du contexte (l'agent présente, le client questionne), avec un indicateur de confiance par réplique et correction manuelle possible dans l'app.
8. **Analyse** avec **Claude (dernière version Sonnet disponible)** via la clé Emergent, en **sortie JSON stricte** validée par Pydantic :
   ```json
   {
     "summary": "résumé de la visite en 5 à 8 phrases",
     "client_profile": {"budget_min": 0, "budget_max": 0, "financing": "comptant|prêt|à définir", "timeline": "…", "criteria": ["…"], "must_have": ["…"], "deal_breakers": ["…"]},
     "sentiment": "très intéressé|intéressé|mitigé|pas intéressé",
     "objections": [{"topic": "…", "detail": "…", "suggested_answer": "…"}],
     "property_feedback": {"liked": ["…"], "disliked": ["…"], "price_opinion": "…"},
     "next_actions": [{"title": "…", "due_in_days": 0, "type": "rappel|envoi_document|contre_visite|offre|autre"}],
     "quotes": [{"speaker": "client|agent", "text": "…", "t": 0}]
   }
   ```
9. Mise à jour automatique du **CRM interne** : fiche client (budget, critères, statut) et fiche bien (retours de visite agrégés, objections récurrentes sur le prix → suggestion de repositionnement avec le moteur d'estimation).
10. **Notification** à l'agent quand le résumé est prêt (Emergent managed push notifications) + e-mail récapitulatif optionnel (Emergent Resend).

**Retour dans l'app**
11. Écran « Compte rendu de visite » : résumé, profil client, objections avec réponses suggérées, tâches cochables (créées dans l'onglet Agenda), transcription complète horodatée avec lecteur audio synchronisé (tap sur une phrase → lecture à cet instant).
12. L'agent **corrige** (édition inline de chaque champ), **valide** (verrouille la version), et **partage** : PDF « Compte rendu de visite » au vendeur (version expurgée : sans budget ni données personnelles de l'acquéreur) ou au client (résumé + prochaines étapes), par e-mail ou lien.

### 3. Exigences non négociables
- Sécurité : chaque ressource filtrée par `agency_id` ; audio accessible uniquement via URL signée courte durée ; suppression définitive (audio + transcript) sur demande, et **purge automatique de l'audio brut après 90 jours** (paramétrable par agence), le texte étant conservé.
- RGPD : page « Confidentialité » détaillant l'enregistrement, mention dans les CGU, export des données d'un client en un clic.
- Hors ligne : l'enregistrement, la consultation des biens/clients et la saisie de notes fonctionnent sans réseau ; synchronisation à la reconnexion.
- Qualité : tests automatisés du pipeline (segment → transcript → JSON validé → CRM) avec un fichier audio de démonstration ; compte de test `demo-pro@achetemamaison.fr` avec abonnement actif pour les revues Apple/Google.
- Fonctionnalités à signaler comme **non testables dans Expo Go** (build natif requis) : enregistrement en arrière-plan, notifications push.

### 4. Ordre de réalisation
1. Clone + nettoyage du parcours particulier, nouveau modèle de données agence/agents, abonnement RevenueCat/Stripe avec essai.
2. Enregistreur (capture segmentée, stockage local, file d'envoi) + stockage objet serveur.
3. Pipeline transcription → Claude → JSON → CRM, avec écran de progression.
4. Compte rendu, corrections, partage PDF, notifications.
5. Onglets Biens/Clients/Agenda, réutilisation estimation + environnement + annonce IA pour les mandats.

Décisions déjà prises : 79 €/mois (essai 14 jours), pas de Deepgram, conservation audio 90 jours. Avant de coder, pose-moi uniquement les questions indispensables restantes (nom définitif, identité visuelle).
