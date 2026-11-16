import { Image } from "expo-image";
import { Link, useRouter } from "expo-router";
import { ShieldCheckIcon, SparkleIcon, StarIcon } from "phosphor-react-native";
import { Pressable, Text, View, useWindowDimensions } from "react-native";

import { BrandDash } from "@/src/components/BrandMarks";
import { EstimateDemo } from "@/src/components/EstimateDemo";
import { HeroDesktop } from "@/src/components/HeroDesktop";
import { HeroMobile } from "@/src/components/HeroMobile";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ReviewsSection } from "@/src/components/ReviewsSection";
import { StoreBadges } from "@/src/components/StoreBadges";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { FreeEstimate } from "@/src/web/FreeEstimate";
import { PublicPage, SITE_NAME, SITE_URL } from "@/src/web/PublicPage";
import { CONTENT_MAX_WIDTH, useBreakpoint } from "@/src/web/useBreakpoint";

const MAP_IMG = require("../../assets/web/map-data.jpg");
const STEP_MASCOTS = {
  1: require("../../assets/mascot/etape2-course.webp"),
  2: require("../../assets/mascot/etape1-telephone.webp"),
  3: require("../../assets/mascot/etape3-notaire.webp"),
} as const;

/** Ce que le moteur prend en compte (sans nommer les sources de données). */
const DATA_POINTS = [
  { title: "Ventes réelles du voisinage", text: "Les transactions récentes de biens comparables autour de l’adresse, ramenées à votre surface : c’est la base de la fourchette." },
  { title: "Votre bien, tel qu’il est", text: "Surface, pièces, état, époque de construction, terrain, équipements : chaque critère devient un ajustement affiché en % et en €." },
  { title: "Écoles, commerces, transports", text: "Distances réelles à pied aux services du quotidien, et accès aux transports : un atout mesuré, pas une impression." },
  { title: "Nature et cadre de vie", text: "Parcs, espaces verts, relief et exposition : ce qui rend un quartier agréable compte dans la valeur." },
  { title: "Nuisances et risques", text: "Routes passantes, voies ferrées, installations industrielles, zones inondables ou sols sensibles : identifiés et pris en compte." },
  { title: "Tendance du marché local", text: "Évolution des prix et délais de vente dans la commune : votre estimation suit le marché, pas une moyenne nationale." },
];

const STEPS = [
  { n: 1, title: "Estimation", mascot: STEP_MASCOTS[1], href: "/etape-estimation", text: "Fourchette fondée sur les ventes réelles autour de chez vous, expliquée ligne par ligne : état, époque, terrain, environnement, tendance du marché." },
  { n: 2, title: "Mise en vente", mascot: STEP_MASCOTS[2], href: "/etape-mise-en-vente", text: "Prix cible, photos retouchées par IA en qualité professionnelle, annonce rédigée avec une accroche structurée, conseils pour les visites." },
  { n: 3, title: "Vendu", mascot: STEP_MASCOTS[3], href: "/etape-vendu", text: "Dossier de vente complet : diagnostics et documents obligatoires adaptés à votre bien, lecture automatique, PDF prêt pour le notaire." },
];

const TRUST = [
  { icon: ShieldCheckIcon, title: "Données officielles", text: "DVF (ventes réelles), BAN, cadastre, IGN, Géorisques, OpenStreetMap. 97 départements couverts." },
  { icon: SparkleIcon, title: "IA au service du réel", text: "Les retouches photo n’inventent rien ; l’annonce ne cite que des faits vérifiés. L’original est toujours conservé." },
  { icon: StarIcon, title: "Sans commission", text: "Estimation gratuite. Pack premium 49 € par bien, paiement unique, contre 4 à 6 % de commission en agence." },
];

/** Page d'accueil vitrine (Web) : promesse, estimation gratuite, 3 étapes, confiance, avis clients, appel à l'action. */
export function LandingPage() {
  const styles = useStyles();
  const { colors } = useTheme();
  const { isDesktop, isTablet } = useBreakpoint();
  const { width: windowWidth } = useWindowDimensions();
  // Le héros ordinateur sort du conteneur centré (1120 px) pour occuper toute la largeur de la fenêtre.
  const bleed = Math.max(spacing.lg, (windowWidth - CONTENT_MAX_WIDTH) / 2 + spacing.lg);
  const router = useRouter();
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: SITE_NAME,
      alternateName: ["Achete ma maison", "achetemamaison", "Achète ma maison — estimation immobilière"],
      url: SITE_URL || undefined,
    },
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL || undefined,
      logo: SITE_URL ? `${SITE_URL}/app-image.png` : undefined,
      email: "contact@achetemamaison.fr",
      areaServed: "FR",
    },
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: SITE_NAME,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web, iOS, Android",
      description: "Estimation immobilière gratuite fondée sur les ventes réelles, puis accompagnement jusqu’à la vente entre particuliers.",
      offers: { "@type": "Offer", price: "0", priceCurrency: "EUR" },
    },
  ];

  return (
    <PublicPage
      title="Achète ma maison : estimation immobilière gratuite et vente entre particuliers"
      description="Estimez gratuitement votre maison ou appartement à partir des ventes réelles (DVF), puis vendez entre particuliers : photos retouchées par IA, annonce, dossier de vente complet."
      path="/accueil"
      jsonLd={jsonLd}
      testID="landing-page"
    >
      <View style={styles.hero}>
        {!isDesktop ? (
          <View style={{ marginHorizontal: -spacing.lg, marginTop: -2 * spacing.lg }}>
            <HeroMobile testID="landing-hero-mobile" />
          </View>
        ) : (
          <View style={{ alignSelf: "stretch", marginHorizontal: -bleed, marginTop: -2 * spacing.lg }}>
            <HeroDesktop testID="landing-hero-desktop" />
          </View>
        )}
        <View style={[styles.heroForm, isDesktop && { flexDirection: "row", alignItems: "flex-start", gap: spacing.xl }]}>
          <View style={isDesktop ? { flex: 1.25 } : { width: "100%" }}>
            <FreeEstimate />
          </View>
          <View style={isDesktop ? { flex: 0.75 } : { width: "100%" }} testID="landing-demo">
            <EstimateDemo />
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Un parcours en 3 étapes</Text></View>
        <View style={[styles.cards, isTablet && { flexDirection: "row" }]}>
          {STEPS.map((s) => (
            <Link key={s.n} href={s.href as any} asChild>
              <Pressable style={styles.stepCard} accessibilityRole="link" accessibilityLabel={`Étape ${s.n} : ${s.title}, en savoir plus`} testID={`landing-step-${s.n}`}>
                <Image source={s.mascot} style={styles.stepMascot} contentFit="contain" accessibilityLabel={`Noisette, étape ${s.n}`} transition={200} />
                <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>{s.n}</Text></View>
                <Text style={styles.cardTitle}>{s.title}</Text>
                <Text style={styles.cardText}>{s.text}</Text>
                <Text style={styles.stepMore}>En savoir plus →</Text>
              </Pressable>
            </Link>
          ))}
        </View>
      </View>

      <View style={styles.section} testID="landing-data">
        <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Une estimation qui regarde tout ce qui compte</Text></View>
        <Text style={styles.sectionLead}>
          Votre maison n’est pas qu’une surface : son prix dépend de ce qui s’est réellement vendu autour, de ce qu’elle est, et de tout ce qui l’entoure.
          Voici ce que notre moteur analyse pour chaque adresse.
        </Text>
        <View style={[styles.dataWrap, isDesktop && { flexDirection: "row", alignItems: "center" }]}>
          <Image
            source={MAP_IMG}
            style={[styles.mapImage, isDesktop && { flex: 1.1 }]}
            contentFit="contain"
            accessibilityLabel="Illustration : la maison au centre, reliée aux écoles, commerces, transports, parcs, nuisances, risques et aux ventes voisines"
            transition={300}
            testID="landing-map-image"
          />
          <View style={[styles.dataList, isDesktop && { flex: 1 }]}>
            {DATA_POINTS.map((d, i) => (
              <View key={d.title} style={styles.dataRow}>
                <View style={styles.dataNum}><Text style={styles.dataNumText}>{i + 1}</Text></View>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={styles.dataTitle}>{d.title}</Text>
                  <Text style={styles.cardText}>{d.text}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Pourquoi nous faire confiance</Text></View>
        <View style={[styles.cards, isTablet && { flexDirection: "row" }]}>
          {TRUST.map((t) => (
            <View key={t.title} style={styles.trustCard}>
              <t.icon size={26} color={colors.onBrandTertiary} weight="fill" />
              <Text style={[styles.cardTitle, { color: colors.onBrandTertiary }]}>{t.title}</Text>
              <Text style={[styles.cardText, { color: colors.onBrandTertiary }]}>{t.text}</Text>
            </View>
          ))}
        </View>
      </View>

      <ReviewsSection row={isTablet} />

      <View style={styles.ctaBlock} testID="landing-cta">
        <Text style={styles.ctaTitle}>Prêt à connaître la valeur de votre bien ?</Text>
        <Text style={styles.ctaText}>Estimation gratuite en 2 minutes, puis créez votre compte pour sauvegarder le bien et préparer la vente — sur le site comme dans l’application mobile.</Text>
        <View style={[styles.ctaRow, isTablet && { flexDirection: "row" }]}>
          <PrimaryButton title="Estimer gratuitement" onPress={() => router.navigate("/estimation-maison")} testID="landing-cta-estimate" />
          <PrimaryButton title="Créer mon compte" variant="secondary" onPress={() => router.navigate("/sign-up")} testID="landing-cta-signup" />
        </View>
        <Text style={styles.ctaText}>Ou emportez-la dans votre poche :</Text>
        <StoreBadges style={{ justifyContent: "center" }} />
        <Link href="/prix-immobilier" asChild>
          <Pressable accessibilityRole="link"><Text style={styles.link}>Voir les prix immobiliers par commune →</Text></Pressable>
        </Link>
      </View>
    </PublicPage>
  );
}

const useStyles = makeStyles((colors) => ({
  hero: { gap: spacing.xl, paddingTop: spacing.lg, alignItems: "center" },
  heroForm: { width: "100%" },
  sectionLead: { fontFamily: fonts.regular, fontSize: 16, lineHeight: 24, color: colors.onSurfaceTertiary, maxWidth: 760 },
  dataWrap: { gap: spacing.xl },
  mapImage: { width: "100%", aspectRatio: 1.6, borderRadius: radius.lg, backgroundColor: colors.surfaceSecondary },
  dataList: { gap: spacing.md },
  dataRow: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  dataNum: { width: 28, height: 28, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center", marginTop: 2 },
  dataNumText: { fontFamily: fonts.bold, fontSize: 13, color: colors.onBrandTertiary },
  dataTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface },
  section: { gap: spacing.md },
  h2Row: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h2: { fontFamily: fonts.extrabold, fontSize: 26, lineHeight: 34, color: colors.onSurface, flexShrink: 1 },
  cards: { flexDirection: "column", gap: spacing.md },
  stepCard: { flex: 1, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  stepMore: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary, marginTop: spacing.xs },
  stepMascot: { width: "100%", height: 160 },
  stepBadge: { width: 32, height: 32, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  stepBadgeText: { fontFamily: fonts.bold, fontSize: 15, color: colors.onBrandPrimary },
  cardTitle: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurface },
  cardText: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceTertiary },
  trustCard: { flex: 1, backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  quoteCard: { flex: 1, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, borderWidth: 1, borderColor: colors.border },
  quote: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 23, color: colors.onSurfaceSecondary, fontStyle: "italic" },
  quoteAuthor: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted },
  ctaBlock: { backgroundColor: colors.brandPrimary, borderRadius: radius.lg, padding: spacing.xl, gap: spacing.md, alignItems: "center" },
  ctaTitle: { fontFamily: fonts.bold, fontSize: 26, lineHeight: 34, color: colors.onBrandPrimary, textAlign: "center" },
  ctaText: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, color: colors.onBrandPrimary, textAlign: "center", maxWidth: 680 },
  ctaRow: { flexDirection: "column", gap: spacing.sm, width: "100%", maxWidth: 560 },
  link: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandPrimary, minHeight: 36, lineHeight: 36, textDecorationLine: "underline" },
}));
