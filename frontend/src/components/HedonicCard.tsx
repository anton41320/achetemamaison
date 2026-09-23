import { BrainIcon, ScalesIcon } from "phosphor-react-native";
import { Text, View } from "react-native";

import { HedonicResult, formatEuro, formatInt, formatK, formatPct } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  hedonic: HedonicResult;
  comparablesValue: number;
}

const AGREEMENT_LABEL = {
  convergent: "Les deux approches convergent",
  ecart_modere: "Écart modéré entre les approches",
  divergent: "Écart important entre les approches",
};

export function HedonicCard({ hedonic, comparablesValue }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const tone =
    hedonic.agreement === "convergent" ? colors.success : hedonic.agreement === "ecart_modere" ? colors.warning : colors.error;
  const maxAbs = Math.max(0.05, ...hedonic.factors.map((f) => Math.abs(f.pct)));

  return (
    <View style={styles.card} testID="hedonic-card">
      <View style={styles.header}>
        <BrainIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Pourquoi cette estimation ?</Text>
      </View>
      <Text style={styles.p}>
        Modèle hédonique (régression log-prix) entraîné sur {formatInt(hedonic.model_n)} ventes réelles. Il décompose la
        valeur en facteurs à partir d’un bien type, à titre de comparaison avec les comparables.
      </Text>

      <View style={styles.refRow}>
        <Text style={styles.refLabel}>{hedonic.reference_label}</Text>
        <Text style={styles.refValue}>{formatK(hedonic.reference_value)}</Text>
      </View>

      {hedonic.factors.map((f) => {
        const positive = f.pct > 0.0005;
        const negative = f.pct < -0.0005;
        const width = Math.round((Math.abs(f.pct) / maxAbs) * 50);
        const color = positive ? colors.success : negative ? colors.error : colors.muted;
        return (
          <View key={f.key} style={styles.factor} testID={`hedonic-factor-${f.key}`}>
            <View style={styles.factorHead}>
              <Text style={styles.factorLabel} numberOfLines={1}>
                {f.label}
                {!f.learned ? <Text style={styles.declared}>  déclaré</Text> : null}
              </Text>
              <Text style={[styles.factorPct, { color }]}>{positive || negative ? formatPct(f.pct, 1) : "—"}</Text>
            </View>
            <View style={styles.axis}>
              <View style={styles.axisHalf}>
                {negative ? <View style={[styles.bar, styles.barLeft, { width: `${width}%`, backgroundColor: color }]} /> : null}
              </View>
              <View style={styles.axisLine} />
              <View style={styles.axisHalf}>
                {positive ? <View style={[styles.bar, { width: `${width}%`, backgroundColor: color }]} /> : null}
              </View>
            </View>
            <Text style={styles.detail}>{f.detail}</Text>
          </View>
        );
      })}

      <View style={styles.compare}>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>Comparables (référence)</Text>
          <Text style={styles.compareValue} testID="hedonic-compare-baseline">{formatEuro(comparablesValue)}</Text>
        </View>
        <ScalesIcon size={22} color={colors.muted} />
        <View style={[styles.compareCol, { alignItems: "flex-end" }]}>
          <Text style={styles.compareLabel}>Hédonique</Text>
          <Text style={styles.compareValue} testID="hedonic-value">{formatEuro(hedonic.value)}</Text>
          <Text style={styles.detail}>
            {formatK(hedonic.low)} – {formatK(hedonic.high)}
          </Text>
        </View>
      </View>
      <View style={[styles.agreement, { borderColor: tone }]} testID="hedonic-agreement">
        <Text style={[styles.agreementText, { color: tone }]}>
          {AGREEMENT_LABEL[hedonic.agreement]} ({formatPct(hedonic.delta_vs_comparables_pct, 0)} vs comparables)
        </Text>
      </View>
      <Text style={styles.detail}>
        Erreur médiane du modèle sur des ventes 2025 non vues : {hedonic.model_median_ape ?? "—"} %. La fourchette
        affichée en haut reste celle des comparables.
      </Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flex: 1 },
  p: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  refRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, padding: spacing.md },
  refLabel: { flex: 1, fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceTertiary },
  refValue: { fontFamily: fonts.bold, fontSize: 15, color: colors.onSurfaceTertiary, fontVariant: ["tabular-nums"] },
  factor: { gap: 4 },
  factorHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md },
  factorLabel: { flex: 1, fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  declared: { fontFamily: fonts.regular, fontSize: 11, color: colors.muted },
  factorPct: { fontFamily: fonts.semibold, fontSize: 14, fontVariant: ["tabular-nums"] },
  axis: { flexDirection: "row", alignItems: "center", height: 8 },
  axisHalf: { flex: 1, height: 8, justifyContent: "center" },
  axisLine: { width: 1, height: 12, backgroundColor: colors.borderStrong },
  bar: { height: 6, borderRadius: radius.pill },
  barLeft: { alignSelf: "flex-end" },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  compare: { flexDirection: "row", alignItems: "center", gap: spacing.md, borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.md },
  compareCol: { flex: 1, gap: 2 },
  compareLabel: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  compareValue: { fontFamily: fonts.bold, fontSize: 17, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  agreement: { borderWidth: 1, borderRadius: radius.md, padding: spacing.md, alignItems: "center" },
  agreementText: { fontFamily: fonts.semibold, fontSize: 13, textAlign: "center" },
}));
