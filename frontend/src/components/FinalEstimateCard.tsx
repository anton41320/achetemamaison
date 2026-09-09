import Slider from "@react-native-community/slider";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SlidersIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { DEFAULT_WEIGHTS, Estimation, Weights, api, blendEstimation, formatEuro, formatK } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  estimation: Estimation;
}

export function FinalEstimateCard({ estimation }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const saved = useQuery({ queryKey: ["weights"], queryFn: api.getWeights });
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);

  useEffect(() => {
    if (saved.data) setWeights(saved.data);
  }, [saved.data]);

  const save = useMutation({
    mutationFn: api.putWeights,
    onSuccess: (w) => {
      queryClient.setQueryData(["weights"], w);
      queryClient.invalidateQueries({ queryKey: ["weights"] });
    },
  });

  const result = blendEstimation(estimation, weights);
  const activeCount = result.components.filter((c) => c.effective_weight > 0).length;

  const commit = (key: keyof Weights, v: number) => {
    const next = { ...weights, [key]: Math.round(v) };
    if (Object.values(next).every((x) => x === 0)) return;
    setWeights(next);
    save.mutate(next);
  };

  return (
    <View style={styles.card} testID="final-estimate-card">
      <View style={styles.header}>
        <SlidersIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Estimation finale pondérée</Text>
      </View>
      <View style={styles.headline}>
        <Text style={styles.range} testID="final-range">
          {formatK(result.low)} – {formatK(result.high)}
        </Text>
        <Text style={styles.central} testID="final-value">Valeur centrale {formatEuro(result.value)}</Text>
        <Text style={styles.detail}>
          {activeCount > 1 ? `Moyenne pondérée de ${activeCount} signaux` : "Un seul signal actif : comparables"} · réglage
          mémorisé pour tous vos biens
        </Text>
      </View>

      {result.components.map((c) => {
        const disabled = !c.available;
        return (
          <View key={c.key} style={[styles.row, disabled && styles.rowDisabled]} testID={`weight-row-${c.key}`}>
            <View style={styles.rowHead}>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowLabel}>{c.label}</Text>
                <Text style={styles.detail}>
                  {c.value !== null ? formatEuro(c.value) : "—"}
                  {disabled
                    ? c.key === "ml"
                      ? "  · non promu (ne bat pas la baseline)"
                      : "  · indisponible"
                    : `  · ${Math.round(c.effective_weight * 100)} % du résultat`}
                </Text>
              </View>
              <Text style={styles.weight} testID={`weight-value-${c.key}`}>{weights[c.key]}</Text>
            </View>
            <Slider
              testID={`weight-slider-${c.key}`}
              style={styles.slider}
              minimumValue={0}
              maximumValue={100}
              step={5}
              value={weights[c.key]}
              disabled={disabled}
              onValueChange={(v) => setWeights((w) => ({ ...w, [c.key]: Math.round(v) }))}
              onSlidingComplete={(v) => commit(c.key, v)}
              minimumTrackTintColor={disabled ? colors.borderStrong : colors.brandPrimary}
              maximumTrackTintColor={colors.surfaceTertiary}
              thumbTintColor={disabled ? colors.borderStrong : colors.brandPrimary}
            />
          </View>
        );
      })}
      <Text style={styles.detail}>
        Les poids sont relatifs (normalisés entre les signaux disponibles). Le ML n’entre dans la pondération que s’il bat
        les comparables sur les ventes 2025 de test.
      </Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flex: 1 },
  headline: { backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg, gap: 4 },
  range: { fontFamily: fonts.bold, fontSize: 28, color: colors.onBrandTertiary, fontVariant: ["tabular-nums"] },
  central: { fontFamily: fonts.medium, fontSize: 14, color: colors.onBrandTertiary },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  row: { gap: 2 },
  rowDisabled: { opacity: 0.55 },
  rowHead: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  rowLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  weight: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurfaceSecondary, minWidth: 36, textAlign: "right", fontVariant: ["tabular-nums"] },
  slider: { width: "100%", height: 40 },
}));
