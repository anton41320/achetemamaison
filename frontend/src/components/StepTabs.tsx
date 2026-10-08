import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { CheckIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { api } from "@/src/api";
import { STAGES, Stage, stageOf, stepRoute } from "@/src/steps";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
  /** Step page currently displayed. */
  current: Stage;
}

/** 3-step funnel tabs (Estimation → Mise en vente → Vendu). Each tab opens its own page. */
export function StepTabs({ propertyId, current }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const steps = useQuery({ queryKey: ["next-steps"], queryFn: api.nextSteps });
  const { stage: reached } = stageOf(steps.data?.properties.find((p) => p.property_id === propertyId));

  return (
    <View style={styles.row} testID="step-tabs">
      {STAGES.map((label, i) => {
        const active = i === current;
        const done = i < reached;
        return (
          <Pressable
            key={label}
            testID={`step-tab-${i + 1}`}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={`Étape ${i + 1} : ${label}`}
            onPress={() => !active && router.navigate(stepRoute(propertyId, i as Stage) as any)}
            style={({ pressed }) => [styles.tab, active && styles.tabActive, pressed && !active && { opacity: 0.8 }]}
          >
            <View style={[styles.dot, done && styles.dotDone, active && styles.dotActive]}>
              {done && !active ? (
                <CheckIcon size={12} color={colors.onBrandPrimary} weight="bold" />
              ) : (
                <Text style={[styles.dotText, (active || done) && styles.dotTextOn]}>{i + 1}</Text>
              )}
            </View>
            <Text style={[styles.label, active && styles.labelActive]} numberOfLines={1} adjustsFontSizeToFit>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  row: { flexDirection: "row", gap: spacing.sm, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.xs },
  tab: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, minHeight: 48, borderRadius: radius.md, paddingHorizontal: spacing.xs },
  tabActive: { flex: 1.5, backgroundColor: colors.brandPrimary },
  dot: { width: 22, height: 22, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  dotDone: { backgroundColor: colors.success },
  dotActive: { backgroundColor: colors.onBrandPrimary },
  dotText: { fontFamily: fonts.bold, fontSize: 12, color: colors.onSurfaceSecondary },
  dotTextOn: { color: colors.brandPrimary },
  label: { flexShrink: 1, fontFamily: fonts.semibold, fontSize: 12, color: colors.muted },
  labelActive: { color: colors.onBrandPrimary },
}));
