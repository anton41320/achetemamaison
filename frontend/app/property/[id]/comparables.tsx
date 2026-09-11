import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Comparable, api, formatDistance, formatEuro, formatInt, formatMonth } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export default function ComparablesScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["property", id],
    queryFn: () => api.getProperty(id!),
    enabled: !!id,
  });

  const comps = data?.estimation?.comparables ?? [];
  const maxWeight = comps.reduce((m, c) => Math.max(m, c.weight), 0) || 1;

  const renderItem = ({ item, index }: { item: Comparable; index: number }) => (
    <View style={styles.row} testID={`comparable-row-${index}`}>
      <View style={styles.rowTop}>
        <Text style={styles.price}>{formatEuro(item.price)}</Text>
        <Text style={styles.pm2}>{formatInt(item.price_m2)} €/m²</Text>
      </View>
      <View style={styles.rowMid}>
        <Text style={styles.meta}>
          {item.surface} m²{item.rooms ? ` · ${item.rooms} p.` : ""}
          {item.property_type === "maison" && item.land_surface ? ` · terrain ${formatInt(item.land_surface)} m²` : ""}
        </Text>
      </View>
      <View style={styles.rowBottom}>
        <Text style={styles.muted}>{formatMonth(item.date)} · à {formatDistance(item.distance_m)} · {item.commune}{item.population ? ` (${formatInt(item.population)} hab.)` : ""}</Text>
        <View style={styles.weightBar}>
          <View style={[styles.weightFill, { width: `${Math.max(8, Math.round((item.weight / maxWeight) * 100))}%` }]} />
        </View>
      </View>
    </View>
  );

  return (
    <View style={styles.screen} testID="comparables-screen">
      <ScreenHeader
        title="Ventes comparables"
        subtitle={data?.estimation ? `${comps.length} ventes DVF · ${data.estimation.confidence.radius_label}` : "DVF"}
        onBack={() => router.back()}
      />
      {isLoading ? (
        <View style={styles.list}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={styles.skeleton} />)}
        </View>
      ) : isError ? (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>Erreur de chargement</Text>
          <PrimaryButton title="Réessayer" onPress={() => refetch()} testID="comparables-retry-button" variant="secondary" />
        </View>
      ) : comps.length === 0 ? (
        <View style={styles.center} testID="comparables-empty">
          <Text style={styles.emptyTitle}>Aucun comparable exact trouvé</Text>
        </View>
      ) : (
        <FlatList
          data={comps}
          keyExtractor={(c, i) => `${c.date}-${c.price}-${i}`}
          renderItem={renderItem}
          contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + spacing.xl }]}
          ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
          ListHeaderComponent={
            <Text style={styles.intro}>
              Triées par poids dans l’estimation (récence, distance, similarité de surface et de taille de commune). Les ventes hors de votre commune ne sont retenues que dans des communes de taille comparable (0,4× à 2,5× votre population), jusqu’à 10 km. La barre indique le poids relatif.
            </Text>
          }
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  list: { padding: spacing.lg },
  intro: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.muted, marginBottom: spacing.md },
  row: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: 6 },
  rowTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" },
  price: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  pm2: { fontFamily: fonts.semibold, fontSize: 15, color: colors.brandPrimary, fontVariant: ["tabular-nums"] },
  rowMid: {},
  meta: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceTertiary },
  rowBottom: { gap: 6 },
  muted: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  weightBar: { height: 4, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, overflow: "hidden" },
  weightFill: { height: 4, backgroundColor: colors.brandSecondary, borderRadius: radius.pill },
  skeleton: { height: 96, borderRadius: radius.md, backgroundColor: colors.skeleton, marginBottom: spacing.sm },
  center: { flex: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: "center" },
  emptyTitle: { fontFamily: fonts.semibold, fontSize: 18, color: colors.onSurface, textAlign: "center" },
}));
