# Kit App Store — « Achètes ma maison »

Tout ce qu'il faut copier-coller dans App Store Connect (Distribution → version iOS). Les limites de caractères Apple sont indiquées ; chaque texte les respecte.

---

## 1. Captures d'écran (dossier `iphone-6.9/` et `ipad-13/`)

| Emplacement App Store Connect | Fichiers | Taille |
|---|---|---|
| iPhone — écran 6,9" (si l'emplacement est proposé) | `iphone-6.9/01-…07-*.png` | 1320 × 2868 px |
| iPhone — écran 6,5" (emplacement affiché par défaut dans App Store Connect) | `iphone-6.5/01-…07-*.png` | 1284 × 2778 px |
| iPad — écran 13" (obligatoire car l'app accepte l'iPad) | `ipad-13/01-…07-*.png` | 2064 × 2752 px |
| **Google Play** — captures téléphone (ratio 9:16 imposé) | `play-phone/01-…07-*.png` | 1080 × 1920 px |
| **Google Play** — image de présentation (obligatoire) | `play-feature-graphic-1024x500.png` | 1024 × 500 px |
| **Google Play** — icône | `play-icon-512.png` | 512 × 512 px |

Ordre conseillé (glisser-déposer dans cet ordre) :
1. `01-welcome` — Estimez, préparez, vendez
2. `03-property` — Une estimation fondée sur les ventes réelles
3. `04-comparables` — Comprenez chaque euro
4. `02-home` — Tous vos biens en un coup d'œil
5. `05-dossier` — Un dossier de vente prêt pour le notaire
6. `06-pack` — Outils IA : annonce, photos, documents
7. `07-photos` — Photos retouchées par l'IA

Astuce : si vous ne voulez pas gérer l'iPad, demandez-moi de passer l'app en « iPhone uniquement » (`supportsTablet: false`) avant le prochain build ; les captures iPad ne seront alors plus demandées.

---

## 2. Informations sur l'app (onglet « Informations sur l'app »)

**Nom** (30 car. max) — 17 car.
```
Achètes ma maison
```

**Sous-titre** (30 car. max) — 28 car.
```
Estimez et vendez votre bien
```

**Catégorie principale** : Finance
**Catégorie secondaire** : Style de vie

**Droits d'auteur**
```
© 2026 Achètes ma maison
```

**Classification par âge** : répondre « Non » à tout → **4+**

---

## 3. Version iOS (onglet de la version, langue : Français (France))

**Texte promotionnel** (170 car. max, modifiable sans nouvelle version) — 157 car.
```
Estimation gratuite fondée sur les ventes réelles DVF, dossier de vente guidé et outils IA (annonce, photos, documents) avec le Pack premium à 49 € par bien.
```

**Description** (4000 car. max) — ≈ 1 900 car.
```
Achètes ma maison accompagne les particuliers de l'estimation de leur logement jusqu'au rendez-vous chez le notaire.

UNE ESTIMATION QUE VOUS POUVEZ EXPLIQUER
• Fourchette de prix calculée à partir des ventes réelles publiées par l'État (base DVF), autour de chez vous et dans les communes de taille comparable.
• Niveau de confiance explicite : nombre de ventes retenues, homogénéité des prix, ancienneté du marché.
• « Pourquoi ce prix ? » : chaque critère (surface, pièces, terrain, état, équipements, localisation) est chiffré et commenté.
• Prix cible : positionnez votre prix de vente dans la fourchette et suivez le signal du marché.
• Rapport PDF partageable à votre agent, votre banque ou vos proches.

UN DOSSIER DE VENTE SANS OUBLI
• Checklist des diagnostics et documents adaptée à votre bien (maison ou appartement, année de construction, copropriété…).
• Rappels avant expiration des diagnostics (DPE, électricité, gaz, ERP…).
• Export « dossier notaire » : synthèse + pièces validées, en un seul PDF.

PACK PREMIUM — 49 € PAR BIEN, SANS ABONNEMENT
• Annonce rédigée par l'IA dans le style de votre choix, uniquement à partir de vos informations : rien n'est inventé.
• Retouche photo par l'IA : lumière, contraste et perspective améliorés, aucun élément ajouté ; l'original est toujours conservé et le visuel retouché porte la mention « non contractuel ».
• Lecture automatique de vos documents : type, dates, champs clés et alertes pré-remplis, que vous validez.
• PDF d'annonce premium prêt à diffuser.

VOS DONNÉES VOUS APPARTIENNENT
Compte personnel sécurisé, données rattachées à votre compte uniquement, suppression du compte possible à tout moment depuis l'application.

Couverture actuelle des estimations : Loir-et-Cher (41), Indre-et-Loire (37) et Loiret (45). D'autres départements arrivent.

Les estimations sont fournies à titre indicatif et ne constituent ni une expertise ni un avis de valeur au sens réglementaire.
```

**Mots-clés** (100 car. max, séparés par des virgules, sans espace) — 96 car.
```
estimation,immobilier,vendre,maison,appartement,prix,DVF,notaire,diagnostic,DPE,annonce,logement
```

**URL d'assistance** (obligatoire)
```
https://estimate-home.emergent.host/api/privacy
```

**URL marketing** (facultatif)
```
https://estimate-home.emergent.host/api/privacy
```

**URL de la politique de confidentialité** (obligatoire — section « Informations sur l'app »)
```
https://estimate-home.emergent.host/api/privacy
```
> Domaine déployé : `estimate-home.emergent.host`. Les pages légales sont servies par le serveur : `/api/privacy` (politique + support) et `/api/account/delete` (suppression de compte, exigée par Google Play → « URL de suppression de compte »).

**Nouveautés de cette version** (4000 car. max)
```
Première version publique :
• Estimation fondée sur les ventes réelles (DVF) avec niveau de confiance et explication critère par critère
• Prix cible et signal de marché
• Dossier de vente : checklist des diagnostics, rappels d'expiration, export notaire
• Pack premium (49 € par bien) : annonce IA, retouche photo IA, lecture automatique des documents, PDF premium
```

---

## 4. Informations sur l'examen (App Review)

**Compte de démonstration** (cochez « Connexion requise »)
```
Identifiant : delivered@resend.dev
Mot de passe : Estimo2026!
```

**Coordonnées** : votre prénom, nom, téléphone et e-mail.

**Notes pour l'examinateur**
```
Achètes ma maison aide un particulier à estimer puis préparer la vente de son logement en France.

Parcours à tester avec le compte de démonstration :
1. Accueil « Mes biens » : ouvrir un bien pour voir l'estimation, la fourchette et le niveau de confiance ; « Ventes comparables » liste les ventes DVF utilisées.
2. « Dossier de vente » : checklist des diagnostics ; un document peut être ajouté (photo ou PDF) puis validé manuellement.
3. « Pack premium » : présentation de l'offre à 49 € et aperçu (exemple réel avant/après de retouche, exemple d'annonce).

Les estimations reposent sur des données publiques ouvertes (DVF, data.gouv.fr) et sont fournies à titre indicatif.
La suppression du compte est disponible dans « Mon compte » → « Supprimer mon compte ».
```

> ⚠️ **Point de vigilance important — paiement du Pack premium.** Aujourd'hui, le Pack (contenu numérique consommé dans l'app : annonce IA, retouche, lecture de documents) est payé via **Stripe**. La règle 3.1.1 de l'App Store impose l'**achat intégré Apple (In-App Purchase)** pour ce type de contenu ; un paiement Stripe dans l'app iOS entraîne très probablement un **refus lors de l'examen**. Deux options : (a) basculer le Pack en achat intégré (RevenueCat géré par Emergent, produit non consommable « pack_premium_bien » à 49,99 € par exemple) — je peux l'implémenter ; (b) soumettre en l'état et prendre le risque d'un refus. Je recommande fortement (a) avant la soumission. Android/Google Play a une règle équivalente.

---

## 5. Confidentialité de l'app (questionnaire « App Privacy »)

Répondre « Oui, nous collectons des données ». Déclarer :

| Type de donnée | Utilisation | Liée à l'identité | Suivi (tracking) |
|---|---|---|---|
| Coordonnées → Adresse e-mail | Fonctionnalités de l'app, gestion du compte | Oui | Non |
| Localisation → Localisation approximative (adresse du bien saisie) | Fonctionnalités de l'app | Oui | Non |
| Contenu utilisateur → Photos ou vidéos | Fonctionnalités de l'app | Oui | Non |
| Contenu utilisateur → Autre contenu (documents, caractéristiques du bien) | Fonctionnalités de l'app | Oui | Non |
| Informations financières → Historique d'achats | Fonctionnalités de l'app | Oui | Non |
| Identifiants → ID utilisateur | Fonctionnalités de l'app | Oui | Non |
| Diagnostic → Données de performance / journaux | Fonctionnalités de l'app | Non | Non |

Aucune donnée n'est utilisée pour le suivi publicitaire (répondre « Non » à « Suivi »).

---

## 6. Disponibilité et tarif

- **Prix de l'app** : Gratuit
- **Disponibilité** : France (et autres pays francophones si souhaité)
- Le Pack premium est un achat par bien, présenté dans l'app.

---

## 7. Checklist avant « Soumettre pour examen »

- [ ] Nouveau build (icône + nom « Achètes ma maison ») sélectionné dans la version
- [ ] 7 captures iPhone 6,9" + 7 captures iPad 13" importées
- [ ] Nom, sous-titre, texte promotionnel, description, mots-clés collés
- [ ] URL d'assistance et URL de confidentialité renseignées avec le domaine publié
- [ ] Questionnaire « Confidentialité de l'app » complété
- [ ] Compte de démonstration + notes pour l'examinateur renseignés
- [ ] Décision prise sur le paiement du Pack (achat intégré recommandé)
