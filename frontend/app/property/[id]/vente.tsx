import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CaretRightIcon, HandshakeIcon, ImagesIcon, PencilLineIcon, SparkleIcon } from "phosphor-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { StepTabs } from "@/src/components/StepTabs";
import { TargetPriceCard } from "@/src/components/TargetPriceCard";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Étape 2 — Mise en vente : prix cible, photos, annonce, visites, pack. */
export default function SaleStepScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();

  const { data, isLoading } = useQuery({ queryKey: ["property", id], queryFn: () => api.getProperty(id!), enabled: !!id });
  const est = data?.estimation ?? null;

  const links: { testID: string; route: string; icon: typeof ImagesIcon; label: string; sub?: string }[] = [
    { testID: "photos-button", route: `/property/${id}/photos`, icon: ImagesIcon, label: "Photos & retouche IA", sub: "Importez vos photos, l’IA les met en valeur" },
    { testID: "write-listing-button", route: `/property/${id}/listing`, icon: PencilLineIcon, label: "Rédiger l’annonce avec l’IA", sub: "Texte prêt à publier, enrichi de l’environnement" },
    { testID: "visits-button", route: `/property/${id}/visites`, icon: HandshakeIcon, label: "Conseils pour les visites", sub: "Préparer et réussir chaque visite" },
  ];

  return (
    <View style={styles.screen} testID="sale-step-screen">
      <ScreenHeader title="Étape 2 · Mise en vente" subtitle={data?.address_label} onBack={() => (router.canGoBack() ? router.back() : router.replace(`/property/${id}`))} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]} showsVerticalScrollIndicator={false}>
        <StepTabs propertyId={id!} current={1} />

        <View style={styles.intro} testID="step-2-header">
          <Text style={styles.introTitle}>Mettez votre bien en vente</Text>
          <Text style={styles.introText}>Commencez par fixer votre prix de vente, puis préparez l’annonce : photos, texte et visites.</Text>
        </View>

        {isLoading ? (
          <View style={styles.skelBlock} />
        ) : est ? (
          <Animated.View entering={FadeInDown.duration(320)}>
            <TargetPriceCard propertyId={id!} suggestedValue={est.value} estimation={est} />
          </Animated.View>
        ) : (
          <View style={styles.notes} testID="target-missing">
            <Text style={styles.noteText}>• Estimation indisponible : revenez à l’étape 1 pour la recalculer avant de fixer votre prix.</Text>
          </View>
        )}

        {links.map((l, i) => (
          <Animated.View key={l.testID} entering={FadeInDown.delay(80 + i * 60).duration(320)}>
            <Pressable testID={l.testID} accessibilityRole="button" onPress={() => router.push(l.route as any)} style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}>
              <l.icon size={20} color={colors.onBrandTertiary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.linkLabel}>{l.label}</Text>
                {l.sub ? <Text style={styles.linkSubMuted}>{l.sub}</Text> : null}
              </View>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>
          </Animated.View>
        ))}

        <Animated.View entering={FadeInDown.delay(280).duration(320)}>
          <Pressable testID="pack-button" accessibilityRole="button" onPress={() => router.push(`/property/${id}/pack`)} style={({ pressed }) => [styles.linkRow, styles.linkRowPremium, pressed && { opacity: 0.85 }]}>
            <SparkleIcon size={20} color={colors.onBrandPrimary} weight="fill" />
            <View style={{ flex: 1 }}>
              <Text style={[styles.linkLabel, { color: colors.onBrandPrimary }]}>Pack premium · 49 €</Text>
              <Text style={styles.linkSub}>Débloque tous les outils IA : annonce, retouches photo, lecture des documents, PDF</Text>
            </View>
            <CaretRightIcon size={18} color={colors.onBrandPrimary} />
          </Pressable>
        </Animated.View>

        <View style={styles.actions}>
          <PrimaryButton title="Valider la mise en vente → Étape 3 : Vendu" onPress={() => router.navigate(`/property/${id}/vendu`)} testID="go-step-3-button" />
          <Text style={styles.hint}>Vous pourrez revenir à tout moment sur cette étape via les onglets.</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  intro: { gap: 4 },
  introTitle: { fontFamily: fonts.bold, fontSize: 20, color: colors.onSurface },
  introText: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  skelBlock: { height: 180, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  notes: { gap: 6, paddingHorizontal: spacing.xs },
  noteText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  linkRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg, minHeight: 56 },
  linkLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  linkRowPremium: { backgroundColor: colors.brandPrimary },
  linkSub: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandPrimary, opacity: 0.85, marginTop: 2 },
  linkSubMuted: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandTertiary, opacity: 0.8, marginTop: 2 },
  actions: { gap: spacing.sm, marginTop: spacing.sm },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted, textAlign: "center" },
}));
