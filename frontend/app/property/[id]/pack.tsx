import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { CreditCardIcon, FileTextIcon, ImagesIcon, LockOpenIcon, PencilLineIcon, SparkleIcon, WarningIcon } from "phosphor-react-native";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LISTING_STYLES, ListingStyle, api } from "@/src/api";
import { PackPreview } from "@/src/components/PackPreview";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { ShareReportButton } from "@/src/components/ShareReportButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const INCLUDED = [
  { Icon: PencilLineIcon, text: "Annonce rédigée par l’IA (style au choix), titre, accroche et points forts" },
  { Icon: SparkleIcon, text: "Retouches photo IA illimitées pour ce bien, original toujours conservé" },
  { Icon: FileTextIcon, text: "Lecture automatique de vos documents (diagnostics, titre, taxe foncière) par l’IA" },
  { Icon: ImagesIcon, text: "PDF d’annonce premium avec photos retouchées en pleine page, régénérable à volonté" },
];

export default function PackScreen() {
  const { id, status: returnStatus } = useLocalSearchParams<{ id: string; status?: string; order_id?: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [style, setStyle] = useState<ListingStyle>("sobre");
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const pollCount = useRef(0);

  const pack = useQuery({
    queryKey: ["pack", id],
    queryFn: () => api.packStatus(id!),
    enabled: !!id,
    refetchInterval: (q) => (polling && !q.state.data?.unlocked ? 2500 : false),
  });

  useEffect(() => {
    if (returnStatus === "success" && !pack.data?.unlocked) setPolling(true);
  }, [returnStatus, pack.data?.unlocked]);

  useEffect(() => {
    if (!polling) return;
    if (pack.data?.unlocked) {
      setPolling(false);
      queryClient.invalidateQueries({ queryKey: ["next-steps"] });
      return;
    }
    pollCount.current += 1;
    if (pollCount.current > 48) {
      setPolling(false);
      setError("Paiement non confirmé pour le moment. Si vous avez payé, revenez dans quelques instants : le déblocage est automatique.");
    }
  }, [pack.dataUpdatedAt, pack.data?.unlocked, polling, queryClient]);

  const checkout = useMutation({
    mutationFn: () => {
      const origin = Platform.OS === "web" && typeof window !== "undefined" ? window.location.origin : process.env.EXPO_PUBLIC_BACKEND_URL!;
      return api.packCheckout(id!, `${origin}/property/${id}/pack`);
    },
    onMutate: () => setError(null),
    onSuccess: async ({ checkout_url }) => {
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.location.assign(checkout_url);
        return;
      }
      pollCount.current = 0;
      setPolling(true);
      await WebBrowser.openBrowserAsync(checkout_url);
    },
    onError: (e: Error) => setError(e.message),
  });

  const d = pack.data;

  return (
    <View style={styles.screen} testID="pack-screen">
      <ScreenHeader title="Pack premium" subtitle="Tous les outils IA · 49 € par bien" onBack={() => (router.canGoBack() ? router.back() : router.replace(`/property/${id}`))} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        {pack.isLoading || !d ? (
          <ActivityIndicator color={colors.brandPrimary} />
        ) : d.unlocked ? (
          <>
            <View style={styles.unlockedCard} testID="pack-unlocked">
              <LockOpenIcon size={22} color={colors.success} weight="fill" />
              <View style={{ flex: 1 }}>
                <Text style={styles.unlockedTitle}>Pack débloqué pour ce bien</Text>
                <Text style={styles.p}>Annonce IA, retouches photo illimitées, lecture des documents et PDF premium débloqués.</Text>
                {d.last_order?.status === "paid" && d.last_order.customer_email ? (
                  <Text style={styles.hint} testID="pack-receipt">
                    {d.last_order.receipt_sent ? "Reçu envoyé à " : "Reçu en cours d’envoi à "}
                    {d.last_order.customer_email}
                  </Text>
                ) : null}
              </View>
            </View>
            <View style={styles.card}>
              <Text style={styles.h3}>Générer le PDF de l’annonce</Text>
              <Text style={styles.p}>
                {d.listings > 0
                  ? "Le PDF reprend votre dernière annonce IA. Pour changer de style, régénérez-la depuis « Rédiger l’annonce »."
                  : "Aucune annonce encore rédigée : elle sera générée automatiquement dans le style choisi."}
              </Text>
              {d.listings === 0 ? (
                <View style={styles.chips}>
                  {LISTING_STYLES.map((s) => (
                    <Pressable key={s.value} testID={`pack-style-${s.value}`} accessibilityRole="button" onPress={() => setStyle(s.value)}
                      style={[styles.chip, style === s.value && styles.chipActive]}>
                      <Text style={[styles.chipLabel, style === s.value && styles.chipLabelActive]}>{s.label}</Text>
                    </Pressable>
                  ))}
                </View>
              ) : null}
              <Text style={styles.hint}>
                {d.photos} photo{d.photos > 1 ? "s" : ""} · {d.retouches_used} retouchée{d.retouches_used > 1 ? "s" : ""}. Les visuels retouchés portent la mention « non contractuel ».
              </Text>
              <ShareReportButton propertyId={id!} url={api.packPdfUrl(id!, style)} label="Générer et partager le PDF"
                fileName={`achetesmamaison-annonce-${id!.slice(-6)}.pdf`} dialogTitle="Partager l’annonce premium" testID="pack-pdf-button" />
              <View style={styles.row}>
                <PrimaryButton title="Photos & retouches" variant="ghost" onPress={() => router.push(`/property/${id}/photos`)} testID="pack-photos-button" style={{ flex: 1 }} />
                <PrimaryButton title="Rédiger l’annonce" variant="ghost" onPress={() => router.push(`/property/${id}/listing`)} testID="pack-listing-button" style={{ flex: 1 }} />
              </View>
            </View>
          </>
        ) : (
          <>
            <View style={styles.priceCard} testID="pack-offer">
              <Text style={styles.priceKicker}>Paiement unique · ce bien</Text>
              <Text style={styles.price}>49 €</Text>
              <Text style={styles.priceSub}>TTC · carte bancaire via Stripe · sans abonnement</Text>
              {d.mode === "test" ? (
                <View style={styles.testBadge} testID="pack-test-mode">
                  <Text style={styles.testBadgeText}>Mode test Stripe — aucun débit réel</Text>
                </View>
              ) : null}
            </View>
            <View style={styles.card}>
              <Text style={styles.h3}>Ce que comprend le pack</Text>
              {INCLUDED.map((it, i) => (
                <View key={i} style={styles.incRow}>
                  <it.Icon size={18} color={colors.brandPrimary} weight="duotone" />
                  <Text style={styles.p}>{it.text}</Text>
                </View>
              ))}
              <Text style={styles.hint}>
                Restent gratuits : l’estimation détaillée, le prix cible, la checklist du dossier de vente (saisie manuelle) et l’export notaire.
              </Text>
            </View>
            <PackPreview />
            {polling ? (
              <View style={styles.warn} testID="pack-polling">
                <ActivityIndicator color={colors.warning} />
                <Text style={styles.warnText}>Vérification du paiement en cours…</Text>
              </View>
            ) : null}
            {returnStatus === "cancelled" && !polling ? (
              <View style={styles.warn} testID="pack-cancelled">
                <WarningIcon size={18} color={colors.warning} weight="fill" />
                <Text style={styles.warnText}>Paiement annulé. Aucun montant n’a été débité.</Text>
              </View>
            ) : null}
            {error ? (
              <View style={styles.warn} testID="pack-error">
                <WarningIcon size={18} color={colors.error} weight="fill" />
                <Text style={[styles.warnText, { color: colors.error }]}>{error}</Text>
              </View>
            ) : null}
            {!d.payments_available ? (
              <Text style={styles.hint} testID="pack-unavailable">Paiement temporairement indisponible.</Text>
            ) : (
              <Pressable testID="pack-pay-button" accessibilityRole="button" disabled={checkout.isPending || polling}
                onPress={() => checkout.mutate()} style={({ pressed }) => [styles.payBtn, (pressed || checkout.isPending) && { opacity: 0.85 }]}>
                {checkout.isPending ? <ActivityIndicator color={colors.onBrandPrimary} /> : <CreditCardIcon size={20} color={colors.onBrandPrimary} weight="fill" />}
                <Text style={styles.payLabel}>Payer 49 € et débloquer</Text>
              </Pressable>
            )}
            <Text style={styles.hint}>
              Vous serez redirigé vers la page de paiement sécurisée Stripe, puis ramené automatiquement ici. Le déblocage est
              confirmé côté serveur après validation du paiement.{" "}
              <Text style={styles.link} onPress={() => Linking.openURL("https://stripe.com/fr/privacy")}>Confidentialité Stripe</Text>
            </Text>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  p: { flex: 1, fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  link: { fontFamily: fonts.medium, color: colors.brandPrimary },
  priceCard: { backgroundColor: colors.brandPrimary, borderRadius: radius.lg, padding: spacing.xl, gap: 4, alignItems: "center" },
  priceKicker: { fontFamily: fonts.medium, fontSize: 12, color: colors.onBrandPrimary, textTransform: "uppercase", letterSpacing: 0.8, opacity: 0.85 },
  price: { fontFamily: fonts.bold, fontSize: 48, lineHeight: 56, color: colors.onBrandPrimary },
  priceSub: { fontFamily: fonts.regular, fontSize: 13, color: colors.onBrandPrimary, opacity: 0.85 },
  testBadge: { marginTop: spacing.sm, paddingHorizontal: spacing.md, paddingVertical: 4, borderRadius: radius.pill, backgroundColor: colors.warningSoft },
  testBadgeText: { fontFamily: fonts.medium, fontSize: 11, color: colors.warning },
  incRow: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "center", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  payBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 56, borderRadius: radius.md, backgroundColor: colors.brandPrimary },
  payLabel: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onBrandPrimary },
  unlockedCard: { flexDirection: "row", gap: spacing.md, alignItems: "center", backgroundColor: colors.successSoft, borderRadius: radius.lg, padding: spacing.lg },
  unlockedTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.success },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { height: 36, paddingHorizontal: spacing.lg, borderRadius: radius.pill, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, justifyContent: "center" },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipLabel: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceSecondary },
  chipLabelActive: { color: colors.onBrandPrimary },
  row: { flexDirection: "row", gap: spacing.md },
}));
