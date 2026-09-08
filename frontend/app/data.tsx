import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { CheckCircleIcon, DatabaseIcon, WarningIcon } from "phosphor-react-native";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ValidationAgg, api, formatInt, formatMonth } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const DEPT_NAMES: Record<string, string> = { "41": "Loir-et-Cher", "37": "Indre-et-Loire", "45": "Loiret" };
const LEVEL_LABELS: Record<string, string> = { eleve: "Confiance élevée", moyen: "Confiance moyenne", faible: "Confiance faible", appartement: "Appartements", maison: "Maisons" };

function pct(v: number) {
  return `${v.toFixed(1).replace(".", ",")} %`;
}

export default function DataScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const status = useQuery({
    queryKey: ["dvf-status"],
    queryFn: api.dvfStatus,
    refetchInterval: (q) => (q.state.data?.state === "running" ? 2000 : false),
  });

  const ingest = useMutation({
    mutationFn: api.dvfIngest,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dvf-status"] }),
  });

  const validation = useMutation({ mutationFn: () => api.validation(40) });

  const model = useQuery({
    queryKey: ["hedonic-model"],
    queryFn: api.hedonicModel,
    refetchInterval: (q) => (q.state.data?.training || !q.state.data?.available ? 3000 : false),
  });
  const train = useMutation({
    mutationFn: api.hedonicTrain,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["hedonic-model"] }),
  });

  const s = status.data;

  const AggBlock = ({ title, agg, testID }: { title: string; agg: ValidationAgg; testID: string }) => (
    <View style={styles.aggBlock} testID={testID}>
      <Text style={styles.aggTitle}>{title} <Text style={styles.aggN}>({agg.n} biens)</Text></Text>
      <View style={styles.aggRow}>
        <View style={styles.aggCell}><Text style={styles.aggValue}>{pct(agg.median_ape)}</Text><Text style={styles.aggLabel}>Erreur médiane</Text></View>
        <View style={styles.aggCell}><Text style={styles.aggValue}>{pct(agg.coverage)}</Text><Text style={styles.aggLabel}>Prix réel dans la fourchette</Text></View>
        <View style={styles.aggCell}><Text style={styles.aggValue}>{pct(agg.within_15pct)}</Text><Text style={styles.aggLabel}>Erreur ≤ 15 %</Text></View>
      </View>
    </View>
  );

  return (
    <View style={styles.screen} testID="data-screen">
      <ScreenHeader title="Données DVF" subtitle="Source : data.gouv.fr · Demandes de valeurs foncières" onBack={() => router.back()} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        {status.isLoading ? (
          <ActivityIndicator color={colors.brandPrimary} />
        ) : status.isError || !s ? (
          <PrimaryButton title="Réessayer" variant="secondary" onPress={() => status.refetch()} testID="data-retry-button" />
        ) : (
          <>
            <View style={styles.card} testID="dvf-status-card">
              <View style={styles.cardHeader}>
                <DatabaseIcon size={20} color={colors.brandPrimary} />
                <Text style={styles.h3}>Base de ventes</Text>
                {s.state === "running" ? (
                  <View style={[styles.pill, { backgroundColor: colors.warningSoft }]}>
                    <ActivityIndicator size="small" color={colors.warning} />
                    <Text style={[styles.pillText, { color: colors.warning }]}>{Math.round(s.progress * 100)} %</Text>
                  </View>
                ) : s.total > 0 ? (
                  <View style={[styles.pill, { backgroundColor: colors.successSoft }]}>
                    <CheckCircleIcon size={14} color={colors.success} weight="fill" />
                    <Text style={[styles.pillText, { color: colors.success }]}>À jour</Text>
                  </View>
                ) : (
                  <View style={[styles.pill, { backgroundColor: colors.errorSoft }]}>
                    <WarningIcon size={14} color={colors.error} weight="fill" />
                    <Text style={[styles.pillText, { color: colors.error }]}>Vide</Text>
                  </View>
                )}
              </View>
              <Text style={styles.big} testID="dvf-total">{formatInt(s.total)} ventes</Text>
              <Text style={styles.muted}>
                Années {s.years[0]}–{s.years[s.years.length - 1]} · Maisons et appartements · une seule habitation par mutation
              </Text>
              {s.departments.map((d) => (
                <View key={d.dept} style={styles.deptRow} testID={`dvf-dept-${d.dept}`}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.deptName}>{DEPT_NAMES[d.dept] ?? "Département"} ({d.dept})</Text>
                    <Text style={styles.muted}>
                      {formatInt(d.appartement)} appts · {formatInt(d.maison)} maisons
                      {d.max_date ? ` · jusqu’à ${formatMonth(d.max_date)}` : ""}
                    </Text>
                  </View>
                  <Text style={styles.deptTotal}>{formatInt(d.total)}</Text>
                </View>
              ))}
              {s.error ? <Text style={styles.errorText}>Dernière erreur : {s.error}</Text> : null}
              {s.state !== "running" ? (
                <PrimaryButton
                  title={s.total > 0 ? "Relancer l’ingestion" : "Lancer l’ingestion"}
                  variant="secondary"
                  onPress={() => ingest.mutate()}
                  loading={ingest.isPending}
                  testID="dvf-ingest-button"
                />
              ) : null}
            </View>

            <View style={styles.card} testID="hedonic-model-card">
              <Text style={styles.h3}>Modèle hédonique (Phase 2)</Text>
              {model.data?.available && model.data.holdout ? (
                <>
                  <Text style={styles.p}>
                    Régression log(prix) sur {formatInt(model.data.n ?? 0)} ventes · {model.data.communes_with_effect} communes avec
                    effet propre · validation temporelle sur {model.data.holdout.test_year} (entraîné sur les années précédentes).
                  </Text>
                  <View style={styles.aggBlock} testID="hedonic-model-metrics">
                    <Text style={styles.aggTitle}>Ventes {model.data.holdout.test_year} non vues <Text style={styles.aggN}>({formatInt(model.data.holdout.n)} biens)</Text></Text>
                    <View style={styles.aggRow}>
                      <View style={styles.aggCell}><Text style={styles.aggValue}>{pct(model.data.holdout.median_ape)}</Text><Text style={styles.aggLabel}>Erreur médiane</Text></View>
                      <View style={styles.aggCell}><Text style={styles.aggValue}>{pct(model.data.holdout.within_15pct)}</Text><Text style={styles.aggLabel}>Erreur ≤ 15 %</Text></View>
                      <View style={styles.aggCell}><Text style={styles.aggValue}>{model.data.holdout.r2_log ?? "—"}</Text><Text style={styles.aggLabel}>R² (log)</Text></View>
                    </View>
                  </View>
                  <Text style={styles.muted}>
                    Élasticité surface {model.data.coefficients?.log_surface?.toFixed(2)} · terrain (maison) {model.data.coefficients?.log_land_maison?.toFixed(3)} ·
                    tendance annuelle {pct((model.data.coefficients?.year_rel ?? 0) * 100)}. Le modèle sert à expliquer et à comparer ; la fourchette affichée reste celle des comparables.
                  </Text>
                </>
              ) : (
                <Text style={styles.p}>{model.data?.training ? "Entraînement en cours…" : "Modèle non entraîné."}</Text>
              )}
              <PrimaryButton
                title="Ré-entraîner le modèle"
                variant="secondary"
                onPress={() => train.mutate()}
                loading={train.isPending || !!model.data?.training}
                disabled={s.total === 0}
                testID="hedonic-train-button"
              />
            </View>

            <View style={styles.card} testID="validation-card">
              <Text style={styles.h3}>Validation de la baseline</Text>
              <Text style={styles.p}>
                Rejoue l’estimation sur 40 ventes réelles récentes tirées au hasard (chaque vente est exclue de ses propres
                comparables) et compare au prix effectivement payé. Critère Phase 1 : l’erreur reste plausible et la
                confiance reflète la précision.
              </Text>
              <PrimaryButton
                title="Lancer la validation (40 biens)"
                onPress={() => validation.mutate()}
                loading={validation.isPending}
                disabled={s.total === 0}
                testID="validation-run-button"
              />
              {validation.isError ? <Text style={styles.errorText}>{(validation.error as Error).message}</Text> : null}
              {validation.data ? (
                <View style={{ gap: spacing.md }} testID="validation-results">
                  <AggBlock title="Ensemble" agg={validation.data} testID="validation-agg-all" />
                  {Object.entries(validation.data.by_confidence).map(([k, v]) => (
                    <AggBlock key={k} title={LEVEL_LABELS[k] ?? k} agg={v} testID={`validation-agg-${k}`} />
                  ))}
                  {Object.entries(validation.data.by_type).map(([k, v]) => (
                    <AggBlock key={k} title={LEVEL_LABELS[k] ?? k} agg={v} testID={`validation-agg-${k}`} />
                  ))}
                  <Text style={styles.muted}>
                    MAPE globale : {pct(validation.data.mape)}. Les ventes DVF incluent des cas atypiques (état, travaux, ventes
                    entre proches) que le modèle ne peut pas connaître : l’erreur médiane est l’indicateur le plus lisible.
                  </Text>
                </View>
              ) : null}
            </View>
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
  cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { flex: 1, fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  pill: { flexDirection: "row", alignItems: "center", gap: 6, height: 28, paddingHorizontal: spacing.md, borderRadius: radius.pill },
  pillText: { fontFamily: fonts.semibold, fontSize: 12 },
  big: { fontFamily: fonts.bold, fontSize: 28, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  muted: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  errorText: { fontFamily: fonts.medium, fontSize: 13, color: colors.error },
  deptRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.sm, borderTopWidth: 1, borderTopColor: colors.divider },
  deptName: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  deptTotal: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  aggBlock: { backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, padding: spacing.md, gap: spacing.sm },
  aggTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceTertiary },
  aggN: { fontFamily: fonts.regular, color: colors.muted },
  aggRow: { flexDirection: "row", gap: spacing.sm },
  aggCell: { flex: 1, gap: 2 },
  aggValue: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurfaceTertiary, fontVariant: ["tabular-nums"] },
  aggLabel: { fontFamily: fonts.regular, fontSize: 11, lineHeight: 14, color: colors.muted },
}));
