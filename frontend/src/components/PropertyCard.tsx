import { BuildingsIcon, CaretRightIcon, HouseIcon } from "phosphor-react-native";
import { Pressable, Text, View } from "react-native";

import { Property, TYPE_LABELS, formatK } from "@/src/api";
import { ConfidenceBadge } from "@/src/components/ConfidenceBadge";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  property: Property;
  onPress: () => void;
  testID: string;
}

export function PropertyCard({ property, onPress, testID }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const est = property.estimation;
  const Icon = property.property_type === "maison" ? HouseIcon : BuildingsIcon;

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.iconWrap}>
        <Icon size={22} color={colors.onBrandTertiary} weight="duotone" />
      </View>
      <View style={styles.body}>
        <Text style={styles.address} numberOfLines={1}>
          {property.address_label}
        </Text>
        <Text style={styles.meta}>
          {TYPE_LABELS[property.property_type]} · {property.surface} m² · {property.rooms} p.
        </Text>
        {est ? (
          <>
            <Text style={styles.range} testID={`${testID}-range`}>
              {formatK(est.low)} – {formatK(est.high)}
            </Text>
            <ConfidenceBadge level={est.confidence.level} />
          </>
        ) : (
          <Text style={styles.meta}>Estimation indisponible</Text>
        )}
      </View>
      <CaretRightIcon size={18} color={colors.muted} />
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pressed: { opacity: 0.9 },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  body: { flex: 1, gap: 4 },
  address: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary },
  meta: { fontFamily: fonts.regular, fontSize: 13, color: colors.muted },
  range: { fontFamily: fonts.bold, fontSize: 20, color: colors.onSurfaceSecondary, marginTop: 2, marginBottom: 4 },
}));
