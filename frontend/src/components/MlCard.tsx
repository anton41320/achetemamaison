import { RobotIcon } from "phosphor-react-native";
import { Text, View } from "react-native";

import { MlResult, formatEuro, formatK, formatPct } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  ml: MlResult;
}

export function MlCard({ ml }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const maxAbs = Math.max(0.05, ...ml.factors.map((f) => Math.abs(f.pct)));

  return (
    <View style={styles.card} testID="ml-card">
      <View style={styles.header}>
        <RobotIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Machine learning (LightGBM + SHAP)</Text>
        <View style={[styles.pill, { backgroundColor: ml.promoted ? colors.successSoft : colors.warningSoft }]} testID="ml-promoted-badge">
          <Text style={[styles.pillText, { color: ml.promoted ? colors.success : colors.warning }]}>
            {ml.promoted ? "Promu" : "Non promu"}
          </Text>
        </View>
      </View>
      <Text style={styles.p}>
        {ml.promoted
          ? "Le modèle bat les comparables sur les ventes 2025 de test : il entre dans la pondération finale."
          : `Sur les ventes 2025 de test, erreur médiane ${ml.model_median_ape ?? "—"} % contre ${ml.baseline_median_ape ?? "—"} % pour les comparables : le modèle reste informatif mais n’entre pas dans la valeur finale.`}
      </Text>
      <View style={styles.valueRow}>
        <Text style={styles.value} testID="ml-value">{formatEuro(ml.value)}</Text>
        <Text style={styles.detail}>{formatK(ml.low)} – {formatK(ml.high)}</Text>
      </View>
      {ml.factors.map((f) => {
        const positive = f.pct > 0.0005;
        const negative = f.pct < -0.0005;
        const color = positive ? colors.success : negative ? colors.error : colors.muted;
        const width = Math.round((Math.abs(f.pct) / maxAbs) * 50);
        return (
          <View key={f.key} style={styles.factor} testID={`ml-factor-${f.key}`}>
            <View style={styles.factorHead}>
              <Text style={styles.factorLabel}>{f.label}</Text>
              <Text style={[styles.factorPct, { color }]}>{positive || negative ? formatPct(f.pct, 1) : "—"}</Text>
            </View>
            <View style={styles.axis}>
              <View style={styles.axisHalf}>{negative ? <View style={[styles.bar, styles.barLeft, { width: `${width}%`, backgroundColor: color }]} /> : null}</View>
              <View style={styles.axisLine} />
              <View style={styles.axisHalf}>{positive ? <View style={[styles.bar, { width: `${width}%`, backgroundColor: color }]} /> : null}</View>
            </View>
          </View>
        );
      })}
      <Text style={styles.detail}>Contributions SHAP par rapport à la vente moyenne ({formatK(ml.reference_value)}).</Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onSurfaceSecondary, flex: 1 },
  pill: { paddingHorizontal: spacing.md, height: 26, borderRadius: radius.pill, justifyContent: "center" },
  pillText: { fontFamily: fonts.semibold, fontSize: 12 },
  p: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  valueRow: { flexDirection: "row", alignItems: "baseline", gap: spacing.md },
  value: { fontFamily: fonts.bold, fontSize: 20, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  factor: { gap: 4 },
  factorHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  factorLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  factorPct: { fontFamily: fonts.semibold, fontSize: 14, fontVariant: ["tabular-nums"] },
  axis: { flexDirection: "row", alignItems: "center", height: 8 },
  axisHalf: { flex: 1, height: 8, justifyContent: "center" },
  axisLine: { width: 1, height: 12, backgroundColor: colors.borderStrong },
  bar: { height: 6, borderRadius: radius.pill },
  barLeft: { alignSelf: "flex-end" },
}));
