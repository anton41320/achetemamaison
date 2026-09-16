import { Image } from "expo-image";
import { Text, View } from "react-native";

import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export const APP_NAME = "Achètes ma maison";

interface Props {
  size?: number;
  /** Show the wordmark next to (row) or under (column) the logo. */
  wordmark?: "row" | "column" | "none";
  testID?: string;
}

/** Brand logo (rounded blue square from assets) with optional wordmark. */
export function BrandLogo({ size = 40, wordmark = "row", testID = "brand-logo" }: Props) {
  const styles = useStyles();
  return (
    <View style={[styles.wrap, wordmark === "column" && styles.column]} testID={testID}>
      <Image
        source={require("../../assets/images/logo.png")}
        style={{ width: size, height: size, borderRadius: Math.round(size * 0.22) }}
        contentFit="contain"
        accessibilityLabel={APP_NAME}
      />
      {wordmark !== "none" ? (
        <Text style={[styles.name, wordmark === "column" && styles.nameColumn, { fontSize: wordmark === "column" ? 22 : Math.max(14, Math.round(size * 0.4)) }]}>
          {APP_NAME}
        </Text>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  wrap: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  column: { flexDirection: "column", gap: spacing.sm, alignItems: "center" },
  name: { fontFamily: fonts.bold, color: colors.brandPrimary, letterSpacing: -0.2 },
  nameColumn: { textAlign: "center", marginTop: spacing.xs, borderRadius: radius.sm },
}));
