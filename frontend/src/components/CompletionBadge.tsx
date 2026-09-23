import { CheckCircleIcon, PencilSimpleIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { Completion } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  completion: Completion;
  testID: string;
  /** Compact pill (home card) or full card with missing criteria + tap to edit (property screen). */
  variant?: "pill" | "card";
  onPress?: () => void;
}

export function CompletionBadge({ completion, testID, variant = "pill", onPress }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const complete = completion.pct >= 80;
  const tone = complete ? colors.success : completion.pct >= 50 ? colors.brandPrimary : colors.warning;
  const soft = complete ? colors.successSoft : completion.pct >= 50 ? colors.brandTertiary : colors.warningSoft;

  if (variant === "pill") {
    return (
      <View style={[styles.pill, { backgroundColor: soft }]} testID={testID} accessibilityLabel={`Profil complété à ${completion.pct} %`}>
        <View style={[styles.dot, { backgroundColor: tone }]} />
        <Text style={[styles.pillText, { color: tone }]}>Profil complété à {completion.pct} %</Text>
      </View>
    );
  }

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`Profil complété à ${completion.pct} %. Compléter les caractéristiques`}
      onPress={onPress}
      style={({ pressed }) => [styles.card, { backgroundColor: soft }, pressed && { opacity: 0.85 }]}
    >
      <View style={styles.cardHead}>
        <Text style={[styles.cardTitle, { color: tone }]}>Profil complété à {completion.pct} %</Text>
        {complete ? <CheckCircleIcon size={20} color={tone} weight="fill" /> : <PencilSimpleIcon size={20} color={tone} />}
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.max(4, completion.pct)}%`, backgroundColor: tone }]} />
      </View>
      <Text style={styles.hint} testID={`${testID}-hint`}>
        {completion.missing.length === 0
          ? "Tous les critères sont renseignés : l’estimation tient compte de toutes les caractéristiques."
          : `${completion.filled}/${completion.total} critères renseignés · à compléter : ${completion.missing.slice(0, 4).join(", ")}${completion.missing.length > 4 ? "…" : ""}`}
      </Text>
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  pill: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", paddingHorizontal: spacing.sm, paddingVertical: 3, borderRadius: radius.pill },
  dot: { width: 6, height: 6, borderRadius: 3 },
  pillText: { fontFamily: fonts.semibold, fontSize: 11 },
  card: { borderRadius: radius.md, padding: spacing.lg, gap: spacing.sm, borderWidth: 1, borderColor: colors.border },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  cardTitle: { fontFamily: fonts.bold, fontSize: 15 },
  track: { height: 6, borderRadius: radius.pill, backgroundColor: colors.surface, overflow: "hidden" },
  fill: { height: 6, borderRadius: radius.pill },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.onSurfaceTertiary },
}));
