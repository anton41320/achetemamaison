import { ListNumbersIcon } from "phosphor-react-native";
import { Text, View } from "react-native";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export const PHOTO_ORDER = ["Façade", "Salon", "Cuisine", "Jardin", "Suite parentale", "Chambre", "Salle de bains", "Terrasse", "Garage", "Vue extérieure"] as const;

/** Recommended photo order for the listing — the first one becomes the cover. */
export function PhotoOrderCard() {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.card} testID="photo-order-card">
      <View style={styles.head}>
        <ListNumbersIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.title}>Ordre conseillé des photos pour l’annonce</Text>
      </View>
      <View style={styles.chips}>
        {PHOTO_ORDER.map((label, i) => (
          <View key={label} style={[styles.chip, i === 0 && styles.chipFirst]} testID={`photo-order-${i + 1}`}>
            <Text style={[styles.num, i === 0 && styles.numFirst]}>{i + 1}</Text>
            <Text style={[styles.chipText, i === 0 && styles.chipTextFirst]}>{label}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.hint}>Importez vos photos dans cet ordre : la façade sert de couverture. Vous pouvez ensuite les réordonner avec les flèches.</Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { flex: 1, fontFamily: fonts.bold, fontSize: 15, color: colors.onSurfaceSecondary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingVertical: 6, paddingLeft: 6, paddingRight: spacing.md, minHeight: 34 },
  chipFirst: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  num: { width: 22, height: 22, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, color: colors.onBrandTertiary, fontFamily: fonts.bold, fontSize: 12, textAlign: "center", lineHeight: 22, overflow: "hidden" },
  numFirst: { backgroundColor: colors.onBrandPrimary, color: colors.brandPrimary },
  chipText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onSurface },
  chipTextFirst: { color: colors.onBrandPrimary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
}));
