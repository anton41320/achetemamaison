import { ArrowRightIcon, BuildingsIcon, CaretRightIcon, CheckCircleIcon, CheckIcon, HouseIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { NextStep, Property, PropertyNextSteps, TYPE_LABELS, formatEuro, formatK } from "@/src/api";
import { CompletionBadge } from "@/src/components/CompletionBadge";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  property: Property;
  onPress: () => void;
  testID: string;
  nextSteps?: PropertyNextSteps | null;
  onStepPress?: (route: string) => void;
}

const STAGES = ["Estimation", "Mise en vente", "Vendu"] as const;

/** Stage of the sale derived from the server-side next steps: prix fixé → mise en vente ; dossier complet → vendu. */
function stageOf(ns: PropertyNextSteps | null | undefined): { stage: 0 | 1 | 2; cta: { label: string; route: string } | null; urgent: boolean } {
  if (!ns) return { stage: 0, cta: null, urgent: false };
  const by = (k: NextStep["key"]) => ns.steps.find((s) => s.key === k);
  const target = by("target");
  const dossier = by("dossier");
  if (target && !target.done) {
    const features = by("features");
    return { stage: 0, cta: { label: features && !features.done ? `${features.label}, puis fixer votre prix de vente` : "Fixer votre prix de vente", route: target.route }, urgent: false };
  }
  if (dossier && !dossier.done) {
    const pending = (["photos", "listing", "dossier"] as const).map(by).find((s) => s && !s.done)!;
    return { stage: 1, cta: { label: pending.label, route: pending.route }, urgent: pending.key === "dossier" && pending.label.startsWith("Renouveler") };
  }
  const exp = by("export");
  return { stage: 2, cta: exp ? { label: exp.label, route: exp.route } : null, urgent: false };
}

export function PropertyCard({ property, onPress, testID, nextSteps, onStepPress }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const est = property.estimation;
  const Icon = property.property_type === "maison" ? HouseIcon : BuildingsIcon;
  const { stage, cta, urgent } = stageOf(nextSteps);

  return (
    <View style={styles.card}>
      <Pressable
        testID={testID}
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [styles.main, pressed && styles.pressed]}
      >
        <View style={styles.iconWrap}>
          <Icon size={22} color={colors.onBrandTertiary} weight="duotone" />
        </View>
        <View style={styles.body}>
          <Text style={styles.address} numberOfLines={1}>
            {property.address_label}
          </Text>
          <Text style={styles.meta}>
            {TYPE_LABELS[property.property_type]} · {property.surface} m² · {property.rooms} p.
          </Text>
          {est ? (
            <>
              <Text style={styles.value} testID={`${testID}-value`}>{formatEuro(est.value)}</Text>
              <Text style={styles.range} testID={`${testID}-range`}>
                Fourchette {formatK(est.low)} – {formatK(est.high)}
              </Text>
              {property.completion ? (
                <View style={styles.badges}>
                  <CompletionBadge completion={property.completion} testID={`${testID}-completion`} />
                </View>
              ) : null}
            </>
          ) : (
            <Text style={styles.meta}>Estimation indisponible</Text>
          )}
        </View>
        <CaretRightIcon size={18} color={colors.muted} />
      </Pressable>

      {nextSteps ? (
        <View style={styles.stageBox} testID={`${testID}-stage`}>
          <View style={styles.stageTrack}>
            {STAGES.map((st, i) => (
              <View key={st} style={styles.stageItem}>
                <View style={[styles.stageDot, i < stage && styles.stageDotDone, i === stage && styles.stageDotCurrent]}>
                  {i < stage ? <CheckIcon size={10} color={colors.onBrandPrimary} weight="bold" /> : <Text style={[styles.stageDotText, i === stage && styles.stageDotTextCurrent]}>{i + 1}</Text>}
                </View>
                <Text style={[styles.stageLabel, i === stage && styles.stageLabelCurrent]} numberOfLines={1}>{st}</Text>
              </View>
            ))}
          </View>
          <Pressable
            testID={`${testID}-next-step`}
            accessibilityRole="button"
            accessibilityLabel={cta ? `Prochaine étape : ${cta.label}` : "Toutes les étapes sont faites"}
            onPress={() => cta && onStepPress?.(cta.route)}
            style={({ pressed }) => [styles.stepRow, urgent && styles.stepRowUrgent, pressed && styles.pressed]}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.stepKicker} testID={`${testID}-stage-label`}>Étape {stage + 1}/3 · {STAGES[stage]}{stage < 2 ? ` → ${STAGES[stage + 1]}` : " · dossier complet"}</Text>
              <Text style={styles.stepLabel} numberOfLines={1} testID={`${testID}-next-step-label`}>
                {cta ? cta.label : "Tout est prêt"}
              </Text>
            </View>
            {cta ? <ArrowRightIcon size={16} color={colors.onBrandTertiary} weight="bold" /> : <CheckCircleIcon size={18} color={colors.success} weight="fill" />}
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  main: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  pressed: { opacity: 0.9 },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  body: { flex: 1, gap: 4 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, alignItems: "center" },
  address: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary },
  meta: { fontFamily: fonts.regular, fontSize: 13, color: colors.muted },
  value: { fontFamily: fonts.bold, fontSize: 22, color: colors.onSurfaceSecondary, marginTop: 2, fontVariant: ["tabular-nums"] },
  range: { fontFamily: fonts.medium, fontSize: 12, color: colors.muted, marginBottom: 4, fontVariant: ["tabular-nums"] },
  stageBox: { borderTopWidth: 1, borderTopColor: colors.border },
  stageTrack: { flexDirection: "row", paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, gap: spacing.sm, backgroundColor: colors.surface },
  stageItem: { flex: 1, flexDirection: "row", alignItems: "center", gap: 6 },
  stageDot: { width: 20, height: 20, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  stageDotDone: { backgroundColor: colors.success },
  stageDotCurrent: { backgroundColor: colors.brandPrimary },
  stageDotText: { fontFamily: fonts.bold, fontSize: 11, color: colors.onSurfaceSecondary },
  stageDotTextCurrent: { color: colors.onBrandPrimary },
  stageLabel: { flex: 1, fontFamily: fonts.medium, fontSize: 11, color: colors.muted },
  stageLabelCurrent: { fontFamily: fonts.bold, color: colors.brandPrimary },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.brandTertiary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: 48,
  },
  stepRowUrgent: { backgroundColor: colors.warningSoft },
  stepKicker: { fontFamily: fonts.medium, fontSize: 10, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  stepLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
}));
