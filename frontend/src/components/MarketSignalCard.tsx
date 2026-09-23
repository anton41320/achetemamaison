import { useQuery } from "@tanstack/react-query";
import { GaugeIcon } from "phosphor-react-native";
import { ActivityIndicator, Text, View } from "react-native";

import { api, formatMonth } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
}

const VERDICT = {
  favorable: { label: "Bon moment pour vendre", text: "Les signaux locaux sont porteurs : prix en hausse ou stables, ventes régulières." },
  neutre: { label: "Moment neutre", text: "Marché sans tendance nette : la qualité du dossier et le prix affiché feront la différence." },
  attentiste: { label: "Marché attentiste", text: "Prix en repli ou peu de ventes : prévoyez une marge de négociation ou attendez de meilleurs signaux." },
};

export function MarketSignalCard({ propertyId }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { data, isLoading } = useQuery({ queryKey: ["market-signal", propertyId], queryFn: () => api.marketSignal(propertyId) });

  const tone = data?.verdict === "favorable" ? colors.success : data?.verdict === "attentiste" ? colors.error : colors.warning;

  return (
    <View style={styles.card} testID="market-signal-card">
      <View style={styles.header}>
        <GaugeIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Bon moment pour vendre ?</Text>
      </View>
      {isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} />
      ) : !data?.available || !data.verdict ? (
        <Text style={styles.detail}>Signal indisponible.</Text>
      ) : (
        <>
          <View style={styles.verdictRow}>
            <View style={[styles.scoreCircle, { borderColor: tone }]}>
              <Text style={[styles.score, { color: tone }]} testID="market-signal-score">{data.score}</Text>
              <Text style={styles.scoreMax}>/100</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={[styles.verdict, { color: tone }]} testID="market-signal-verdict">{VERDICT[data.verdict].label}</Text>
              <Text style={styles.p}>{VERDICT[data.verdict].text}</Text>
            </View>
          </View>
          <View style={styles.gauge}>
            <View style={[styles.gaugeFill, { width: `${data.score ?? 0}%` as `${number}%`, backgroundColor: tone }]} />
          </View>
          {data.reasons?.map((r) => (
            <View key={r.key} style={styles.reason} testID={`market-signal-reason-${r.key}`}>
              <View style={styles.reasonHead}>
                <Text style={styles.reasonLabel}>{r.label}</Text>
                <Text style={styles.reasonScore}>{r.score}/{r.max_score}</Text>
              </View>
              <Text style={styles.detail}>{r.text}</Text>
            </View>
          ))}
          <Text style={styles.detail}>
            {data.scope} · calculé à la dernière vente enregistrée ({data.as_of ? formatMonth(data.as_of) : "—"}). Les
            données de ventes sont publiées avec ~6 mois de décalage.
          </Text>
        </>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flex: 1 },
  p: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  verdictRow: { flexDirection: "row", alignItems: "center", gap: spacing.lg },
  scoreCircle: { width: 72, height: 72, borderRadius: 36, borderWidth: 3, alignItems: "center", justifyContent: "center" },
  score: { fontFamily: fonts.bold, fontSize: 24, lineHeight: 28, fontVariant: ["tabular-nums"] },
  scoreMax: { fontFamily: fonts.regular, fontSize: 10, color: colors.muted },
  verdict: { fontFamily: fonts.bold, fontSize: 16 },
  gauge: { height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, overflow: "hidden" },
  gaugeFill: { height: 8, borderRadius: radius.pill },
  reason: { gap: 2, borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.sm },
  reasonHead: { flexDirection: "row", justifyContent: "space-between" },
  reasonLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  reasonScore: { fontFamily: fonts.medium, fontSize: 13, color: colors.muted },
}));
