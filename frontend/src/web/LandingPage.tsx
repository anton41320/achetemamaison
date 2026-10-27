import { Image } from "expo-image";
import { Link, useRouter } from "expo-router";
import { ChartBarIcon, FolderOpenIcon, ImagesIcon, ShieldCheckIcon, SparkleIcon, StarIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { BrandDash } from "@/src/components/BrandMarks";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { FreeEstimate } from "@/src/web/FreeEstimate";
import { PublicPage, SITE_NAME, SITE_URL } from "@/src/web/PublicPage";
import { useBreakpoint } from "@/src/web/useBreakpoint";

const HERO_IMG = require("../../assets/web/hero-house.webp");
const MAP_IMG = require("../../assets/web/map-data.jpg");

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
  { n: 1, title: "Estimation", icon: ChartBarIcon, text: "Fourchette fondée sur les ventes réelles autour de chez vous, expliquée ligne par ligne : état, époque, terrain, environnement, tendance du marché." },
  { n: 2, title: "Mise en vente", icon: ImagesIcon, text: "Prix cible, photos retouchées par IA en qualité professionnelle, annonce rédigée avec une accroche structurée, conseils pour les visites." },
  { n: 3, title: "Vendu", icon: FolderOpenIcon, text: "Dossier de vente complet : diagnostics et documents obligatoires adaptés à votre bien, lecture automatique, PDF prêt pour le notaire." },
];

const TRUST = [
  { icon: ShieldCheckIcon, title: "Données officielles", text: "DVF (ventes réelles), BAN, cadastre, IGN, Géorisques, OpenStreetMap. 97 départements couverts." },
  { icon: SparkleIcon, title: "IA au service du réel", text: "Les retouches photo n’inventent rien ; l’annonce ne cite que des faits vérifiés. L’original est toujours conservé." },
  { icon: StarIcon, title: "Sans commission", text: "Estimation gratuite. Pack premium 49 € par bien, paiement unique, contre 4 à 6 % de commission en agence." },
];

// À remplacer par vos témoignages réels (prénom, commune, autorisation de publication).
const TESTIMONIALS = [
  { name: "Sophie", place: "Loir-et-Cher", text: "L’estimation correspondait à ce que deux agences m’avaient annoncé, mais avec le détail du calcul. J’ai vendu en six semaines au prix fixé." },
  { name: "Marc", place: "Indre-et-Loire", text: "Les photos retouchées ont changé mon annonce du tout au tout, sans rien inventer. Le dossier de vente m’a évité des allers-retours avec le notaire." },
  { name: "Nadia", place: "Loiret", text: "Simple et honnête : on comprend pourquoi la maison vaut ce prix. Le rapport PDF a rassuré les acheteurs pendant les visites." },
];

/** Page d'accueil vitrine (Web) : promesse, estimation gratuite, 3 étapes, confiance, témoignages, appel à l'action. */
export function LandingPage() {
  const styles = useStyles();
  const { colors } = useTheme();
  const { isDesktop, isTablet } = useBreakpoint();
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
        <View style={[styles.heroTop, isDesktop && { flexDirection: "row", alignItems: "center" }]}>
          <View style={[styles.heroText, isDesktop && { flex: 1, alignItems: "flex-start" }]}>
          <Text style={[styles.kicker, isDesktop && { textAlign: "left" }]}>De l’estimation à la vente, sans agence</Text>
          <Text style={[styles.h1, isDesktop && { textAlign: "left" }]} accessibilityRole="header">Combien vaut votre maison ? La réponse est dans les ventes réelles.</Text>
          <Text style={[styles.lead, isDesktop && { textAlign: "left" }]}>
            {SITE_NAME} estime votre bien gratuitement et précisément : le questionnaire complet de l’application (adresse, surface, état, année,
            terrain, équipements) confronté aux transactions enregistrées autour de chez vous. Créez ensuite un compte gratuit pour enregistrer le bien
            et accéder au dossier environnement ; le Pack premium (49 €, paiement unique) ouvre les étapes 2 et 3 : photos, annonce, dossier de vente.
          </Text>
            <View style={[styles.badges, isDesktop && { justifyContent: "flex-start" }]}>
              {["Gratuit et sans inscription", "Questionnaire complet", "97 départements", "Fourchette ±5 %"].map((b) => (
                <View key={b} style={styles.badge}><Text style={styles.badgeText}>{b}</Text></View>
              ))}
            </View>
          </View>
          <Image
            source={HERO_IMG}
            style={[styles.heroImage, isDesktop && { flex: 1, maxWidth: 560 }]}
            contentFit="contain"
            accessibilityLabel="Une famille découvre l’estimation de sa maison sur son téléphone"
            transition={300}
            testID="landing-hero-image"
          />
        </View>
        <View style={[styles.heroForm, isDesktop && { maxWidth: 820 }]}>
          <FreeEstimate />
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Un parcours en 3 étapes</Text></View>
        <View style={[styles.cards, isTablet && { flexDirection: "row" }]}>
          {STEPS.map((s) => (
            <View key={s.n} style={styles.stepCard} testID={`landing-step-${s.n}`}>
              <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>{s.n}</Text></View>
              <s.icon size={28} color={colors.brandPrimary} weight="duotone" />
              <Text style={styles.cardTitle}>{s.title}</Text>
              <Text style={styles.cardText}>{s.text}</Text>
            </View>
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

      <View style={styles.section}>
        <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Ils ont vendu avec {SITE_NAME}</Text></View>
        <View style={[styles.cards, isTablet && { flexDirection: "row" }]}>
          {TESTIMONIALS.map((t) => (
            <View key={t.name} style={styles.quoteCard} testID="landing-testimonial">
              <View style={{ flexDirection: "row", gap: 2 }}>{[0, 1, 2, 3, 4].map((i) => <StarIcon key={i} size={16} color={colors.warning} weight="fill" />)}</View>
              <Text style={styles.quote}>« {t.text} »</Text>
              <Text style={styles.quoteAuthor}>{t.name} · {t.place}</Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.ctaBlock} testID="landing-cta">
        <Text style={styles.ctaTitle}>Prêt à connaître la valeur de votre bien ?</Text>
        <Text style={styles.ctaText}>Estimation gratuite en 2 minutes, puis créez votre compte pour sauvegarder le bien et préparer la vente — sur le site comme dans l’application mobile.</Text>
        <View style={[styles.ctaRow, isTablet && { flexDirection: "row" }]}>
          <PrimaryButton title="Estimer gratuitement" onPress={() => router.navigate("/estimation-maison")} testID="landing-cta-estimate" />
          <PrimaryButton title="Créer mon compte" variant="secondary" onPress={() => router.navigate("/sign-up")} testID="landing-cta-signup" />
        </View>
        <Link href="/prix-immobilier" asChild>
          <Pressable accessibilityRole="link"><Text style={styles.link}>Voir les prix immobiliers par commune →</Text></Pressable>
        </Link>
      </View>
    </PublicPage>
  );
}

const useStyles = makeStyles((colors) => ({
  hero: { gap: spacing.xl, paddingTop: spacing.lg, alignItems: "center" },
  heroTop: { width: "100%", gap: spacing.xl, alignItems: "center" },
  heroText: { width: "100%", gap: spacing.md, alignItems: "center" },
  heroImage: { width: "100%", aspectRatio: 1.6 },
  heroForm: { width: "100%" },
  sectionLead: { fontFamily: fonts.regular, fontSize: 16, lineHeight: 24, color: colors.onSurfaceTertiary, maxWidth: 760 },
  dataWrap: { gap: spacing.xl },
  mapImage: { width: "100%", aspectRatio: 1.6, borderRadius: radius.lg, backgroundColor: colors.surfaceSecondary },
  dataList: { gap: spacing.md },
  dataRow: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  dataNum: { width: 28, height: 28, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center", marginTop: 2 },
  dataNumText: { fontFamily: fonts.bold, fontSize: 13, color: colors.onBrandTertiary },
  dataTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface },
  kicker: { fontFamily: fonts.semibold, fontSize: 13, letterSpacing: 1.2, textTransform: "uppercase", color: colors.brandPrimary, textAlign: "center" },
  h1: { fontFamily: fonts.extrabold, fontSize: 36, lineHeight: 44, color: colors.onSurface, textAlign: "center" },
  lead: { fontFamily: fonts.regular, fontSize: 17, lineHeight: 26, color: colors.onSurfaceTertiary, textAlign: "center" },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, justifyContent: "center" },
  badge: { backgroundColor: colors.brandTertiary, borderRadius: radius.pill, paddingHorizontal: spacing.md, minHeight: 32, justifyContent: "center" },
  badgeText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  section: { gap: spacing.md },
  h2Row: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h2: { fontFamily: fonts.extrabold, fontSize: 26, lineHeight: 34, color: colors.onSurface, flexShrink: 1 },
  cards: { flexDirection: "column", gap: spacing.md },
  stepCard: { flex: 1, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
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
