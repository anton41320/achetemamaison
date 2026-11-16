import type { ImageSourcePropType } from "react-native";

/** Contenu des pages « étape » du parcours (site web) : argumentaire + visuels, sans témoignage fictif. */
export type StepBlock = {
  title: string;
  text: string;
  bullets?: string[];
  /** Visuel du bloc ; absent → bloc texte seul. */
  image?: ImageSourcePropType;
  /** Légende factuelle sous le visuel (jamais une citation attribuée). */
  caption?: string;
  /** Visuel « avant / après » (deux images côte à côte). */
  after?: ImageSourcePropType;
};

export type StepContent = {
  n: 1 | 2 | 3;
  slug: string;
  path: string;
  title: string;
  description: string;
  h1: string;
  tagline: string;
  intro: string;
  /** Noisette dans la posture de l'étape (fond transparent). */
  mascot: ImageSourcePropType;
  blocks: StepBlock[];
  cta: { label: string; href: string };
};

export const STEP_PAGES: StepContent[] = [
  {
    n: 1,
    slug: "etape-estimation",
    path: "/etape-estimation",
    title: "Étape 1 · Estimation : la plus fiable et la plus rapide",
    description: "Estimation immobilière gratuite en 2 minutes, fondée sur les ventes réelles autour de chez vous et expliquée ligne par ligne.",
    h1: "L’estimation la plus fiable, la plus rapide",
    tagline: "ÉTAPE 1 · ESTIMATION",
    intro: "Deux minutes, une adresse, quelques caractéristiques : vous obtenez une fourchette de prix fondée sur ce qui s’est réellement vendu autour de chez vous — et vous comprenez pourquoi.",
    mascot: require("../../assets/mascot/etape2-course.webp"),
    blocks: [
      {
        title: "Des ventes réelles, pas des annonces",
        text: "Notre moteur s’appuie sur les transactions enregistrées par les notaires (base DVF de l’État), pas sur les prix affichés dans les annonces, souvent surévalués de 5 à 10 %. Il retient les biens comparables au vôtre, dans votre quartier, sur les derniers mois.",
        bullets: ["Transactions réelles des 5 dernières années", "Comparables sélectionnés par distance, surface, type et époque", "Tendance du marché local intégrée"],
        image: require("../../assets/web/map-data.jpg"),
        caption: "Chaque adresse est croisée avec les ventes du voisinage et les données publiques (cadastre, DPE, risques).",
      },
      {
        title: "Plusieurs méthodes, un seul prix cohérent",
        text: "Une seule méthode se trompe ; trois méthodes qui convergent, rarement. Nous croisons la comparaison directe, un modèle statistique entraîné sur des dizaines de milliers de ventes et une analyse des caractéristiques (état, travaux, terrain, extérieur, véranda…).",
        bullets: ["Fourchette basse / cible / haute", "Indice de confiance affiché clairement", "Chaque ajustement expliqué ligne par ligne"],
        image: require("../../assets/web/step1-trust.jpg"),
      },
      {
        title: "Tout ce qui compte autour de votre bien",
        text: "Écoles, transports, commerces, espaces verts, nuisances, risques naturels : le prix dépend aussi de l’environnement. Nous l’analysons automatiquement pour chaque adresse et nous l’intégrons à l’estimation.",
        image: require("../../assets/web/step1-sources.jpg"),
      },
    ],
    cta: { label: "Estimer mon bien gratuitement", href: "/estimation-maison" },
  },
  {
    n: 2,
    slug: "etape-mise-en-vente",
    path: "/etape-mise-en-vente",
    title: "Étape 2 · Mise en vente : photos IA, annonce et prix cible",
    description: "Photos retouchées par IA fidèles au bien, annonce rédigée automatiquement, prix cible et conseils pour les visites.",
    h1: "Une mise en vente digne d’un professionnel",
    tagline: "ÉTAPE 2 · MISE EN VENTE",
    intro: "Le prix est fixé ; il faut maintenant donner envie. Photos propres et lumineuses, annonce claire, bon positionnement : tout ce qu’une agence fait pour vous, en quelques minutes, sans commission.",
    mascot: require("../../assets/mascot/etape1-telephone.webp"),
    blocks: [
      {
        title: "Vos photos, version professionnelle",
        text: "Notre retouche par IA range, éclaire et nettoie : vaisselle, câbles, objets qui traînent disparaissent. Mais rien n’est inventé : les murs, les ouvertures, le mobilier, la vue et la météo restent exactement ceux de votre bien. Un contrôle automatique vérifie chaque image avant de vous la rendre.",
        bullets: ["Désencombrement et lumière corrigés", "Fidélité au bien garantie : l’acheteur ne sera pas surpris", "Originaux conservés, export HD en un clic"],
        image: require("../../assets/images/demo-before.jpg"),
        after: require("../../assets/images/demo-after.jpg"),
        caption: "Avant / après : même pièce, même angle, même lumière naturelle — seulement rangée.",
      },
      {
        title: "L’annonce rédigée pour vous",
        text: "À partir de votre bien, de son environnement et de votre estimation, l’IA écrit une annonce structurée : accroche, description pièce par pièce, atouts du quartier, informations obligatoires. Vous la relisez, vous l’ajustez, vous la copiez sur Leboncoin, SeLoger ou PAP.",
        bullets: ["Accroche et description adaptées à votre bien", "Atouts du quartier mesurés : écoles, gare, commerces", "Mentions légales (DPE, copropriété) intégrées"],
        image: require("../../assets/web/step2-annonce.jpg"),
      },
      {
        title: "Un prix cible et des visites bien préparées",
        text: "Prix d’affichage, marge de négociation, ordre des visites, questions fréquentes des acheteurs : nous vous donnons une stratégie simple pour vendre au bon prix dans un délai raisonnable.",
        image: require("../../assets/web/step2-visite.jpg"),
      },
      {
        title: "Réussir ses photos soi-même",
        text: "Avant même la retouche, quelques règles font la différence : lumière du jour, cadrage à hauteur de poitrine, pièces rangées, volets ouverts. Notre guide intégré vous accompagne pièce par pièce.",
        image: require("../../assets/images/photo-tuto.jpg"),
      },
    ],
    cta: { label: "Commencer par mon estimation", href: "/estimation-maison" },
  },
  {
    n: 3,
    slug: "etape-vendu",
    path: "/etape-vendu",
    title: "Étape 3 · Vendu : le dossier complet pour le notaire",
    description: "Checklist des diagnostics et documents obligatoires adaptée à votre bien, lecture automatique de vos documents, PDF prêt pour le notaire.",
    h1: "Jusqu’à la signature, sans mauvaise surprise",
    tagline: "ÉTAPE 3 · VENDU",
    intro: "Un acheteur est prêt ? La vente se joue maintenant chez le notaire. Un dossier complet dès le compromis, c’est une signature plus rapide et moins de stress.",
    mascot: require("../../assets/mascot/etape3-notaire.webp"),
    blocks: [
      {
        title: "La liste exacte des documents pour votre bien",
        text: "Maison ou appartement, copropriété ou non, année de construction, zone à risques : la liste des diagnostics et pièces obligatoires change. Nous la générons pour votre bien précisément, et nous la mettons à jour quand la loi évolue.",
        bullets: ["Diagnostics (DPE, amiante, plomb, électricité, gaz, ERP, termites…)", "Titre de propriété, taxe foncière, PV d’assemblée générale…", "Statut de chaque pièce : à fournir, reçu, vérifié"],
        image: require("../../assets/web/step3-dossier.jpg"),
      },
      {
        title: "Vos documents lus et vérifiés automatiquement",
        text: "Photographiez ou importez chaque document : nous lisons la date, la validité, la surface, le classement énergétique et nous vous signalons ce qui manque ou ce qui a expiré — avant que le notaire ne le fasse.",
        caption: "Le dossier se complète au fil des semaines, depuis le téléphone, sans rien oublier.",
      },
      {
        title: "Un PDF prêt pour le notaire et les acheteurs",
        text: "En un clic, un dossier de vente complet : présentation du bien, estimation, environnement, diagnostics et pièces jointes. Vous l’envoyez au notaire et aux acheteurs sérieux, et vous marquez le bien « Vendu » le jour de la signature.",
        image: require("../../assets/web/step3-couple.jpg"),
        caption: "Les avis affichés sur notre site sont déposés par de vrais vendeurs depuis l’application et vérifiés avant publication.",
      },
    ],
    cta: { label: "Démarrer mon dossier de vente", href: "/estimation-maison" },
  },
];

export const stepBySlug = (slug: string) => STEP_PAGES.find((s) => s.slug === slug)!;
