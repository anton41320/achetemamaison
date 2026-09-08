import { useQuery } from "@tanstack/react-query";
import { ChartLineUpIcon, TrendDownIcon, TrendUpIcon } from "phosphor-react-native";
import { ActivityIndicator, Text, View } from "react-native";

import { TrendPoint, api, formatInt, formatPct } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
  typeLabel: string;
}

export function TrendCard({ propertyId, typeLabel }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["trend", propertyId],
    queryFn: () => api.trend(propertyId),
  });

  const Change = ({ value, label }: { value: number | null; label: string }) => {
    if (value === null) return <Text style={styles.detail}>{label} : données insuffisantes</Text>;
    const up = value > 0.01;
    const down = value < -0.01;
    const color = up ? colors.success : down ? colors.error : colors.muted;
    const Icon = up ? TrendUpIcon : TrendDownIcon;
    return (
      <View style={styles.changeRow}>
        {up || down ? <Icon size={16} color={color} weight="bold" /> : null}
        <Text style={[styles.changeText, { color }]}>
          {label} : {formatPct(value, 0)} {up ? "(marché en hausse)" : down ? "(marché en repli)" : "(marché stable)"}
        </Text>
      </View>
    );
  };

  return (
    <View style={styles.card} testID="trend-card">
      <View style={styles.header}>
        <ChartLineUpIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Tendance du marché</Text>
      </View>
      {isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} />
      ) : isError || !data ? (
        <Text style={styles.detail}>Tendance indisponible.</Text>
      ) : (
        <>
          <Text style={styles.p}>
            Prix/m² médian des {typeLabel.toLowerCase()}s vendus par année à {data.commune} (barres) et dans un rayon de
            1,5 km (points).
          </Text>
          <Bars commune={data.commune_series} quartier={data.quartier_series} />
          <Change value={data.commune_change_pct} label={`${data.commune}, ${data.years[0]}→${data.years[data.years.length - 1]}`} />
          <Change value={data.quartier_change_pct} label="Rayon 1,5 km" />
          <Text style={styles.detail}>
            Les années comptant moins de 5 ventes sont ignorées dans le calcul de la variation.
          </Text>
        </>
      )}
    </View>
  );
}

function Bars({ commune, quartier }: { commune: TrendPoint[]; quartier: TrendPoint[] }) {
  const styles = useStyles();
  const vals = [...commune, ...quartier].map((p) => p.median_pm2).filter((v): v is number => v !== null);
  const max = Math.max(1, ...vals);
  const min = Math.min(...vals, max);
  const floor = Math.max(0, min - (max - min) * 0.25);
  const scale = (v: number) => Math.min(1, Math.max(0.06, (v - floor) / (max - floor || 1)));
  const H = 120;
  return (
    <View style={styles.chart} testID="trend-chart">
      {commune.map((p, i) => {
        const q = quartier[i];
        return (
          <View key={p.year} style={styles.col} testID={`trend-year-${p.year}`}>
            <Text style={styles.colValue}>{p.median_pm2 ? formatInt(p.median_pm2) : "—"}</Text>
            <View style={[styles.barArea, { height: H }]}>
              {p.median_pm2 ? (
                <View style={[styles.bar, { height: Math.round(scale(p.median_pm2) * H) }]} />
              ) : (
                <View style={[styles.bar, styles.barEmpty, { height: 6 }]} />
              )}
              {q?.median_pm2 ? (
                <View style={[styles.dot, { bottom: Math.round(scale(q.median_pm2) * H) - 5 }]} />
              ) : null}
            </View>
            <Text style={styles.colYear}>{p.year}</Text>
            <Text style={styles.colCount}>{p.count} v.</Text>
          </View>
        );
      })}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary, flex: 1 },
  p: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  chart: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-end", paddingTop: spacing.sm },
  col: { flex: 1, alignItems: "center", gap: 4 },
  colValue: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onSurfaceTertiary, fontVariant: ["tabular-nums"] },
  barArea: { width: "100%", justifyContent: "flex-end", alignItems: "center", position: "relative" },
  bar: { width: "70%", borderRadius: radius.sm, backgroundColor: colors.brandSecondary },
  barEmpty: { backgroundColor: colors.surfaceTertiary },
  dot: { position: "absolute", width: 10, height: 10, borderRadius: 5, backgroundColor: colors.brandPrimary, borderWidth: 2, borderColor: colors.surfaceSecondary },
  colYear: { fontFamily: fonts.medium, fontSize: 12, color: colors.onSurfaceSecondary },
  colCount: { fontFamily: fonts.regular, fontSize: 10, color: colors.muted },
  changeRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  changeText: { flex: 1, fontFamily: fonts.medium, fontSize: 13 },
}));
