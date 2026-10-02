import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  ArrowsOutIcon, CaretLeftIcon, CaretRightIcon, ChartBarIcon, FolderOpenIcon, HandshakeIcon, ImagesIcon, ListBulletsIcon, PencilLineIcon,
  RulerIcon, SparkleIcon, TargetIcon, TrashIcon, TreeIcon, WarningIcon,
} from "phosphor-react-native";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { TYPE_LABELS, api, formatEuro, formatInt, formatK, formatPct } from "@/src/api";
import { CompletionBadge } from "@/src/components/CompletionBadge";
import { FinalEstimateCard } from "@/src/components/FinalEstimateCard";
import { HedonicCard } from "@/src/components/HedonicCard";
import { MarketSignalCard } from "@/src/components/MarketSignalCard";
import { MlCard } from "@/src/components/MlCard";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ShareReportButton } from "@/src/components/ShareReportButton";
import { RisksCard } from "@/src/components/RisksCard";
import { TargetPriceCard } from "@/src/components/TargetPriceCard";
import { TrendCard } from "@/src/components/TrendCard";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1649083048770-82e8ffd80431?crop=entropy&cs=srgb&fm=jpg&q=80&w=1000";

export default function PropertyDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["property", id],
    queryFn: () => api.getProperty(id!),
    enabled: !!id,
  });

  const reestimate = useMutation({
    mutationFn: () => api.reestimate(id!),
    onSuccess: (p) => {
      queryClient.setQueryData(["property", id], p);
      queryClient.invalidateQueries({ queryKey: ["properties"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => api.deleteProperty(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      router.replace("/");
    },
  });

  const est = data?.estimation ?? null;

  if (isLoading) {
    return (
      <View style={styles.screen} testID="property-loading">
        <View style={[styles.heroSkeleton, { paddingTop: insets.top }]} />
        <View style={styles.body}>
          <View style={styles.skelRow}>
            <View style={styles.skelCard} />
            <View style={styles.skelCard} />
          </View>
          <View style={styles.skelBlock} />
          <View style={styles.skelBlock} />
        </View>
      </View>
    );
  }

  if (isError || !data) {
    return (
      <View style={[styles.screen, styles.centered, { paddingTop: insets.top }]}>
        <Text style={styles.h3}>Bien introuvable</Text>
        <PrimaryButton title="Réessayer" onPress={() => refetch()} testID="property-retry-button" variant="secondary" />
        <PrimaryButton title="Retour" onPress={() => router.replace("/")} testID="property-back-home-button" variant="ghost" />
      </View>
    );
  }

  return (
    <View style={styles.screen} testID="property-detail-screen">
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + spacing.xl }} showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View style={styles.hero}>
          <Image source={{ uri: HERO_IMAGE }} style={styles.heroImage} contentFit="cover" blurRadius={2} transition={400} />
          <LinearGradient colors={[colors.scrimTop, colors.scrimBottom]} style={styles.heroImage} />
          <View style={[styles.heroContent, { paddingTop: insets.top + spacing.sm }]}>
            <Pressable
              testID="header-back-button"
              accessibilityRole="button"
              accessibilityLabel="Retour"
              onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}
              style={styles.heroBack}
            >
              <CaretLeftIcon size={22} color={colors.onHero} weight="bold" />
            </Pressable>
            <View style={{ flex: 1 }} />
            <Text style={styles.heroAddress} numberOfLines={2} testID="property-address">
              {data.address_label}
            </Text>
            <Text style={styles.heroMeta}>
              {TYPE_LABELS[data.property_type]} · {data.surface} m² · {data.rooms} pièces · {data.bedrooms} ch.
            </Text>
            {est ? (
              <>
                <Text style={styles.heroRangeLabel}>Valeur estimée</Text>
                <Text style={styles.heroCentral} testID="estimation-value">
                  {formatEuro(est.value)}
                </Text>
                <Text style={styles.heroRange} testID="estimation-range">
                  Fourchette {formatK(est.low)} – {formatK(est.high)}
                </Text>
              </>
            ) : null}
          </View>
        </View>

        {est ? (
          <View style={styles.body}>
            <View style={[styles.stepHeader, { marginTop: 0 }]} testID="step-1-header">
              <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>1</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stepTitle}>Estimation</Text>
                <Text style={styles.stepSub}>Votre bien au juste prix, expliqué critère par critère.</Text>
              </View>
            </View>
            {est.insufficient_data ? (
              <Animated.View entering={FadeInDown.duration(300)} style={styles.warnBanner} testID="insufficient-data-banner">
                <WarningIcon size={20} color={colors.warning} weight="fill" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.warnTitle}>Données insuffisantes — fourchette élargie</Text>
                  <Text style={styles.warnText}>
                    Très peu de ventes comparables dans la zone. L’estimation s’appuie sur toutes les ventes du secteur et
                    doit être considérée avec prudence.
                  </Text>
                </View>
              </Animated.View>
            ) : null}

            {/* Metrics */}
            <Animated.View entering={FadeInDown.delay(60).duration(320)} style={styles.metricRow}>
              <View style={styles.metric} testID="metric-price-m2">
                <RulerIcon size={18} color={colors.brandPrimary} />
                <Text style={styles.metricValue}>{formatInt(est.price_m2)} €/m²</Text>
                <Text style={styles.metricLabel}>Prix estimé</Text>
              </View>
              <View style={styles.metric} testID="metric-radius">
                <TargetIcon size={18} color={colors.brandPrimary} />
                <Text style={styles.metricValue} numberOfLines={1} adjustsFontSizeToFit>{est.confidence.radius_label}</Text>
                <Text style={styles.metricLabel}>Périmètre retenu</Text>
              </View>
            </Animated.View>
            <Animated.View entering={FadeInDown.delay(120).duration(320)} style={styles.metricRow}>
              <View style={styles.metric} testID="metric-count">
                <ListBulletsIcon size={18} color={colors.brandPrimary} />
                <Text style={styles.metricValue}>{est.confidence.n_comparables}</Text>
                <Text style={styles.metricLabel}>Ventes comparables</Text>
              </View>
              <View style={styles.metric} testID="metric-age">
                <ArrowsOutIcon size={18} color={colors.brandPrimary} />
                <Text style={styles.metricValue}>±{est.confidence.dispersion_pct.toFixed(0).replace(".", ",")} %</Text>
                <Text style={styles.metricLabel}>Dispersion des prix/m²</Text>
              </View>
            </Animated.View>

            {/* Notes */}
            {est.notes.length > 0 ? (
              <View style={styles.notes} testID="estimation-notes">
                {est.notes.map((n, i) => (
                  <Text key={i} style={styles.noteText}>• {n}</Text>
                ))}
              </View>
            ) : null}

            {/* Adjustments */}
            <Animated.View entering={FadeInDown.delay(240).duration(320)} style={styles.card} testID="adjustments-card">
              <Text style={styles.h3}>Comment est calculée la fourchette ?</Text>
              <View style={styles.lineRow}>
                <Text style={styles.lineLabel}>Prix/m² médian pondéré des comparables (ramené à {data.surface} m²)</Text>
                <Text style={styles.lineValue}>{formatInt(est.base_price_m2)} €/m²</Text>
              </View>
              <View style={styles.lineRow}>
                <Text style={styles.lineLabel}>× Surface {data.surface} m²</Text>
                <Text style={styles.lineValue}>{formatK(est.base_price_m2 * data.surface)}</Text>
              </View>
              {est.adjustments.map((a) => (
                <View key={a.key} style={styles.lineRow}>
                  <Text style={styles.lineLabel} numberOfLines={2}>{a.label}</Text>
                  <Text style={[styles.lineValue, a.amount > 0 ? { color: colors.success } : a.amount < 0 ? { color: colors.error } : null]}>
                    {a.amount === 0 ? "—" : `${formatPct(a.pct, 1)} (${a.amount > 0 ? "+" : "−"}${formatK(Math.abs(a.amount))})`}
                  </Text>
                </View>
              ))}
              <View style={[styles.lineRow, styles.lineTotal]}>
                <Text style={styles.lineLabelStrong}>Valeur centrale</Text>
                <Text style={styles.lineValueStrong} testID="estimation-central-recap">{formatEuro(est.value)}</Text>
              </View>
              <Text style={styles.detailHint}>
                Les prix/m² des ventes sont d’abord ramenés à votre surface (le prix/m² baisse quand la taille
                augmente), puis pondérés par récence, distance, similarité de surface et taille de commune. Le rayon
                s’élargit jusqu’à 10 km, en ne retenant hors de votre commune que des communes de taille comparable,
                tant que cela rend la valeur centrale plus robuste. La fourchette encadre la valeur centrale
                (incertitude de la médiane + spécificités non renseignées) et non l’écart entre ventes individuelles,
                indiqué par la dispersion. Elle est plafonnée à ±15 % (±20 % lorsque les ventes comparables sont peu
                nombreuses ou dispersées).
              </Text>
            </Animated.View>

            {/* Market */}
            <Animated.View entering={FadeInDown.delay(300).duration(320)} style={styles.card} testID="market-card">
              <View style={styles.cardHeader}>
                <Text style={styles.h3}>Marché local ({TYPE_LABELS[data.property_type].toLowerCase()}s, 3 ans)</Text>
                <ChartBarIcon size={18} color={colors.muted} />
              </View>
              {est.market.map((m) => (
                <View key={m.label} style={styles.lineRow}>
                  <View>
                    <Text style={styles.lineLabel}>{m.label}</Text>
                    <Text style={styles.detailHint}>{m.count} vente{m.count > 1 ? "s" : ""}</Text>
                  </View>
                  <Text style={styles.lineValue}>{m.median_pm2 ? `${formatInt(m.median_pm2)} €/m²` : "—"}</Text>
                </View>
              ))}
            </Animated.View>

            {/* Hedonic — Phase 2 */}
            {est.hedonic ? (
              <Animated.View entering={FadeInDown.delay(330).duration(320)}>
                <HedonicCard hedonic={est.hedonic} comparablesValue={est.value} />
              </Animated.View>
            ) : (
              <View style={styles.notes} testID="hedonic-missing">
                <Text style={styles.noteText}>
                  • Analyses « Pourquoi cette estimation ? », ML et pondération indisponibles pour cette estimation : appuyez sur « Recalculer » pour les obtenir.
                </Text>
              </View>
            )}

            {/* ML — Phase 3 */}
            {est.ml ? (
              <Animated.View entering={FadeInDown.delay(345).duration(320)}>
                <MlCard ml={est.ml} />
              </Animated.View>
            ) : null}

            {/* Blended final estimate */}
            {est.hedonic || est.market_estimate ? (
              <Animated.View entering={FadeInDown.delay(350).duration(320)}>
                <FinalEstimateCard estimation={est} />
              </Animated.View>
            ) : null}

            {/* Market trend */}
            <Animated.View entering={FadeInDown.delay(360).duration(320)}>
              <TrendCard propertyId={id!} typeLabel={TYPE_LABELS[data.property_type]} />
            </Animated.View>

            <Animated.View entering={FadeInDown.delay(380).duration(320)}>
              <MarketSignalCard propertyId={id!} />
            </Animated.View>

            <Animated.View entering={FadeInDown.delay(420).duration(320)}>
              <RisksCard propertyId={id!} />
            </Animated.View>

            {data.completion ? (
              <Animated.View entering={FadeInDown.delay(440).duration(320)}>
                <CompletionBadge variant="card" completion={data.completion} testID="completion-card" onPress={() => router.push(`/property/${id}/edit`)} />
              </Animated.View>
            ) : null}

            <Pressable
              testID="environment-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/environment`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <TreeIcon size={20} color={colors.onBrandTertiary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.linkLabel}>Environnement du bien</Text>
                <Text style={styles.linkSubMuted}>
                  {est.adjustments.some((a) => a.key.startsWith("env_"))
                    ? `Analyse intégrée à l’estimation (${formatPct(est.adjustments.filter((a) => a.key.startsWith("env_")).reduce((s, a) => s + a.pct, 0), 1)})`
                    : "Voisinage, nuisances, risques, urbanisme — affine l’estimation"}
                </Text>
              </View>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>

            <View style={styles.stepHeader} testID="step-2-header">
              <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>2</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stepTitle}>Mise en vente</Text>
                <Text style={styles.stepSub}>Commencez par fixer votre prix de vente, puis préparez l’annonce.</Text>
              </View>
            </View>
            <Animated.View entering={FadeInDown.delay(400).duration(320)}>
              <TargetPriceCard propertyId={id!} suggestedValue={est.value} estimation={est} />
            </Animated.View>

            <Pressable
              testID="photos-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/photos`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <ImagesIcon size={20} color={colors.onBrandTertiary} />
              <Text style={styles.linkLabel}>Photos & retouche IA</Text>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>

            <Pressable
              testID="write-listing-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/listing`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <PencilLineIcon size={20} color={colors.onBrandTertiary} />
              <Text style={styles.linkLabel}>Rédiger l’annonce avec l’IA</Text>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>
            <Pressable
              testID="visits-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/visites`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <HandshakeIcon size={20} color={colors.onBrandTertiary} />
              <Text style={styles.linkLabel}>Conseils pour les visites</Text>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>

            <Pressable
              testID="pack-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/pack`)}
              style={({ pressed }) => [styles.linkRow, styles.linkRowPremium, pressed && { opacity: 0.85 }]}
            >
              <SparkleIcon size={20} color={colors.onBrandPrimary} weight="fill" />
              <View style={{ flex: 1 }}>
                <Text style={[styles.linkLabel, { color: colors.onBrandPrimary }]}>Pack premium · 49 €</Text>
                <Text style={styles.linkSub}>Débloque tous les outils IA : annonce, retouches photo, lecture des documents, PDF</Text>
              </View>
              <CaretRightIcon size={18} color={colors.onBrandPrimary} />
            </Pressable>

            <View style={styles.stepHeader} testID="step-3-header">
              <View style={styles.stepBadge}><Text style={styles.stepBadgeText}>3</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stepTitle}>Vendu</Text>
                <Text style={styles.stepSub}>Le dossier de vente complet pour signer sereinement.</Text>
              </View>
            </View>
            <Pressable
              testID="dossier-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/dossier`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <FolderOpenIcon size={20} color={colors.onBrandTertiary} />
              <Text style={styles.linkLabel}>Dossier de vente (documents & diagnostics)</Text>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>

            <Pressable
              testID="view-comparables-button"
              accessibilityRole="button"
              onPress={() => router.push(`/property/${id}/comparables`)}
              style={({ pressed }) => [styles.linkRow, pressed && { opacity: 0.85 }]}
            >
              <ListBulletsIcon size={20} color={colors.onBrandTertiary} />
              <Text style={styles.linkLabel}>Voir les {est.comparables.length} ventes comparables</Text>
              <CaretRightIcon size={18} color={colors.onBrandTertiary} />
            </Pressable>

            <View style={styles.actions}>
              <ShareReportButton propertyId={id!} />
              <Text style={styles.detailHint} testID="report-photos-hint">
                Le rapport PDF inclut vos photos (versions retouchées par IA si disponibles, signalées comme non contractuelles).
              </Text>
              <PrimaryButton
                title="Modifier les caractéristiques"
                variant="secondary"
                onPress={() => router.push(`/property/${id}/edit`)}
                testID="edit-property-button"
              />
              <PrimaryButton
                title="Recalculer l’estimation"
                variant="secondary"
                onPress={() => reestimate.mutate()}
                loading={reestimate.isPending}
                testID="reestimate-button"
              />
              {confirmDelete ? (
                <View style={styles.confirmRow} testID="delete-confirm">
                  <PrimaryButton title="Annuler" variant="ghost" onPress={() => setConfirmDelete(false)} testID="delete-cancel-button" style={{ flex: 1 }} />
                  <PrimaryButton title="Confirmer" variant="danger" onPress={() => remove.mutate()} loading={remove.isPending} testID="delete-confirm-button" style={{ flex: 1 }} />
                </View>
              ) : (
                <Pressable testID="delete-button" accessibilityRole="button" onPress={() => setConfirmDelete(true)} style={styles.deleteRow}>
                  <TrashIcon size={18} color={colors.error} />
                  <Text style={styles.deleteLabel}>Supprimer ce bien</Text>
                </Pressable>
              )}
            </View>

            <Text style={styles.disclaimer}>
              Estimation indicative fondée sur les ventes réelles enregistrées à proximité et la Base Adresse
              Nationale. Elle ne constitue pas une expertise et ne tient pas compte des spécificités non renseignées.
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  centered: { alignItems: "stretch", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  hero: { height: 400, backgroundColor: colors.surfaceInverse },
  heroImage: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  heroSkeleton: { height: 400, backgroundColor: colors.skeleton },
  heroContent: { flex: 1, padding: spacing.lg, paddingBottom: spacing.xl },
  heroBack: { width: 44, height: 44, borderRadius: radius.pill, backgroundColor: colors.glassFill, alignItems: "center", justifyContent: "center" },
  heroAddress: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onHero },
  heroMeta: { fontFamily: fonts.regular, fontSize: 13, color: colors.onHeroMuted, marginTop: 4, marginBottom: spacing.lg },
  heroRangeLabel: { fontFamily: fonts.medium, fontSize: 13, color: colors.onHeroMuted, textTransform: "uppercase", letterSpacing: 0.8 },
  heroCentral: { fontFamily: fonts.bold, fontSize: 44, lineHeight: 52, color: colors.onHero, marginTop: 4, fontVariant: ["tabular-nums"] },
  heroRange: { fontFamily: fonts.medium, fontSize: 15, color: colors.onHeroMuted, marginTop: 4, fontVariant: ["tabular-nums"] },
  body: { padding: spacing.lg, gap: spacing.lg },
  skelRow: { flexDirection: "row", gap: spacing.md },
  skelCard: { flex: 1, height: 96, borderRadius: radius.md, backgroundColor: colors.skeleton },
  skelBlock: { height: 180, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  warnBanner: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.warning },
  warnText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.warning, marginTop: 2 },
  metricRow: { flexDirection: "row", gap: spacing.md },
  metric: { flex: 1, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: 6 },
  metricValue: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  metricLabel: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  notes: { gap: 6, paddingHorizontal: spacing.xs },
  noteText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  cardHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.md },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flexShrink: 1 },
  detailHint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  lineRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md, paddingVertical: 4 },
  lineLabel: { flex: 1, fontFamily: fonts.regular, fontSize: 14, color: colors.onSurfaceTertiary },
  lineValue: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  stepHeader: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginTop: spacing.lg },
  stepBadge: { width: 32, height: 32, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  stepBadgeText: { fontFamily: fonts.bold, fontSize: 15, color: colors.onBrandPrimary },
  stepTitle: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurface },
  stepSub: { fontFamily: fonts.regular, fontSize: 13, color: colors.onSurfaceTertiary },
  lineTotal: { borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.md, marginTop: spacing.xs, backgroundColor: colors.brandTertiary, marginHorizontal: -spacing.md, paddingHorizontal: spacing.md, paddingBottom: spacing.md, borderRadius: radius.md },
  lineLabelStrong: { fontFamily: fonts.semibold, fontSize: 15, color: colors.brandPrimary },
  lineValueStrong: { fontFamily: fonts.bold, fontSize: 22, color: colors.brandPrimary, fontVariant: ["tabular-nums"] },
  linkRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg, minHeight: 56 },
  linkLabel: { flex: 1, fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  linkRowPremium: { backgroundColor: colors.brandPrimary },
  linkSub: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandPrimary, opacity: 0.85, marginTop: 2 },
  linkSubMuted: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandTertiary, opacity: 0.8, marginTop: 2 },
  actions: { gap: spacing.md, marginTop: spacing.sm },
  confirmRow: { flexDirection: "row", gap: spacing.md },
  deleteRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 48 },
  deleteLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.error },
  disclaimer: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted, textAlign: "center", paddingHorizontal: spacing.sm },
}));
