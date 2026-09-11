import { ArrowRightIcon, BuildingsIcon, CaretRightIcon, CheckCircleIcon, HouseIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { Property, PropertyNextSteps, TYPE_LABELS, formatK } from "@/src/api";
import { ConfidenceBadge } from "@/src/components/ConfidenceBadge";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  property: Property;
  onPress: () => void;
  testID: string;
  nextSteps?: PropertyNextSteps | null;
  onStepPress?: (route: string) => void;
}

export function PropertyCard({ property, onPress, testID, nextSteps, onStepPress }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const est = property.estimation;
  const Icon = property.property_type === "maison" ? HouseIcon : BuildingsIcon;
  const next = nextSteps?.next ?? null;

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
              <Text style={styles.range} testID={`${testID}-range`}>
                {formatK(est.low)} – {formatK(est.high)}
              </Text>
              <ConfidenceBadge level={est.confidence.level} />
            </>
          ) : (
            <Text style={styles.meta}>Estimation indisponible</Text>
          )}
        </View>
        <CaretRightIcon size={18} color={colors.muted} />
      </Pressable>

      {nextSteps ? (
        <Pressable
          testID={`${testID}-next-step`}
          accessibilityRole="button"
          accessibilityLabel={next ? `Prochaine étape : ${next.label}` : "Toutes les étapes sont faites"}
          onPress={() => next && onStepPress?.(next.route)}
          style={({ pressed }) => [styles.stepRow, next?.key === "dossier" && next.label.startsWith("Renouveler") && styles.stepRowUrgent, pressed && styles.pressed]}
        >
          <View style={styles.stepProgress}>
            <Text style={styles.stepProgressText}>{nextSteps.done}/{nextSteps.total}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.stepKicker}>Prochaine étape</Text>
            <Text style={styles.stepLabel} numberOfLines={1} testID={`${testID}-next-step-label`}>
              {next ? next.label : "Tout est prêt"}
            </Text>
          </View>
          {next ? (
            <ArrowRightIcon size={16} color={colors.onBrandTertiary} weight="bold" />
          ) : (
            <CheckCircleIcon size={18} color={colors.success} weight="fill" />
          )}
        </Pressable>
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
  address: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary },
  meta: { fontFamily: fonts.regular, fontSize: 13, color: colors.muted },
  range: { fontFamily: fonts.bold, fontSize: 20, color: colors.onSurfaceSecondary, marginTop: 2, marginBottom: 4 },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.brandTertiary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: 48,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  stepRowUrgent: { backgroundColor: colors.warningSoft },
  stepProgress: { minWidth: 40, height: 28, borderRadius: radius.pill, backgroundColor: colors.surfaceSecondary, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.sm },
  stepProgressText: { fontFamily: fonts.bold, fontSize: 12, color: colors.onBrandTertiary, fontVariant: ["tabular-nums"] },
  stepKicker: { fontFamily: fonts.medium, fontSize: 10, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  stepLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
}));
