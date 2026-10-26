import { Image } from "expo-image";
import { View } from "react-native";

import { makeStyles, spacing } from "@/src/theme";

export const APP_NAME = "Achète ma maison";

/** Ratio largeur/hauteur du logo complet (fichier de la charte : 1558 × 407). */
const WORDMARK_RATIO = 1558 / 407;

interface Props {
  /** Hauteur de l'icône (mode « none ») ou du logo complet (mode « row »/« column »). */
  size?: number;
  /** « none » : icône seule ; sinon le logo complet « Achète ma maison .fr » de la charte. */
  wordmark?: "row" | "column" | "none";
  /** Version blanche pour fonds sombres. */
  onDark?: boolean;
  testID?: string;
}

/** Logo de la charte (maison noire + plus bleu), seul ou avec le nom. */
export function BrandLogo({ size = 40, wordmark = "row", onDark = false, testID = "brand-logo" }: Props) {
  const styles = useStyles();
  if (wordmark === "none") {
    return (
      <View style={styles.wrap} testID={testID}>
        <Image source={require("../../assets/images/logo.png")} style={{ width: size, height: size }} contentFit="contain" accessibilityLabel={APP_NAME} />
      </View>
    );
  }
  const height = wordmark === "column" ? Math.round(size * 0.6) : size;
  return (
    <View style={[styles.wrap, wordmark === "column" && styles.column]} testID={testID}>
      <Image
        source={onDark ? require("../../assets/images/logo-wordmark-dark.png") : require("../../assets/images/logo-wordmark.png")}
        style={{ width: Math.round(height * WORDMARK_RATIO), height }}
        contentFit="contain"
        accessibilityLabel={APP_NAME}
      />
    </View>
  );
}

const useStyles = makeStyles(() => ({
  wrap: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  column: { flexDirection: "column", alignItems: "center" },
}));
