import { AppleLogoIcon, GooglePlayLogoIcon } from "phosphor-react-native";
import { Linking, Pressable, Text, View, type StyleProp, type ViewStyle } from "react-native";

import { APP_STORE_URL, PLAY_STORE_URL } from "@/src/stores";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

/** Badges « Télécharger dans l'App Store » / « Disponible sur Google Play » (style sombre, couleurs identiques en clair et sombre). */
export function StoreBadges({ style, compact }: { style?: StyleProp<ViewStyle>; compact?: boolean }) {
  const styles = useStyles();
  const items = [
    { url: APP_STORE_URL, Icon: AppleLogoIcon, small: "Télécharger dans", big: "l’App Store", testID: "store-badge-ios" },
    { url: PLAY_STORE_URL, Icon: GooglePlayLogoIcon, small: "Disponible sur", big: "Google Play", testID: "store-badge-android" },
  ];
  return (
    <View style={[styles.row, style]}>
      {items.map((it) => (
        <Pressable key={it.testID} onPress={() => Linking.openURL(it.url)} accessibilityRole="link" accessibilityLabel={`${it.small} ${it.big}`}
          style={({ pressed }) => [styles.badge, compact && styles.badgeCompact, pressed && { opacity: 0.85 }]} testID={it.testID}>
          <it.Icon size={compact ? 22 : 28} color="#FFFFFF" weight="fill" />
          <View>
            <Text style={styles.small}>{it.small}</Text>
            <Text style={[styles.big, compact && { fontSize: 15 }]}>{it.big}</Text>
          </View>
        </Pressable>
      ))}
    </View>
  );
}

const useStyles = makeStyles(() => ({
  row: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  // Badges de store : noir et blanc quel que soit le thème (convention Apple/Google).
  badge: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#111111", borderRadius: radius.md, paddingHorizontal: 14, minHeight: 52, borderWidth: 1, borderColor: "#3A3A3A" },
  badgeCompact: { minHeight: 44, paddingHorizontal: 12 },
  small: { fontFamily: fonts.medium, fontSize: 10, color: "#D6D6D6", lineHeight: 12 },
  big: { fontFamily: fonts.semibold, fontSize: 17, color: "#FFFFFF", lineHeight: 20 },
}));
