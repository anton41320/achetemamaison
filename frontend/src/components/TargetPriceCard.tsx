import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CrosshairIcon } from "phosphor-react-native";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { TargetZone, api, formatEuro, formatInt, formatK, formatPct } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
  suggestedValue: number;
}

export function TargetPriceCard({ propertyId, suggestedValue }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const target = useQuery({ queryKey: ["target", propertyId], queryFn: () => api.getTarget(propertyId) });

  const save = useMutation({
    mutationFn: (v: number | null) => api.putTarget(propertyId, v),
    onSuccess: (r) => {
      queryClient.setQueryData(["target", propertyId], r);
      setEditing(false);
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const submit = () => {
    const n = Number(input.replace(/[^\d]/g, ""));
    if (!n || n < 10_000) {
      setError("Saisissez un prix en euros (10 000 € minimum).");
      return;
    }
    save.mutate(n);
  };

  const startEdit = () => {
    setInput(String(Math.round(target.data?.target_price ?? suggestedValue)));
    setError(null);
    setEditing(true);
  };

  const a = target.data?.analysis ?? null;
  const zoneTone = (z: TargetZone) =>
    z === "central" || z === "bas" ? colors.success : z === "haut" ? colors.warning : colors.error;
  const zoneSoft = (z: TargetZone) =>
    z === "central" || z === "bas" ? colors.successSoft : z === "haut" ? colors.warningSoft : colors.errorSoft;

  const showForm = editing || (!target.isLoading && !target.data?.target_price);

  return (
    <View style={styles.card} testID="target-price-card">
      <View style={styles.header}>
        <CrosshairIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Prix cible</Text>
        {a && !editing ? (
          <Pressable testID="target-edit-button" accessibilityRole="button" onPress={startEdit} style={styles.smallBtn}>
            <Text style={styles.smallBtnLabel}>Modifier</Text>
          </Pressable>
        ) : null}
      </View>

      {showForm ? (
        <View style={{ gap: spacing.md }} testID="target-form">
          <Text style={styles.p}>
            À quel prix souhaitez-vous vendre ? Estimo situe ce prix dans la fourchette finale et les signaux du marché.
          </Text>
          <View style={styles.inputRow}>
            <TextInput
              testID="target-input"
              value={input}
              onChangeText={(t) => setInput(t.replace(/[^\d]/g, ""))}
              keyboardType="number-pad"
              inputMode="numeric"
              returnKeyType="done"
              onSubmitEditing={submit}
              placeholder={String(Math.round(suggestedValue))}
              placeholderTextColor={colors.muted}
              style={styles.input}
              maxLength={9}
            />
            <Text style={styles.suffix}>€</Text>
          </View>
          {error ? <Text style={styles.error} testID="target-error">{error}</Text> : null}
          <View style={styles.formRow}>
            {editing && target.data?.target_price ? (
              <PrimaryButton title="Annuler" variant="ghost" onPress={() => setEditing(false)} testID="target-cancel-button" style={{ flex: 1 }} />
            ) : null}
            <PrimaryButton title="Enregistrer" onPress={submit} loading={save.isPending} testID="target-save-button" style={{ flex: 1 }} />
          </View>
        </View>
      ) : a ? (
        <>
          <View style={[styles.headline, { backgroundColor: zoneSoft(a.zone) }]}>
            <Text style={[styles.zone, { color: zoneTone(a.zone) }]} testID="target-zone">{a.label}</Text>
            <Text style={styles.big} testID="target-value">{formatEuro(a.target_price)}</Text>
            <Text style={styles.p}>
              {formatPct(a.delta_pct, 1)} vs valeur centrale ({formatEuro(a.value)}) · {formatInt(a.target_price_m2)} €/m²
            </Text>
          </View>

          <RangeBar low={a.low} high={a.high} value={a.value} position={a.position} tone={zoneTone(a.zone)} />

          <Text style={styles.p} testID="target-advice">{a.advice}</Text>
          {a.tips.map((t, i) => (
            <Text key={i} style={styles.tip} testID={`target-tip-${i}`}>• {t}</Text>
          ))}
          <Pressable testID="target-clear-button" accessibilityRole="button" onPress={() => save.mutate(null)} style={styles.clearBtn}>
            <Text style={styles.clearLabel}>Retirer le prix cible</Text>
          </Pressable>
        </>
      ) : null}
    </View>
  );
}

function RangeBar({ low, high, value, position, tone }: { low: number; high: number; value: number; position: number; tone: string }) {
  const styles = useStyles();
  const clamp = (p: number) => Math.min(0.97, Math.max(0.03, p));
  const central = clamp((value - low) / Math.max(high - low, 1));
  const target = clamp(position);
  const outside = position < 0 || position > 1;
  return (
    <View style={{ gap: 6 }} testID="target-range-bar">
      <View style={styles.track}>
        <View style={[styles.marker, styles.markerCentral, { left: `${central * 100}%` as `${number}%` }]} />
        <View style={[styles.marker, { left: `${target * 100}%` as `${number}%`, backgroundColor: tone, borderColor: tone }]} />
      </View>
      <View style={styles.legendRow}>
        <Text style={styles.legend}>{formatK(low)}</Text>
        <Text style={styles.legend}>Fourchette finale{outside ? " · prix hors fourchette" : ""}</Text>
        <Text style={styles.legend}>{formatK(high)}</Text>
      </View>
      <View style={styles.legendRow}>
        <View style={styles.legendItem}><View style={[styles.dot, styles.markerCentral]} /><Text style={styles.legend}>Valeur centrale</Text></View>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: tone }]} /><Text style={styles.legend}>Votre prix</Text></View>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flex: 1 },
  smallBtn: { minHeight: 36, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, justifyContent: "center" },
  smallBtnLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  p: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  tip: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  inputRow: { flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, paddingHorizontal: spacing.lg, minHeight: 52 },
  input: { flex: 1, fontFamily: fonts.bold, fontSize: 20, color: colors.onSurface, paddingVertical: 12, fontVariant: ["tabular-nums"] },
  suffix: { fontFamily: fonts.medium, fontSize: 16, color: colors.muted, marginLeft: spacing.sm },
  error: { fontFamily: fonts.medium, fontSize: 12, color: colors.error },
  formRow: { flexDirection: "row", gap: spacing.md },
  headline: { borderRadius: radius.md, padding: spacing.lg, gap: 4 },
  zone: { fontFamily: fonts.semibold, fontSize: 13, textTransform: "uppercase", letterSpacing: 0.6 },
  big: { fontFamily: fonts.bold, fontSize: 28, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  track: { height: 10, borderRadius: radius.pill, backgroundColor: colors.brandSecondary, marginTop: spacing.sm, marginHorizontal: 8 },
  marker: { position: "absolute", top: -5, width: 20, height: 20, marginLeft: -10, borderRadius: radius.pill, borderWidth: 3, borderColor: colors.surfaceSecondary },
  markerCentral: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  legendRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.sm },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  dot: { width: 10, height: 10, borderRadius: radius.pill },
  legend: { fontFamily: fonts.regular, fontSize: 11, color: colors.muted },
  clearBtn: { minHeight: 40, alignItems: "center", justifyContent: "center" },
  clearLabel: { fontFamily: fonts.medium, fontSize: 13, color: colors.error },
}));
