import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { ArrowLeftIcon, CheckIcon, EnvelopeSimpleIcon, LockKeyIcon } from "phosphor-react-native";
import { useEffect, useRef, useState } from "react";
import { Platform, Pressable, Text, TextInput, View } from "react-native";

import { Estimation, PropertyIn, api, formatEuro, formatInt } from "@/src/api";
import { useSession } from "@/src/auth";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { PropertyWizard, WIZARD_STEPS } from "@/src/components/PropertyWizard";
import { saveFreeDraft } from "@/src/freeDraft";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const FREE_NEXT = [
  "Estimation enregistrée et recalculée automatiquement, sur le site et dans l’application mobile",
  "Dossier environnement du bien (écoles, commerces, transports, risques, urbanisme)",
  "Ventes comparables détaillées et tendance du marché local",
];
const PREMIUM_NEXT = [
  "Étape 2 · Mise en vente : prix cible, photos retouchées par IA, annonce rédigée par IA, conseils visites",
  "Étape 3 · Dossier de vente : diagnostics et documents, lecture automatique, PDF pour le notaire",
];

/**
 * Estimation gratuite sans compte : le questionnaire complet de l'application (adresse, bien, détails, équipements)
 * → estimation précise avec ajustements ; la création d'un compte gratuit enregistre le bien et ouvre les étapes suivantes.
 */
export function FreeEstimate() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const [step, setStep] = useState(0);
  const cardRef = useRef<View>(null);
  const firstRender = useRef(true);
  const [body, setBody] = useState<PropertyIn | null>(null);
  const [email, setEmail] = useState("");

  const estimate = useMutation({
    mutationFn: (b: PropertyIn) => api.estimatePreview(b),
    onSuccess: (est, b) => {
      setBody(b);
      if (!user) saveFreeDraft(b, est);
    },
  });
  const save = useMutation({
    mutationFn: () => api.createProperty(body!),
    onSuccess: (prop) => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      router.replace(`/property/${prop.id}`);
    },
  });

  // À chaque changement d'étape (et à l'affichage du résultat), revenir en haut de la carte plutôt que rester en bas de page.
  const resultShown = !!estimate.data;
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if (Platform.OS !== "web") return;
    const node = cardRef.current as unknown as { scrollIntoView?: (o: ScrollIntoViewOptions) => void } | null;
    node?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [step, resultShown]);

  const sendEmail = useMutation({ mutationFn: () => api.freeEstimateEmail(email.trim(), body!) });

  const est: Estimation | undefined = estimate.data;
  const reset = () => {
    estimate.reset();
    sendEmail.reset();
    setBody(null);
    setStep(0);
  };

  if (est && body) {
    const shown = est.adjustments.filter((a) => Math.abs(a.pct) >= 0.1);
    // Même chiffre que dans l'application : valeur finale pondérée (comparables, modèle hédonique, marché local)
    const v = est.final ?? est;
    const models = est.final?.components.filter((c) => c.effective_weight > 0 && c.value !== null) ?? [];
    return (
      <View ref={cardRef} style={styles.card} testID="free-estimate">
        <View style={styles.result} testID="free-result">
          <Text style={styles.resultLabel}>Valeur estimée · {body.address_label}</Text>
          <Text style={styles.resultValue} testID="free-result-value">{formatEuro(v.value)}</Text>
          <Text style={styles.resultRange}>
            Fourchette {formatEuro(v.low)} – {formatEuro(v.high)} · {formatInt(Math.round(v.value / body.surface / 10) * 10)} €/m²
          </Text>
          <Text style={styles.resultMeta}>
            {est.confidence.n_comparables} ventes comparables ({est.confidence.radius_label}) · {body.property_type === "maison" ? "Maison" : "Appartement"} {body.surface} m² · {body.rooms} pièces
          </Text>
          {models.length > 1 ? (
            <Text style={styles.resultMeta} testID="free-result-models">
              Valeur pondérée : {models.map((c) => `${c.label} ${formatEuro(c.value ?? 0)} (${Math.round(c.effective_weight * 100)} %)`).join(" · ")}
            </Text>
          ) : null}
        </View>

        {shown.length > 0 ? (
          <View style={styles.block} testID="free-adjustments">
            <Text style={styles.blockTitle}>Ajustements appliqués à la vente type du secteur</Text>
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
            <Text style={styles.blockTitle}>Inclus avec votre compte gratuit</Text>
          </View>
          {FREE_NEXT.map((l) => (
            <Text key={l} style={styles.lockItem}>• {l}</Text>
          ))}
          <Text style={[styles.blockTitle, { marginTop: spacing.sm }]} testID="free-premium-title">Pack premium · 49 € par bien, paiement unique</Text>
          {PREMIUM_NEXT.map((l) => (
            <Text key={l} style={styles.lockItem}>• {l}</Text>
          ))}
        </View>

        <View style={styles.emailBlock} testID="free-email-block">
          <View style={styles.lockHeader}>
            <EnvelopeSimpleIcon size={18} color={colors.brandPrimary} weight="fill" />
            <Text style={styles.blockTitle}>Recevoir le rapport PDF par e-mail</Text>
          </View>
          {sendEmail.isSuccess ? (
            <Text style={styles.emailOk} testID="free-email-sent">
              Rapport envoyé à {email.trim()}. Pensez à vérifier vos courriers indésirables. Le lien reste valable 90 jours.
            </Text>
          ) : (
            <>
              <Text style={styles.lockItem}>Calcul détaillé, ajustements et marché local, au format PDF — gratuit, sans autre sollicitation.</Text>
              <View style={styles.emailRow}>
                <TextInput
                  testID="free-email-input"
                  style={styles.emailInput}
                  placeholder="vous@exemple.fr"
                  placeholderTextColor={colors.muted}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                  inputMode="email"
                  onSubmitEditing={() => sendEmail.mutate()}
                />
                <PrimaryButton
                  title="Envoyer"
                  variant="secondary"
                  onPress={() => sendEmail.mutate()}
                  loading={sendEmail.isPending}
                  disabled={!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email.trim())}
                  testID="free-email-submit"
                  style={styles.emailBtn}
                />
              </View>
              {sendEmail.isError ? <Text style={styles.error} testID="free-email-error">{(sendEmail.error as Error).message}</Text> : null}
            </>
          )}
        </View>

        <PrimaryButton
          title={user ? "Enregistrer ce bien dans mon espace" : "Créer mon compte gratuit et continuer"}
          onPress={() => (user ? save.mutate() : router.navigate("/sign-up"))}
          loading={save.isPending}
          testID="free-result-cta"
        />
        {save.isError ? <Text style={styles.error}>{(save.error as Error).message}</Text> : null}
        {!user ? (
          <Text style={styles.hint}>
            Déjà inscrit ? <Text style={styles.link} onPress={() => router.navigate("/sign-in")} testID="free-signin-link">Se connecter</Text> — votre estimation sera rattachée à votre compte.
          </Text>
        ) : null}
        <Pressable onPress={reset} accessibilityRole="button" style={styles.resetBtn} testID="free-reset">
          <Text style={styles.resetText}>Modifier mes réponses</Text>
        </Pressable>
        <Text style={styles.disclaimer}>
          Avis de valeur indicatif fondé sur les ventes réelles enregistrées et vos déclarations ; il ne constitue ni une expertise ni une garantie de prix de vente.
        </Text>
      </View>
    );
  }

  return (
    <View ref={cardRef} style={styles.card} testID="free-estimate">
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Estimation gratuite, précise, sans compte</Text>
          <Text style={styles.sub}>
            Le même questionnaire que l’application : étape {step + 1} sur {WIZARD_STEPS.length} · {WIZARD_STEPS[step]}
          </Text>
        </View>
        {step > 0 ? (
          <Pressable onPress={() => setStep(step - 1)} accessibilityRole="button" style={styles.backBtn} testID="free-back">
            <ArrowLeftIcon size={18} color={colors.brandPrimary} />
            <Text style={styles.backText}>Retour</Text>
          </Pressable>
        ) : null}
      </View>
      <View style={styles.steps} testID="free-steps">
        {WIZARD_STEPS.map((s, i) => {
          const done = i < step;
          const active = i === step;
          return (
            <Pressable
              key={s}
              testID={`free-step-${i + 1}`}
              accessibilityRole="button"
              accessibilityState={{ selected: active, disabled: !done }}
              disabled={!done}
              onPress={() => setStep(i)}
              style={styles.stepItem}
            >
              <View style={[styles.stepDot, (done || active) && styles.stepDotActive]}>
                {done ? <CheckIcon size={12} color={colors.onBrandPrimary} weight="bold" /> : <Text style={[styles.stepNum, active && { color: colors.onBrandPrimary }]}>{i + 1}</Text>}
              </View>
              <Text style={[styles.stepLabel, active && styles.stepLabelActive]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.8}>{s}</Text>
              <View style={[styles.progressSeg, i <= step && styles.progressSegActive]} />
            </Pressable>
          );
        })}
      </View>
      <PropertyWizard
        step={step}
        onStepChange={setStep}
        onSubmit={(b) => estimate.mutate(b)}
        submitLabel={estimate.isPending ? "Calcul en cours…" : "Obtenir mon estimation gratuite"}
        loading={estimate.isPending}
        errorMessage={estimate.isError ? (estimate.error as Error).message || "Estimation indisponible pour cette adresse." : null}
      />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md, shadowColor: colors.onSurface, shadowOpacity: 0.06, shadowRadius: 16, shadowOffset: { width: 0, height: 6 } },
  header: { flexDirection: "row", alignItems: "flex-start", gap: spacing.md },
  title: { fontFamily: fonts.bold, fontSize: 22, color: colors.onSurface },
  sub: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary, marginTop: 4 },
  backBtn: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 44, paddingHorizontal: spacing.sm },
  backText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary },
  steps: { flexDirection: "row", gap: spacing.sm },
  stepItem: { flex: 1, gap: 6, alignItems: "center" },
  stepDot: { width: 24, height: 24, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  stepDotActive: { backgroundColor: colors.brandPrimary },
  stepNum: { fontFamily: fonts.bold, fontSize: 12, color: colors.muted },
  stepLabel: { fontFamily: fonts.medium, fontSize: 11, color: colors.muted, textAlign: "center" },
  stepLabelActive: { color: colors.brandPrimary, fontFamily: fonts.semibold },
  progressSeg: { alignSelf: "stretch", height: 4, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary },
  progressSegActive: { backgroundColor: colors.brandPrimary },
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
  emailBlock: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: spacing.lg, gap: spacing.sm },
  emailRow: { flexDirection: "row", gap: spacing.sm, alignItems: "center", flexWrap: "wrap" },
  emailInput: { flex: 1, minWidth: 200, minHeight: 48, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: spacing.md, fontFamily: fonts.regular, fontSize: 15, color: colors.onSurface, backgroundColor: colors.surface },
  emailBtn: { minWidth: 120 },
  emailOk: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.success },
  lockHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  lockItem: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceSecondary },
  hint: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary, textAlign: "center" },
  link: { fontFamily: fonts.semibold, color: colors.brandPrimary },
  resetBtn: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  resetText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary },
  error: { fontFamily: fonts.regular, fontSize: 13, color: colors.error },
  disclaimer: { fontFamily: fonts.regular, fontSize: 11, lineHeight: 16, color: colors.muted },
}));
