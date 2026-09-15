import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useFocusEffect, useRouter } from "expo-router";
import { DatabaseIcon, PlusIcon, UserCircleIcon } from "phosphor-react-native";
import { useCallback } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { AlertsBanner } from "@/src/components/AlertsBanner";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { PropertyCard } from "@/src/components/PropertyCard";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const EMPTY_IMAGE =
  "https://images.unsplash.com/photo-1614595737476-42487331b8a1?crop=entropy&cs=srgb&fm=jpg&q=85&w=900";

export default function HomeScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error, refetch, isRefetching } = useQuery({
    queryKey: ["properties"],
    queryFn: api.listProperties,
  });
  const steps = useQuery({ queryKey: ["next-steps"], queryFn: api.nextSteps, enabled: !!data && data.length > 0 });
  const stepsById = new Map((steps.data?.properties ?? []).map((s) => [s.property_id, s]));

  useFocusEffect(
    useCallback(() => {
      queryClient.invalidateQueries({ queryKey: ["next-steps"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["properties"] });
    }, [queryClient]),
  );

  const goNew = () => router.push("/new");
  const onRefresh = () => {
    refetch();
    steps.refetch();
  };

  return (
    <View style={styles.screen} testID="home-screen">
      <ScreenHeader
        title="Mes biens"
        subtitle="Estimo · Estimations DVF · Centre-Val de Loire"
        right={
          <View style={{ flexDirection: "row", gap: spacing.sm }}>
            <Pressable
              testID="home-data-button"
              accessibilityRole="button"
              accessibilityLabel="Données DVF"
              onPress={() => router.push("/data")}
              style={styles.iconBtn}
            >
              <DatabaseIcon size={20} color={colors.onSurface} />
            </Pressable>
            <Pressable
              testID="home-account-button"
              accessibilityRole="button"
              accessibilityLabel="Mon compte"
              onPress={() => router.push("/account")}
              style={styles.iconBtn}
            >
              <UserCircleIcon size={22} color={colors.onSurface} />
            </Pressable>
          </View>
        }
      />

      {isLoading ? (
        <View style={styles.list}>
          {[0, 1, 2].map((i) => (
            <View key={i} style={styles.skeleton} testID={`home-skeleton-${i}`} />
          ))}
        </View>
      ) : isError ? (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>Impossible de charger vos biens</Text>
          <Text style={styles.emptyText} testID="home-error-detail">
            {error instanceof Error ? error.message : "Erreur réseau"} · Vérifiez votre connexion puis réessayez.
          </Text>
          <PrimaryButton title="Réessayer" onPress={() => refetch()} testID="home-retry-button" variant="secondary" />
        </View>
      ) : !data || data.length === 0 ? (
        <View style={styles.center} testID="home-empty-state">
          <Image source={{ uri: EMPTY_IMAGE }} style={styles.emptyImage} contentFit="cover" transition={300} />
          <Text style={styles.emptyTitle}>Aucune estimation pour le moment</Text>
          <Text style={styles.emptyText}>
            Renseignez l’adresse et les caractéristiques de votre bien : Estimo calcule une fourchette de valeur à
            partir des ventes réelles (DVF) autour de chez vous, avec un niveau de confiance explicite.
          </Text>
          <PrimaryButton title="Nouvelle estimation" onPress={goNew} testID="home-empty-cta" />
        </View>
      ) : (
        <FlatList
          data={data}
          keyExtractor={(p) => p.id}
          contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + 96 }]}
          ListHeaderComponent={<AlertsBanner />}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={onRefresh} tintColor={colors.brandPrimary} />}
          renderItem={({ item, index }) => (
            <Animated.View entering={FadeInDown.delay(Math.min(index, 6) * 60).duration(320)}>
              <PropertyCard
                property={item}
                onPress={() => router.push(`/property/${item.id}`)}
                testID={`property-card-${item.id}`}
                nextSteps={stepsById.get(item.id) ?? null}
                onStepPress={(route) => router.push(route as any)}
              />
            </Animated.View>
          )}
          ItemSeparatorComponent={() => <View style={{ height: spacing.md }} />}
        />
      )}

      {data && data.length > 0 ? (
        <Pressable
          testID="home-fab-new"
          accessibilityRole="button"
          accessibilityLabel="Nouvelle estimation"
          onPress={goNew}
          style={({ pressed }) => [styles.fab, { bottom: insets.bottom + spacing.lg }, pressed && styles.fabPressed]}
        >
          <PlusIcon size={20} color={colors.onBrandPrimary} weight="bold" />
          <Text style={styles.fabLabel}>Nouvelle estimation</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  list: { padding: spacing.lg, gap: spacing.md },
  skeleton: { height: 120, borderRadius: radius.lg, backgroundColor: colors.skeleton, marginBottom: spacing.md },
  center: { flex: 1, padding: spacing.xl, gap: spacing.lg, justifyContent: "center" },
  emptyImage: { width: "100%", height: 220, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  emptyTitle: { fontFamily: fonts.bold, fontSize: 22, color: colors.onSurface },
  emptyText: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, color: colors.onSurfaceTertiary },
  fab: {
    position: "absolute",
    right: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    height: 52,
    paddingHorizontal: spacing.xl,
    borderRadius: radius.pill,
    backgroundColor: colors.brandPrimary,
    shadowColor: colors.surfaceInverse,
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 4,
  },
  fabPressed: { opacity: 0.9 },
  fabLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandPrimary },
}));
