export interface SeoPageContent {
  path: string;
  title: string;
  description: string;
  h1: string;
  intro: string;
  sections: { h2: string; paragraphs: string[]; bullets?: string[] }[];
  faq: { q: string; a: string }[];
}

const SOURCES = "Nos estimations s’appuient sur les ventes réelles publiées par l’État (base DVF – Demandes de valeurs foncières), enrichies par les données officielles d’adresse (BAN), de cadastre et d’environnement (IGN, Géorisques, OpenStreetMap).";

export const SEO_PAGES: Record<string, SeoPageContent> = {
  "estimation-maison": {
    path: "/estimation-maison",
    title: "Estimation maison gratuite en ligne : combien vaut votre maison ?",
    description: "Estimation gratuite de votre maison en 2 minutes à partir des ventes réelles autour de chez vous (DVF). Fourchette de prix, prix au m², ventes comparables.",
    h1: "Estimation de maison gratuite, fondée sur les ventes réelles",
    intro: "Renseignez l’adresse et quelques caractéristiques : Achète ma maison calcule immédiatement une fourchette de valeur à partir des ventes enregistrées autour de chez vous, sans inscription et sans démarchage.",
    sections: [
      { h2: "Comment est calculée l’estimation de votre maison ?", paragraphs: [
        SOURCES,
        "Le moteur sélectionne les ventes de maisons comparables (distance, taille de commune, surface, période), ramène leur prix au m² à la surface de votre bien, puis applique des ajustements transparents : état général, époque de construction, terrain, équipements et environnement (nuisances, services, risques). Trois modèles sont combinés : comparables, modèle hédonique et apprentissage automatique.",
      ], bullets: ["Fourchette resserrée (±5 %) avec indice de confiance", "Chaque ajustement est expliqué ligne par ligne", "Prise en compte de l’époque : une maison des années 1970 n’est pas estimée comme une construction récente", "Analyse de l’environnement : calme, commerces, écoles, risques naturels"] },
      { h2: "Pourquoi estimer sa maison avant de vendre ?", paragraphs: [
        "Un prix trop élevé fait fuir les acheteurs et allonge le délai de vente ; un prix trop bas vous fait perdre plusieurs milliers d’euros. Une estimation objective, appuyée sur des ventes réelles, vous permet de fixer un prix de mise en vente cohérent et de le défendre face aux acheteurs.",
        "Après l’estimation, l’application vous accompagne en 3 étapes : Estimation, Mise en vente (photos retouchées par IA, annonce rédigée, prix cible) et Vendu (dossier de vente et diagnostics).",
      ] },
    ],
    faq: [
      { q: "L’estimation est-elle vraiment gratuite ?", a: "Oui. L’estimation et ses explications sont gratuites et sans engagement. Seuls les outils de mise en vente (retouche photo IA, annonce, dossier complet) font partie du Pack premium à 49 €." },
      { q: "Quelle est la fiabilité de l’estimation ?", a: "Elle dépend du nombre de ventes comparables autour de votre adresse : l’indice de confiance et le rayon retenu sont affichés. Pour un bien atypique, complétez le questionnaire détaillé après inscription." },
      { q: "Mes données sont-elles partagées avec des agences ?", a: "Non. Aucune donnée n’est transmise à des agences ou à des annonceurs. Vous pouvez supprimer votre compte et vos données à tout moment." },
    ],
  },
  "estimation-immobiliere": {
    path: "/estimation-immobiliere",
    title: "Estimation immobilière gratuite : maison ou appartement, prix au m²",
    description: "Estimation immobilière gratuite et immédiate pour une maison ou un appartement partout en France. Prix au m² de votre commune et ventes comparables DVF.",
    h1: "Estimation immobilière gratuite, partout en France",
    intro: "Maison ou appartement, en ville ou à la campagne : obtenez une fourchette de valeur fondée sur les ventes réelles des 97 départements couverts, en 2 minutes.",
    sections: [
      { h2: "Une estimation immobilière objective", paragraphs: [SOURCES, "Contrairement à une estimation d’agence, qui peut être orientée pour obtenir un mandat, le calcul est purement statistique et vérifiable : vous consultez les ventes comparables retenues, leur distance et leur poids dans le résultat."] },
      { h2: "Appartement : ce qui compte vraiment", paragraphs: ["Étage et ascenseur, dernier étage, balcon ou terrasse, stationnement (place, box ou garage), charges et performance énergétique sont pris en compte dans l’estimation, en plus de la localisation fine."] },
      { h2: "Maison : terrain, époque et équipements", paragraphs: ["Surface du terrain, époque de construction, plain-pied, piscine, dépendances, chauffage et DPE ajustent la valeur par rapport à la maison type vendue dans votre secteur. Une construction récente est adossée au coût de construction actuel lorsque le marché local ne porte que sur de l’ancien."] },
    ],
    faq: [
      { q: "Quelles zones sont couvertes ?", a: "La France métropolitaine, la Corse et les départements d’outre-mer (Guadeloupe, Martinique, Guyane, La Réunion), soit 97 départements." },
      { q: "Puis-je estimer plusieurs biens ?", a: "Oui, autant que vous le souhaitez. Chaque bien est suivi dans votre espace, sur le site comme dans l’application mobile." },
    ],
  },
  "combien-vaut-ma-maison": {
    path: "/combien-vaut-ma-maison",
    title: "Combien vaut ma maison ? Réponse gratuite en 2 minutes",
    description: "Combien vaut ma maison aujourd’hui ? Obtenez une fourchette de prix gratuite basée sur les ventes réelles de votre quartier, avec le détail du calcul.",
    h1: "Combien vaut ma maison ?",
    intro: "La réponse se trouve dans les ventes réelles autour de chez vous. Saisissez votre adresse : nous comparons votre maison aux maisons vendues récemment dans votre secteur et vous expliquons chaque écart.",
    sections: [
      { h2: "Les 5 facteurs qui font le prix de votre maison", paragraphs: ["Dans l’ordre d’importance : la localisation (commune, quartier, environnement), la surface habitable et le terrain, l’époque de construction et la performance énergétique, l’état général, puis les équipements (garage, piscine, dépendances)."], bullets: ["Localisation : jusqu’à ±30 % entre deux communes voisines", "Époque : une maison des années 1960–1980 se vend 5 à 10 % sous une maison des années 2000, et bien en dessous d’une construction RT 2012", "État : de −15 % (à rénover) à +8 % (neuf)", "DPE : les classes F et G sont fortement décotées"] },
      { h2: "Prix au m² : attention aux moyennes", paragraphs: ["Le prix moyen au m² d’une ville mélange studios et maisons, centre et périphérie. Notre estimation ne se base que sur des maisons comparables à la vôtre, ramenées à votre surface. Consultez aussi nos pages Prix immobilier par commune pour situer votre secteur."] },
    ],
    faq: [
      { q: "Faut-il créer un compte ?", a: "Non pour la fourchette gratuite. Le compte (gratuit) sert à sauvegarder le bien, affiner l’estimation avec le questionnaire complet et préparer la vente." },
      { q: "L’estimation remplace-t-elle un expert ?", a: "Non : c’est un outil d’aide à la décision, indicatif. Pour une succession, un divorce ou un litige, une expertise réglementée reste nécessaire." },
    ],
  },
  "vendre-sa-maison": {
    path: "/vendre-sa-maison",
    title: "Vendre sa maison entre particuliers : estimation, photos, annonce, dossier",
    description: "Vendez votre maison entre particuliers sans commission d’agence : estimation gratuite, photos retouchées par IA, annonce rédigée, dossier de vente et diagnostics guidés.",
    h1: "Vendre sa maison entre particuliers, étape par étape",
    intro: "Achète ma maison vous accompagne de l’estimation à la signature : fixez le bon prix, présentez votre bien comme un professionnel et constituez un dossier de vente complet, sans commission d’agence.",
    sections: [
      { h2: "Étape 1 — Estimer au juste prix", paragraphs: ["Fourchette fondée sur les ventes réelles, explications ligne par ligne, analyse de l’environnement, tendance du marché local et signal « bon moment pour vendre »."] },
      { h2: "Étape 2 — Mettre en vente", paragraphs: ["Fixez votre prix cible, importez vos photos : l’IA les retouche en photographie immobilière professionnelle (lumière, perspectives, rangement) sans rien inventer, puis rédige une annonce prête à publier avec une accroche structurée. Conseils pour réussir les visites."], bullets: ["Ordre conseillé des photos : façade, salon, cuisine, jardin…", "Annonce enrichie des atouts de l’environnement", "Prix cible comparé au marché"] },
      { h2: "Étape 3 — Vendu : le dossier de vente", paragraphs: ["Liste des diagnostics et documents obligatoires adaptée à votre bien (année, zone, copropriété), lecture automatique des documents, suivi des dates de validité, dossier PDF prêt pour le notaire et l’acheteur."] },
      { h2: "Combien ça coûte ?", paragraphs: ["L’estimation est gratuite. Le Pack premium (49 € par bien, paiement unique) débloque la retouche photo IA, l’annonce, la lecture des documents et les PDF. À comparer aux 4 à 6 % de commission d’une agence : 10 000 € pour une maison de 200 000 €."] },
    ],
    faq: [
      { q: "Où publier mon annonce ?", a: "Le texte et les photos sont exportables vers les portails entre particuliers (Leboncoin, PAP…) et les réseaux sociaux. L’application ne publie pas à votre place." },
      { q: "Quels diagnostics sont obligatoires ?", a: "DPE, amiante (avant 1997), plomb (avant 1949), électricité et gaz (installations de plus de 15 ans), ERP (risques), termites selon la zone, assainissement non collectif, Loi Carrez en copropriété. La liste est générée automatiquement pour votre bien." },
    ],
  },
};
