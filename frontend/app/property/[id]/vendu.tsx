import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CaretRightIcon, CheckCircleIcon, FolderOpenIcon } from "phosphor-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { ShareReportButton } from "@/src/components/ShareReportButton";
import { StepTabs } from "@/src/components/StepTabs";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Étape 3 — Vendu : dossier de vente et documents à remettre. */
export default function SoldStepScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();

  const { data } = useQuery({ queryKey: ["property", id], queryFn: () => api.getProperty(id!), enabled: !!id });
  const steps = useQuery({ queryKey: ["next-steps"], queryFn: api.nextSteps });
  const dossier = steps.data?.properties.find((p) => p.property_id === id)?.steps.find((s) => s.key === "dossier");

  return (
    <View style={styles.screen} testID="sold-step-screen">
      <ScreenHeader title="Étape 3 · Vendu" subtitle={data?.address_label} onBack={() => (router.canGoBack() ? router.back() : router.replace(`/property/${id}/vente`))} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]} showsVerticalScrollIndicator={false}>
        <StepTabs propertyId={id!} current={2} />

        <View style={styles.intro} testID="step-3-header">
          <Text style={styles.introTitle}>Signez sereinement</Text>
          <Text style={styles.introText}>Rassemblez les documents et diagnostics obligatoires : votre dossier de vente complet est prêt à être remis au notaire et à l’acheteur.</Text>
        </View>

        <Animated.View entering={FadeInDown.duration(320)}>
          <Pressable testID="dossier-button" accessibilityRole="button" onPress={() => router.push(`/property/${id}/dossier`)} style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}>
            <FolderOpenIcon size={20} color={colors.onBrandTertiary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.linkLabel}>Dossier de vente (documents & diagnostics)</Text>
              {dossier ? <Text style={styles.linkSubMuted} testID="dossier-status">{dossier.done ? "Dossier complet" : dossier.label} · {dossier.detail}</Text> : null}
            </View>
            {dossier?.done ? <CheckCircleIcon size={20} color={colors.success} weight="fill" /> : <CaretRightIcon size={18} color={colors.onBrandTertiary} />}
          </Pressable>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(80).duration(320)} style={styles.card} testID="final-report-card">
          <Text style={styles.h3}>Rapport complet PDF</Text>
          <Text style={styles.p}>Estimation détaillée, analyse de l’environnement, photos retouchées et annonce : un document unique à partager avec vos interlocuteurs.</Text>
          <ShareReportButton propertyId={id!} label="Partager le rapport complet PDF" />
          <Text style={styles.hint}>Les photos retouchées par IA sont signalées comme non contractuelles.</Text>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(160).duration(320)} style={styles.outro} testID="sold-outro">
          <CheckCircleIcon size={22} color={colors.onBrandTertiary} weight="fill" />
          <Text style={styles.outroText}>Une fois le dossier complet, exportez-le pour le notaire depuis l’écran « Dossier de vente ». Félicitations pour votre vente !</Text>
        </Animated.View>
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
  linkRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg, minHeight: 56 },
  linkLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  linkSubMuted: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandTertiary, opacity: 0.8, marginTop: 2 },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  outro: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.brandTertiary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.brandSecondary, padding: spacing.lg },
  outroText: { flex: 1, fontFamily: fonts.medium, fontSize: 14, lineHeight: 21, color: colors.onBrandTertiary },
}));
