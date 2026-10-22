import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { LockKeyIcon } from "phosphor-react-native";
import { useEffect, useRef, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PropertyIn, api, formatEuro, formatInt } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { PropertyWizard, WIZARD_STEPS } from "@/src/components/PropertyWizard";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { saveFreeDraft } from "@/src/freeDraft";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CTA_HEIGHT = 92;
const FREE_NEXT = [
  "Estimation enregistrée et recalculée automatiquement",
  "Dossier environnement (écoles, commerces, transports, risques, urbanisme)",
  "Ventes comparables détaillées et tendance du marché local",
];
const PREMIUM_NEXT = [
  "Étape 2 · Mise en vente : prix cible, photos et annonce par IA, conseils visites",
  "Étape 3 · Dossier de vente : diagnostics, documents, PDF pour le notaire",
];

/**
 * Estimation visiteur (sans compte) : même questionnaire et même moteur que l'application connectée ; le compte gratuit
 * n'est proposé qu'ensuite, pour enregistrer le bien (exigence App Store 5.1.1 : fonctions non liées au compte accessibles librement).
 */
export default function FreeEstimateScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [body, setBody] = useState<PropertyIn | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const estimate = useMutation({
    mutationFn: (b: PropertyIn) => api.estimatePreview(b),
    onSuccess: (est, b) => {
      setBody(b);
      saveFreeDraft(b, est);
    },
  });
  useEffect(() => {
    scrollRef.current?.scrollTo({ y: 0, animated: true });
  }, [step, estimate.data]);

  const back = () => {
    if (estimate.data) {
      estimate.reset();
      return;
    }
    if (step === 0) router.back();
    else setStep(step - 1);
  };

  const est = estimate.data;
  if (est && body) {
    const v = est.final ?? est;
    const shown = est.adjustments.filter((a) => Math.abs(a.pct) >= 0.1);
    return (
      <View style={styles.screen} testID="free-estimate-screen">
        <ScreenHeader title="Votre estimation" subtitle={body.address_label} onBack={back} />
        <ScrollView ref={scrollRef} contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}>
          <View style={styles.result} testID="free-result">
            <Text style={styles.resultLabel}>Valeur estimée</Text>
            <Text style={styles.resultValue} testID="free-result-value">{formatEuro(v.value)}</Text>
            <Text style={styles.resultRange}>
              Fourchette {formatEuro(v.low)} – {formatEuro(v.high)} · {formatInt(Math.round(v.value / body.surface / 10) * 10)} €/m²
            </Text>
            <Text style={styles.resultMeta}>
              {est.confidence.n_comparables} ventes comparables ({est.confidence.radius_label}) · {body.property_type === "maison" ? "Maison" : "Appartement"} {body.surface} m² · {body.rooms} pièces
            </Text>
          </View>
          {shown.length > 0 ? (
            <View style={styles.block} testID="free-adjustments">
              <Text style={styles.blockTitle}>Ajustements appliqués</Text>
              {shown.map((a) => (
                <View key={a.key} style={styles.adjRow}>
                  <Text style={styles.adjLabel} numberOfLines={2}>{a.label}</Text>
                  <Text style={[styles.adjPct, { color: a.pct >= 0 ? colors.success : colors.error }]}>
                    {a.pct > 0 ? "+" : ""}{a.pct.toFixed(1)} % · {a.amount > 0 ? "+" : ""}{formatEuro(a.amount)}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
          <View style={styles.lockBlock} testID="free-locked">
            <View style={styles.lockHeader}>
              <LockKeyIcon size={18} color={colors.brandPrimary} weight="fill" />
              <Text style={styles.blockTitle}>Inclus avec un compte gratuit</Text>
            </View>
            {FREE_NEXT.map((l) => <Text key={l} style={styles.lockItem}>• {l}</Text>)}
            <Text style={[styles.blockTitle, { marginTop: spacing.sm }]}>Pack premium · 49 € par bien, paiement unique</Text>
            {PREMIUM_NEXT.map((l) => <Text key={l} style={styles.lockItem}>• {l}</Text>)}
          </View>
          <Text style={styles.disclaimer}>
            Avis de valeur indicatif fondé sur les ventes réelles enregistrées et vos déclarations ; il ne constitue ni une expertise ni une garantie de prix de vente.
          </Text>
        </ScrollView>
        <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>
          <PrimaryButton title="Créer un compte gratuit et enregistrer" onPress={() => router.push("/sign-up")} testID="free-result-cta" />
          <Text style={styles.hint}>
            Déjà inscrit ? <Text style={styles.link} onPress={() => router.push("/sign-in")} testID="free-signin-link">Se connecter</Text> — l’estimation sera rattachée à votre compte.
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.screen} testID="free-estimate-screen">
      <ScreenHeader title="Estimation gratuite" subtitle={`Sans compte · Étape ${step + 1} sur ${WIZARD_STEPS.length} · ${WIZARD_STEPS[step]}`} onBack={back} />
      <View style={styles.progress}>
        {WIZARD_STEPS.map((s, i) => (
          <View key={s} style={[styles.progressSeg, i <= step && styles.progressSegActive]} />
        ))}
      </View>
      <PropertyWizard
        step={step}
        onStepChange={setStep}
        onSubmit={(b) => estimate.mutate(b)}
        submitLabel="Obtenir mon estimation"
        loading={estimate.isPending}
        errorMessage={estimate.isError ? (estimate.error as Error).message || "Estimation indisponible pour cette adresse." : null}
        renderLayout={(content, cta) => (
          <>
            <KeyboardAwareScrollView
              style={{ flex: 1 }}
              contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
              bottomOffset={CTA_HEIGHT + spacing.lg}
              keyboardShouldPersistTaps="handled"
            >
              {content}
            </KeyboardAwareScrollView>
            <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
              <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>{cta}</View>
            </KeyboardStickyView>
          </>
        )}
      />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  progress: { flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  progressSeg: { flex: 1, height: 4, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary },
  progressSegActive: { backgroundColor: colors.brandPrimary },
  content: { padding: spacing.lg, paddingTop: spacing.xl, gap: spacing.lg },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.sm, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider },
  result: { backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.xs },
  resultLabel: { fontFamily: fonts.semibold, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase", color: colors.onBrandTertiary },
  resultValue: { fontFamily: fonts.bold, fontSize: 40, color: colors.onBrandTertiary },
  resultRange: { fontFamily: fonts.semibold, fontSize: 15, lineHeight: 21, color: colors.onBrandTertiary },
  resultMeta: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onBrandTertiary },
  block: { gap: spacing.xs },
  blockTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurface },
  adjRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md, minHeight: 32, borderBottomWidth: 1, borderBottomColor: colors.divider },
  adjLabel: { flex: 1, fontFamily: fonts.regular, fontSize: 13, color: colors.onSurfaceSecondary },
  adjPct: { fontFamily: fonts.semibold, fontSize: 13 },
  lockBlock: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, padding: spacing.lg, gap: spacing.xs },
  lockHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  lockItem: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceSecondary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.onSurfaceTertiary, textAlign: "center" },
  link: { fontFamily: fonts.semibold, color: colors.brandPrimary },
  disclaimer: { fontFamily: fonts.regular, fontSize: 11, lineHeight: 16, color: colors.muted },
}));
