import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircleIcon, HandshakeIcon } from "phosphor-react-native";
import { ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PremiumGate, usePackUnlocked } from "@/src/components/PremiumGate";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const INTRO =
  "Une visite est avant tout un moment d’échange entre vous, propriétaire, et les personnes intéressées par votre maison. L’objectif est de leur permettre de découvrir les lieux sereinement et de se projeter dans leur futur chez eux.";

const TIPS: { title: string; text: string }[] = [
  { title: "Préparez votre maison", text: "Rangez, nettoyez et aérez les pièces afin de présenter un intérieur agréable et accueillant." },
  { title: "Faites entrer la lumière", text: "Ouvrez les volets et les rideaux pour profiter au maximum de la lumière naturelle." },
  { title: "Présentez les espaces simplement", text: "Laissez les visiteurs circuler librement et prendre le temps de regarder chaque pièce." },
  {
    title: "Soyez disponible",
    text: "Répondez aux questions, notamment concernant les travaux réalisés, les équipements, les consommations, les charges ou encore le voisinage.",
  },
  {
    title: "Restez honnête et transparent",
    text: "Sur les éventuels travaux à prévoir ou les petits défauts du bien. Cette transparence contribue à instaurer un climat de confiance.",
  },
  { title: "Évitez de trop intervenir", text: "Laissez les visiteurs découvrir la maison à leur rythme et échanger entre eux." },
  {
    title: "Préparez les documents utiles",
    text: "Diagnostics, factures de travaux, taxe foncière, plans, informations sur les équipements, etc. Votre dossier de vente les rassemble déjà.",
  },
  { title: "Mettez de côté les objets personnels ou de valeur", text: "Avant la visite, rangez ce qui ne doit pas rester à la vue des visiteurs." },
];

const OUTRO =
  "Enfin, gardez à l’esprit qu’une visite réussie ne consiste pas à convaincre à tout prix. Il s’agit surtout de permettre aux visiteurs de découvrir votre maison dans les meilleures conditions et de se faire leur propre opinion. Un échange naturel, sincère et convivial sera souvent votre meilleur atout.";

/** Pack premium — « Conseils pour les visites ». */
export default function VisitTipsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const pack = usePackUnlocked(id);

  return (
    <View style={[styles.screen, { paddingTop: insets.top }]} testID="visits-screen">
      <ScreenHeader title="Conseils pour les visites" subtitle="Pack premium · réussir vos visites" onBack={() => router.back()} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xxl }]}>
        {!pack.loading && !pack.unlocked ? (
          <PremiumGate propertyId={id!} feature="les conseils pour vos visites" testID="visits-premium-gate" />
        ) : (
          <>
            <View style={styles.intro} testID="visits-intro">
              <HandshakeIcon size={26} color={colors.brandPrimary} weight="duotone" />
              <Text style={styles.h2}>Quelques conseils pour votre visite</Text>
              <Text style={styles.p}>{INTRO}</Text>
            </View>
            {TIPS.map((t, i) => (
              <View key={t.title} style={styles.tip} testID={`visit-tip-${i}`}>
                <View style={styles.badge}>
                  <CheckCircleIcon size={18} color={colors.onBrandPrimary} weight="fill" />
                </View>
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={styles.tipTitle}>{t.title}</Text>
                  <Text style={styles.p}>{t.text}</Text>
                </View>
              </View>
            ))}
            <View style={styles.outro} testID="visits-outro">
              <Text style={styles.outroText}>{OUTRO}</Text>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.md },
  intro: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.sm },
  h2: { fontFamily: fonts.bold, fontSize: 20, lineHeight: 26, color: colors.onSurface },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceTertiary },
  tip: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg },
  badge: { width: 32, height: 32, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  tipTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary },
  outro: { backgroundColor: colors.brandTertiary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.brandSecondary, padding: spacing.lg },
  outroText: { fontFamily: fonts.medium, fontSize: 14, lineHeight: 21, color: colors.onBrandTertiary },
}));
