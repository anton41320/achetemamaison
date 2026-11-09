import { Image } from "expo-image";
import type { StyleProp, ViewStyle } from "react-native";
import { Text, View } from "react-native";

import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export const MASCOT_NAME = "Noisette";

/** Visuels de la mascotte, déjà fondus (alpha circulaire) : ils se posent sur n'importe quel fond. */
export const MASCOT_POSES = {
  pouce: require("../../assets/mascot/noisette-pouce.webp"),
  telephone: require("../../assets/mascot/noisette-telephone.webp"),
  noisettes: require("../../assets/mascot/noisette-noisettes.webp"),
  course: require("../../assets/mascot/noisette-course.webp"),
} as const;

export type MascotPose = keyof typeof MASCOT_POSES;

const POSE_ALT: Record<MascotPose, string> = {
  pouce: `${MASCOT_NAME}, la mascotte écureuil, pouce levé`,
  telephone: `${MASCOT_NAME}, la mascotte écureuil, montre l’application sur un téléphone`,
  noisettes: `${MASCOT_NAME}, la mascotte écureuil, fait la sieste sur ses noisettes`,
  course: `${MASCOT_NAME}, la mascotte écureuil, court`,
};

type Props = {
  pose: MascotPose;
  /** Conseil court dit par la mascotte. */
  text: string;
  /** Taille de la vignette ronde (px). */
  size?: number;
  /** `row` : vignette à gauche + bulle ; `column` : vignette au-dessus, bulle centrée (états vides). */
  layout?: "row" | "column";
  style?: StyleProp<ViewStyle>;
  testID?: string;
};

/** Mascotte « Noisette » avec une bulle de conseil. Discrète : vignette ronde fondue + bulle courte. */
export function MascotTip({ pose, text, size = 96, layout = "row", style, testID = "mascot-tip" }: Props) {
  const styles = useStyles();
  const column = layout === "column";
  return (
    <View style={[column ? styles.column : styles.row, style]} testID={testID} accessible accessibilityLabel={`${MASCOT_NAME} : ${text}`}>
      <Image source={MASCOT_POSES[pose]} style={{ width: size, height: size }} contentFit="contain" accessibilityLabel={POSE_ALT[pose]} transition={200} />
      <View style={[styles.bubbleWrap, column && styles.bubbleWrapColumn]}>
        <View style={[styles.pointer, column ? styles.pointerUp : styles.pointerLeft]} />
        <View style={styles.bubble}>
          <Text style={styles.name}>{MASCOT_NAME}</Text>
          <Text style={[styles.text, column && { textAlign: "center" }]} testID={`${testID}-text`}>{text}</Text>
        </View>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm, maxWidth: 760 },
  column: { alignItems: "center", gap: spacing.xs },
  bubbleWrap: { flex: 1, justifyContent: "center" },
  bubbleWrapColumn: { flexGrow: 0, flexShrink: 0, flexBasis: "auto", alignItems: "center", width: "100%", maxWidth: 420 },
  bubble: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: 2,
  },
  pointer: {
    position: "absolute",
    width: 14,
    height: 14,
    backgroundColor: colors.surfaceSecondary,
    borderColor: colors.border,
    transform: [{ rotate: "45deg" }],
    zIndex: 1,
  },
  pointerLeft: { left: -6, borderLeftWidth: 1, borderBottomWidth: 1 },
  pointerUp: { top: -6, alignSelf: "center", borderLeftWidth: 1, borderTopWidth: 1 },
  name: { fontFamily: fonts.bold, fontSize: 11, letterSpacing: 0.8, textTransform: "uppercase", color: colors.brandPrimary },
  text: { fontFamily: fonts.medium, fontSize: 14, lineHeight: 20, color: colors.onSurfaceSecondary },
}));
