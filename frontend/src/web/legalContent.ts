import type { SeoPageContent } from "@/src/web/seoContent";

const BRAND = "Achète ma maison";
const CONTACT = "contact@achetesmamaison.fr";
/** Informations éditeur à compléter par l'exploitant du site (marquées [À COMPLÉTER]). */
const EDITOR = {
  raison: "[À COMPLÉTER : raison sociale ou nom de l’exploitant]",
  forme: "[À COMPLÉTER : forme juridique et capital, ou « entrepreneur individuel »]",
  siret: "[À COMPLÉTER : n° SIREN/SIRET et, le cas échéant, n° de TVA intracommunautaire]",
  adresse: "[À COMPLÉTER : adresse du siège]",
  directeur: "[À COMPLÉTER : nom du directeur de la publication]",
};

export const LEGAL_PAGES: Record<string, SeoPageContent> = {
  "mentions-legales": {
    path: "/mentions-legales",
    title: "Mentions légales",
    description: `Mentions légales du site ${BRAND} : éditeur, hébergeur, propriété intellectuelle, données personnelles, contact.`,
    h1: "Mentions légales",
    intro: `Informations légales relatives au site et à l’application ${BRAND}, conformément à la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l’économie numérique.`,
    showEstimate: false,
    footerOnly: true,
    sections: [
      { h2: "Éditeur du site", paragraphs: [
        `${EDITOR.raison} — ${EDITOR.forme}.`,
        `${EDITOR.siret}.`,
        `Siège : ${EDITOR.adresse}.`,
        `Directeur de la publication : ${EDITOR.directeur}.`,
        `Contact : ${CONTACT}.`,
      ] },
      { h2: "Hébergement", paragraphs: [
        "Le site et l’application sont hébergés sur la plateforme Emergent (emergent.sh), Emergent Labs, Inc. Les données sont stockées sur une infrastructure cloud sécurisée ; les fichiers (photos, documents) sont conservés dans un espace de stockage objet chiffré.",
      ] },
      { h2: "Propriété intellectuelle", paragraphs: [
        `L’ensemble du site (textes, logo, interface, méthodes de calcul, rapports) est protégé par le droit d’auteur et le droit des marques. Toute reproduction, représentation ou extraction, totale ou partielle, sans autorisation écrite de ${BRAND} est interdite.`,
        "Les photos et documents importés par les utilisateurs restent leur propriété ; ils ne sont utilisés que pour fournir le service.",
      ] },
      { h2: "Sources des données", paragraphs: [
        "Ventes immobilières : base « Demandes de valeurs foncières » (DVF), DGFiP / Etalab, licence ouverte 2.0. Adresses : Base Adresse Nationale (BAN). Cadastre, bâti, relief : IGN. Occupation du sol : Corine Land Cover. Risques : Géorisques (BRGM / ministère de la Transition écologique). Commerces, services et transports : OpenStreetMap (ODbL).",
        "Les estimations produites sont des avis de valeur indicatifs : elles ne constituent ni une expertise immobilière au sens juridique, ni une garantie du prix de vente.",
      ] },
      { h2: "Données personnelles", paragraphs: [
        "Le traitement des données personnelles est décrit dans la politique de confidentialité, accessible depuis le pied de page. Vous disposez d’un droit d’accès, de rectification, d’effacement et de portabilité, exerçable à l’adresse de contact ci-dessus ou directement depuis votre compte (suppression du compte et des données en un clic).",
      ] },
    ],
    faq: [],
  },
  cgu: {
    path: "/cgu",
    title: "Conditions générales d’utilisation et de vente",
    description: `Conditions générales d’utilisation du site et de l’application ${BRAND} et conditions de vente du Pack premium.`,
    h1: "Conditions générales d’utilisation et de vente",
    intro: `Les présentes conditions régissent l’utilisation du site et de l’application ${BRAND} (ci-après « le Service ») et l’achat du Pack premium. En créant un compte, vous les acceptez.`,
    showEstimate: false,
    footerOnly: true,
    sections: [
      { h2: "1. Objet du Service", paragraphs: [
        "Le Service permet à un particulier d’estimer la valeur d’un bien immobilier à partir des ventes réelles enregistrées, d’analyser son environnement, puis de préparer sa mise en vente : prix cible, photos, annonce, checklist des diagnostics et documents, export pour le notaire.",
        "Le Service ne réalise aucune transaction, ne met pas en relation acheteurs et vendeurs et n’exerce aucune activité d’agent immobilier au sens de la loi Hoguet.",
      ] },
      { h2: "2. Compte utilisateur", paragraphs: [
        "La création d’un compte (adresse e-mail et mot de passe) est gratuite et réservée aux personnes majeures. Vous êtes responsable de la confidentialité de vos identifiants. Vous pouvez supprimer votre compte à tout moment depuis « Mon compte » ou via la page de suppression en ligne ; les données associées sont alors effacées.",
      ] },
      { h2: "3. Estimations : nature indicative", paragraphs: [
        "Les estimations sont des avis de valeur calculés automatiquement à partir de données publiques et de vos déclarations. Elles sont fournies à titre indicatif, sans garantie d’exactitude ni de prix de vente. Elles ne remplacent ni une expertise, ni un avis de valeur d’un professionnel, ni un diagnostic. Vous restez seul décisionnaire du prix de mise en vente.",
      ] },
      { h2: "4. Pack premium (49 € TTC par bien)", paragraphs: [
        "Le Pack premium est un achat unique, par bien, qui débloque : rédaction d’annonce par IA, retouches photo par IA (nombre illimité pour le bien), lecture automatique des documents, dossier de vente complet et export PDF, conseils pour les visites, PDF d’annonce premium.",
        "Paiement : par carte via Stripe sur le site ; via l’App Store ou Google Play dans l’application mobile (achat intégré). Le prix affiché est TTC. Une confirmation est envoyée par e-mail.",
        "Droit de rétractation : conformément à l’article L221-28 du Code de la consommation, le contenu numérique est fourni immédiatement après paiement avec votre accord exprès ; vous reconnaissez renoncer à votre droit de rétractation dès le déblocage. En cas de dysfonctionnement avéré du Service empêchant l’usage du Pack, contactez-nous : un remboursement pourra être accordé.",
        "Achats intégrés mobiles : la gestion des remboursements relève des conditions d’Apple ou de Google.",
      ] },
      { h2: "5. Contenus générés par IA", paragraphs: [
        "Les annonces et retouches photo générées par IA sont des propositions : vous devez les relire et vous assurer de leur exactitude avant publication. Les retouches ne modifient pas la réalité du bien (aucun élément ajouté ou supprimé de façon trompeuse) et portent la mention « non contractuel » ; l’original est toujours conservé. Vous êtes responsable des contenus que vous publiez à partir du Service.",
      ] },
      { h2: "6. Obligations de l’utilisateur", paragraphs: [
        "Vous vous engagez à n’importer que des biens, photos et documents dont vous disposez des droits, à fournir des informations sincères, et à ne pas détourner le Service (extraction massive de données, revente, usage frauduleux).",
      ] },
      { h2: "7. Disponibilité et responsabilité", paragraphs: [
        `${BRAND} met tout en œuvre pour assurer la disponibilité du Service, sans garantie d’absence d’interruption. Les données externes (DVF, Géorisques, OpenStreetMap…) sont fournies par des tiers et peuvent comporter des erreurs ou retards. La responsabilité de l’éditeur ne saurait être engagée pour un dommage indirect, une perte de chance ou un écart entre une estimation et un prix de vente.`,
      ] },
      { h2: "8. Données personnelles", paragraphs: [
        "Voir la politique de confidentialité. Aucune donnée n’est vendue ni transmise à des agences ou annonceurs.",
      ] },
      { h2: "9. Droit applicable", paragraphs: [
        "Les présentes conditions sont soumises au droit français. En cas de litige, une solution amiable sera recherchée ; le consommateur peut recourir gratuitement à un médiateur de la consommation ou à la plateforme européenne de règlement en ligne des litiges. À défaut, les tribunaux français sont compétents.",
        "Version en vigueur : octobre 2026.",
      ] },
    ],
    faq: [],
  },
  faq: {
    path: "/faq",
    title: "FAQ : estimation gratuite, Pack premium, données et confidentialité",
    description: `Réponses aux questions fréquentes sur ${BRAND} : fiabilité de l’estimation, données utilisées, Pack premium à 49 €, photos IA, dossier de vente, confidentialité.`,
    h1: "Questions fréquentes",
    intro: `Tout ce qu’il faut savoir avant d’estimer et de vendre votre bien avec ${BRAND}. Une question sans réponse ? Écrivez-nous à ${CONTACT}.`,
    showEstimate: false,
    sections: [],
    faq: [
      { q: "L’estimation est-elle vraiment gratuite et sans inscription ?", a: "Oui. Le questionnaire complet (adresse, surface, état, année, terrain, équipements) et le résultat détaillé (valeur, fourchette, ajustements) sont gratuits et accessibles sans compte. Créer un compte, également gratuit, permet d’enregistrer le bien, de consulter le dossier environnement et les ventes comparables, puis de préparer la vente." },
      { q: "Sur quelles données repose l’estimation ?", a: "Sur les ventes réelles enregistrées par l’État (base DVF) autour de votre adresse, ramenées à la surface de votre bien, puis ajustées de façon transparente selon l’état, l’époque de construction, le terrain, les équipements et l’environnement mesuré (services, nuisances, risques). Trois approches sont combinées : comparables, modèle hédonique et apprentissage automatique." },
      { q: "Quelle est la fiabilité ? Pourquoi une fourchette ?", a: "Aucun modèle ne connaît l’état exact de votre bien ni la négociation à venir : nous affichons donc toujours une fourchette (±5 % autour de la valeur centrale) avec le nombre de ventes comparables et le rayon retenu. Plus il y a de ventes proches et récentes, plus l’estimation est robuste. Il s’agit d’un avis de valeur indicatif, pas d’une garantie de prix." },
      { q: "Quelles zones sont couvertes ?", a: "Toute la France métropolitaine, la Corse et les DOM (Guadeloupe, Martinique, Guyane, La Réunion), soit 97 départements. L’Alsace-Moselle (57, 67, 68) n’est pas couverte : ses ventes ne sont pas publiées dans la base DVF." },
      { q: "Qu’est-ce que le dossier environnement ?", a: "Une analyse du voisinage de l’adresse à partir de sources officielles et d’OpenStreetMap : écoles, commerces, transports, espaces verts, nuisances (routes, voies ferrées, installations classées), risques naturels (inondation, argile, radon), urbanisme (zonage, servitudes), relief et occupation du sol. Ses conclusions ajustent l’estimation et alimentent l’annonce." },
      { q: "Que contient le Pack premium à 49 € ?", a: "Un paiement unique par bien qui débloque la rédaction d’annonce par IA (avec accroche structurée), les retouches photo IA illimitées, la lecture automatique des documents (diagnostics, titre, taxe foncière…), le dossier de vente complet avec export PDF pour le notaire, le PDF d’annonce premium et les conseils pour les visites. Sans abonnement, sans commission." },
      { q: "Les photos retouchées par IA sont-elles honnêtes ?", a: "Oui : la retouche améliore lumière, couleurs, netteté et perspective, range les petits objets gênants, mais n’ajoute ni ne supprime aucun élément de la pièce et ne masque pas les défauts. L’original est toujours conservé et la version retouchée porte la mention « visuel retouché par IA · non contractuel »." },
      { q: "L’annonce générée peut-elle inventer des atouts ?", a: "Non. L’IA n’utilise que les faits que vous avez déclarés et les atouts du quartier réellement mesurés (distance à l’école, aux commerces, à la gare…). Elle ne qualifie pas le quartier et reprend l’état du bien tel que vous l’avez indiqué. Vous relisez et modifiez le texte avant de le publier." },
      { q: "Quels diagnostics sont obligatoires pour vendre ?", a: "La checklist s’adapte à votre bien : DPE, électricité et gaz (installations de plus de 15 ans), amiante (permis avant juillet 1997), plomb (avant 1949), termites selon la zone, état des risques (ERP), assainissement non collectif, mesurage et documents de copropriété pour un appartement, étude géotechnique si le terrain est argileux… Chaque pièce indique sa durée de validité et son statut." },
      { q: "Mes données sont-elles revendues ou transmises à des agences ?", a: "Jamais. Vos coordonnées, biens, photos et documents servent uniquement à fournir le service. Vous pouvez supprimer votre compte et l’ensemble de vos données à tout moment depuis « Mon compte »." },
      { q: "Le site et l’application mobile sont-ils synchronisés ?", a: "Oui : même compte, mêmes biens, mêmes documents. Vous pouvez estimer sur le site, prendre les photos avec l’application mobile et finaliser le dossier sur ordinateur." },
      { q: "Comment vous contacter ?", a: `Par e-mail à ${CONTACT}. Nous répondons sous 48 h ouvrées.` },
    ],
  },
  "conseils-vente": {
    path: "/conseils-vente",
    title: "Préparer la vente de sa maison : 10 conseils pour vendre vite et au bon prix",
    description: "Conseils pratiques pour préparer la vente d’un bien immobilier : fixer le prix, diagnostics, photos, annonce, visites, offre d’achat, compromis et acte authentique.",
    h1: "Préparer la vente de son bien : le guide pas à pas",
    intro: "Vendre sans agence est à la portée de tout vendeur organisé. Voici les étapes qui font la différence entre une vente qui traîne et une vente conclue en quelques semaines au bon prix.",
    showEstimate: true,
    sections: [
      { h2: "1. Partir d’un prix juste, pas d’un prix espéré", paragraphs: [
        "Les premières semaines de diffusion sont décisives : un bien affiché trop cher est ignoré, puis perçu comme « ayant un problème » quand son prix baisse. Appuyez-vous sur les ventes réelles autour de chez vous, comparez des biens de même type et de surface proche, et fixez un prix dans la fourchette estimée en tenant compte de la marge de négociation habituelle (environ 5 %).",
      ] },
      { h2: "2. Rassembler les diagnostics avant la mise en vente", paragraphs: [
        "Le dossier de diagnostic technique (DPE, électricité, gaz, amiante, plomb, termites, ERP, assainissement…) doit être remis à l’acheteur dès la promesse. Le commander en amont évite les surprises (par exemple un DPE F ou G qui impose d’annoncer la classe et peut peser sur le prix) et rassure les visiteurs sérieux.",
      ], bullets: ["DPE : valable 10 ans, obligatoire dans l’annonce", "Électricité et gaz : 3 ans, si l’installation a plus de 15 ans", "ERP (état des risques) : 6 mois", "Assainissement non collectif : contrôle SPANC de moins de 3 ans"] },
      { h2: "3. Préparer le bien : désencombrer, réparer, nettoyer", paragraphs: [
        "Un bien rangé paraît plus grand et mieux entretenu. Réparez les petits défauts visibles (poignée, joint, ampoule, trace d’humidité traitée), neutralisez les odeurs, aérez et soignez l’entrée et la façade : la première impression se joue dès le trottoir.",
      ] },
      { h2: "4. Soigner les photos", paragraphs: [
        "Les photos décident du clic sur l’annonce. Photographiez de jour, volets ouverts, lumières allumées, à hauteur de poitrine, en cadrant large depuis un angle de la pièce. Ordre conseillé : façade, salon, cuisine, jardin, suite parentale, chambres, salle de bains, terrasse, garage, vue extérieure. La retouche IA améliore la lumière et la netteté sans jamais travestir la réalité.",
      ] },
      { h2: "5. Rédiger une annonce factuelle et complète", paragraphs: [
        "Une accroche structurée (commune, type, pièces, surface, chambres, atouts, terrain, DPE), puis une description qui va du général au particulier : situation, distribution des pièces, prestations, extérieurs, environnement mesuré (écoles, commerces, gare à telle distance). Évitez les superlatifs invérifiables et indiquez clairement le prix et les charges.",
      ] },
      { h2: "6. Organiser les visites", paragraphs: [
        "Qualifiez les contacts par téléphone (projet, financement, délai), groupez les visites sur des créneaux lumineux, laissez les visiteurs se projeter sans monologue, et préparez les réponses aux questions récurrentes : charges, taxe foncière, travaux réalisés, voisinage, chauffage. Ayez le dossier de diagnostics à portée de main.",
      ] },
      { h2: "7. Recevoir et négocier une offre d’achat", paragraphs: [
        "Une offre écrite précise le prix, le mode de financement et la durée de validité. Vérifiez la solidité du financement (simulation ou accord de principe bancaire). Vous pouvez accepter, refuser ou faire une contre-proposition ; une fois acceptée par écrit, l’offre engage le vendeur au prix convenu.",
      ] },
      { h2: "8. Signer le compromis ou la promesse de vente", paragraphs: [
        "L’avant-contrat se signe chez le notaire (ou sous seing privé) avec le dossier de diagnostics, le titre de propriété et, pour une copropriété, les documents de la loi ALUR. L’acheteur dispose d’un délai de rétractation de 10 jours ; les conditions suspensives (prêt, urbanisme, préemption) protègent les deux parties.",
      ] },
      { h2: "9. Préparer l’acte authentique", paragraphs: [
        "Entre le compromis et la signature définitive (en général 2 à 3 mois), le notaire purge le droit de préemption, réunit les pièces d’urbanisme et vérifie la situation hypothécaire. Préparez les relevés de compteurs, les contrats à transférer ou résilier, les clés et les notices des équipements.",
      ] },
      { h2: "10. Le jour de la signature", paragraphs: [
        "Faites une dernière visite avec l’acheteur pour constater l’état du bien et relever les compteurs. Le prix est versé au notaire puis à vous après déduction des frais éventuels. Pensez à votre déménagement, aux déclarations fiscales (plus-value hors résidence principale) et au changement d’adresse.",
      ] },
    ],
    faq: [
      { q: "Faut-il un agent immobilier pour vendre ?", a: "Non. Vendre entre particuliers est légal et courant ; l’acte doit simplement être reçu par un notaire. Vous économisez la commission d’agence (4 à 6 % du prix en moyenne) en prenant en charge l’estimation, l’annonce et les visites." },
      { q: "Combien de temps dure une vente ?", a: "Entre la mise en ligne et la signature définitive, comptez en moyenne 3 à 5 mois : 1 à 2 mois pour trouver un acheteur au prix juste, puis 2 à 3 mois entre le compromis et l’acte." },
      { q: "Quels documents fournir pour un appartement en copropriété ?", a: "Règlement de copropriété, procès-verbaux des trois dernières assemblées générales, carnet d’entretien, montant des charges, pré-état daté, fiche synthétique, diagnostic technique global si l’immeuble a plus de 15 ans, et mesurage loi Carrez." },
    ],
  },
};
