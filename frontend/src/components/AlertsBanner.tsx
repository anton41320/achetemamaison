import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { BellRingingIcon, CaretRightIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { ExpiryAlert, api } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

function describe(a: ExpiryAlert): string {
  if (a.days_left < 0) return `Expiré depuis ${-a.days_left} jour${-a.days_left > 1 ? "s" : ""} — à refaire avant la vente`;
  if (a.days_left === 0) return "Expire aujourd’hui";
  return `Expire dans ${a.days_left} jour${a.days_left > 1 ? "s" : ""}`;
}

export function AlertsBanner() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["alerts"], queryFn: api.alerts });
  const alerts = data?.alerts ?? [];
  if (alerts.length === 0) return null;

  const tone = (level: ExpiryAlert["level"]) => (level === "bientot" ? colors.warning : colors.error);

  return (
    <View style={styles.wrap} testID="alerts-banner">
      <View style={styles.head}>
        <BellRingingIcon size={18} color={colors.warning} weight="fill" />
        <Text style={styles.title}>
          {alerts.length} diagnostic{alerts.length > 1 ? "s" : ""} à renouveler
        </Text>
      </View>
      {alerts.slice(0, 4).map((a) => (
        <Pressable
          key={a.document_id}
          testID={`alert-${a.item_key}-${a.property_id}`}
          accessibilityRole="button"
          onPress={() => router.push(`/property/${a.property_id}/document/${a.document_id}`)}
          style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}
        >
          <View style={[styles.dot, { backgroundColor: tone(a.level) }]} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={styles.label} numberOfLines={1}>{a.label}</Text>
            <Text style={styles.meta} numberOfLines={1}>{a.address_label}</Text>
            <Text style={[styles.meta, { color: tone(a.level) }]}>{describe(a)}</Text>
          </View>
          <CaretRightIcon size={16} color={colors.muted} />
        </Pressable>
      ))}
      {alerts.length > 4 ? <Text style={styles.meta}>+ {alerts.length - 4} autre{alerts.length - 4 > 1 ? "s" : ""}</Text> : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  wrap: { backgroundColor: colors.warningSoft, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, marginBottom: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { fontFamily: fonts.semibold, fontSize: 14, color: colors.warning, flex: 1 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, padding: spacing.md, minHeight: 56 },
  dot: { width: 10, height: 10, borderRadius: radius.pill },
  label: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceSecondary },
  meta: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
}));
