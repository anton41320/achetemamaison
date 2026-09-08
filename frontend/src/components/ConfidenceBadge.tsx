import { BlurView } from "expo-blur";
import { ShieldCheckIcon } from "phosphor-react-native";
import { Platform, Text, View } from "react-native";

import { CONFIDENCE_LABELS, ConfidenceLevel } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  level: ConfidenceLevel;
  score?: number;
  glass?: boolean;
  testID?: string;
}

export function useConfidenceColor(level: ConfidenceLevel) {
  const { colors } = useTheme();
  if (level === "eleve") return { fg: colors.success, bg: colors.successSoft };
  if (level === "moyen") return { fg: colors.warning, bg: colors.warningSoft };
  return { fg: colors.error, bg: colors.errorSoft };
}

export function ConfidenceBadge({ level, score, glass, testID }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const tone = useConfidenceColor(level);
  const label = CONFIDENCE_LABELS[level];

  if (glass) {
    const inner = (
      <View style={styles.glassRow}>
        <View style={[styles.dot, { backgroundColor: tone.fg }]} />
        <Text style={styles.glassLabel} testID={testID}>
          {label}
          {score !== undefined ? ` · ${score}/100` : ""}
        </Text>
      </View>
    );
    if (Platform.OS === "web") {
      return <View style={[styles.glassWrap, { backgroundColor: colors.glassFill }]}>{inner}</View>;
    }
    return (
      <BlurView intensity={40} tint="light" style={styles.glassWrap} experimentalBlurMethod="dimezisBlurView">
        {inner}
      </BlurView>
    );
  }

  return (
    <View style={[styles.pill, { backgroundColor: tone.bg }]} testID={testID}>
      <ShieldCheckIcon size={14} color={tone.fg} weight="fill" />
      <Text style={[styles.pillLabel, { color: tone.fg }]}>{label}</Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    paddingHorizontal: spacing.md,
    height: 28,
    borderRadius: radius.pill,
  },
  pillLabel: { fontFamily: fonts.semibold, fontSize: 12 },
  glassWrap: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  glassRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    height: 36,
  },
  dot: { width: 10, height: 10, borderRadius: 5 },
  glassLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onHero },
}));
